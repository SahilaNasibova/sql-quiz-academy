import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone
from sqlalchemy import create_engine, text


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f'{salt}:{digest}'


def password_ok(password, stored):
    return hmac.compare_digest(password_hash(password, stored.split(':')[0]), stored)


class Academy:
    def __init__(self, url, teacher_email=''):
        self.engine = create_engine(url, pool_pre_ping=True)
        self.teacher_email = teacher_email.strip().lower()
        if self.engine.dialect.name == 'postgresql':
            # Keep credentials and answer keys outside Supabase's default Data API schema.
            with self.engine.begin() as c:
                c.execute(text('CREATE SCHEMA IF NOT EXISTS quiz_academy'))
                c.execute(text('REVOKE ALL ON SCHEMA quiz_academy FROM PUBLIC'))
            self.engine.dispose()
            self.engine = create_engine(url, pool_pre_ping=True, connect_args={'options': '-csearch_path=quiz_academy'})
        statements = [
            'CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, name TEXT NOT NULL, password TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS questions (id TEXT PRIMARY KEY, topic TEXT NOT NULL, prompt TEXT NOT NULL, options TEXT NOT NULL, answer INTEGER NOT NULL, points INTEGER NOT NULL, explanation TEXT NOT NULL, active INTEGER NOT NULL)',
            'CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, duration INTEGER NOT NULL)',
            'CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, email TEXT NOT NULL, started DOUBLE PRECISION NOT NULL, deadline DOUBLE PRECISION NOT NULL, questions TEXT NOT NULL, answers TEXT NOT NULL, result TEXT)',
        ]
        with self.engine.begin() as c:
            for statement in statements:
                c.execute(text(statement))
            c.execute(text('INSERT INTO settings (id,duration) VALUES (1,20) ON CONFLICT (id) DO NOTHING'))

    def rows(self, sql, **params):
        with self.engine.connect() as c:
            return [dict(r) for r in c.execute(text(sql), params).mappings()]

    def register(self, name, email, password):
        email = email.strip().lower()
        if len(name.strip()) < 3 or '@' not in email or len(password) < 10:
            raise ValueError('Ad-soyad, düzgün e-poçt və ən azı 10 simvolluq şifrə daxil edin.')
        # The configured teacher must be provisioned privately, never through public registration.
        if email == self.teacher_email:
            raise ValueError('Bu hesab administrator tərəfindən yaradılmalıdır.')
        with self.engine.begin() as c:
            c.execute(text('INSERT INTO users VALUES (:email,:name,:password)'), dict(email=email, name=name.strip(), password=password_hash(password)))

    def provision_teacher(self, password):
        if not self.teacher_email or len(password) < 10:
            raise ValueError('Müəllim e-poçtu və ən azı 10 simvolluq şifrə lazımdır.')
        with self.engine.begin() as c:
            c.execute(text('INSERT INTO users VALUES (:email,:name,:password) ON CONFLICT (email) DO NOTHING'), dict(email=self.teacher_email, name='Müəllim', password=password_hash(password)))

    def login(self, email, password):
        email = email.strip().lower()
        user = self.rows('SELECT * FROM users WHERE email=:email', email=email)
        if not user or not password_ok(password, user[0]['password']):
            return None
        return {'email': email, 'name': user[0]['name'], 'teacher': email == self.teacher_email}

    def require_teacher(self, email):
        if not self.teacher_email or email != self.teacher_email:
            raise PermissionError('Müəllim səlahiyyəti tələb olunur.')

    def questions(self):
        return self.rows('SELECT * FROM questions WHERE active=1 ORDER BY topic,id')

    def save_question(self, email, q):
        self.require_teacher(email)
        options = q['options']
        if not q['prompt'].strip() or len(options) != 4 or not all(str(x).strip() for x in options) or int(q['answer']) not in range(4) or int(q['points']) < 1:
            raise ValueError('Sual, dörd variant, düzgün cavab (0–3) və müsbət bal tələb olunur.')
        with self.engine.begin() as c:
            c.execute(text('INSERT INTO questions VALUES (:id,:topic,:prompt,:options,:answer,:points,:explanation,1) ON CONFLICT (id) DO UPDATE SET topic=:topic,prompt=:prompt,options=:options,answer=:answer,points=:points,explanation=:explanation,active=1'), dict(id=q.get('id') or secrets.token_hex(12), topic=q['topic'], prompt=q['prompt'], options=json.dumps(options), answer=int(q['answer']), points=int(q['points']), explanation=q.get('explanation','')))

    def remove_question(self, email, qid):
        self.require_teacher(email)
        with self.engine.begin() as c:
            c.execute(text('UPDATE questions SET active=0 WHERE id=:id'), {'id': qid})

    def duration(self):
        return self.rows('SELECT duration FROM settings WHERE id=1')[0]['duration']

    def set_duration(self, email, duration):
        self.require_teacher(email)
        if not 1 <= duration <= 180:
            raise ValueError('Müddət 1–180 dəqiqə olmalıdır.')
        with self.engine.begin() as c:
            c.execute(text('UPDATE settings SET duration=:duration WHERE id=1'), {'duration': duration})

    def start(self, email, topic):
        active = self.rows('SELECT * FROM attempts WHERE email=:email AND result IS NULL ORDER BY started DESC', email=email)
        if active:
            return active[0]['id']
        qs = [q for q in self.questions() if topic == 'Hamısı' or q['topic'] == topic]
        if not qs:
            raise ValueError('Bu mövzuda sual yoxdur.')
        secrets.SystemRandom().shuffle(qs)
        aid, now = secrets.token_hex(16), time.time()
        with self.engine.begin() as c:
            c.execute(text('INSERT INTO attempts VALUES (:id,:email,:started,:deadline,:questions,:answers,NULL)'), dict(id=aid,email=email,started=now,deadline=now+self.duration()*60,questions=json.dumps(qs),answers='{}'))
        return aid

    def attempt(self, email, aid):
        rows = self.rows('SELECT * FROM attempts WHERE id=:id AND email=:email', id=aid,email=email)
        if not rows:
            raise PermissionError('Test tapılmadı.')
        a = rows[0]
        for k in ['questions','answers','result']:
            a[k] = json.loads(a[k]) if a[k] else None
        return a

    def public_attempt(self, email, aid):
        a = self.attempt(email,aid)
        if a['result'] is None:
            a['questions'] = [{k:v for k,v in q.items() if k not in ('answer','explanation')} for q in a['questions']]
        return a

    def answer(self, email, aid, index, choice):
        a = self.attempt(email,aid)
        if a['result'] is not None or time.time() >= a['deadline']:
            return False
        if index not in range(len(a['questions'])) or choice not in range(4):
            raise ValueError('Yanlış cavab.')
        a['answers'][str(index)] = choice
        with self.engine.begin() as c:
            c.execute(text('UPDATE attempts SET answers=:answers WHERE id=:id AND email=:email AND result IS NULL AND deadline>:now'), dict(answers=json.dumps(a['answers']),id=aid,email=email,now=time.time()))
        return True

    def finish(self, email, aid):
        a = self.attempt(email,aid)
        if a['result'] is not None:
            return a['result']
        total = sum(q['points'] for q in a['questions'])
        score = sum(q['points'] for i,q in enumerate(a['questions']) if a['answers'].get(str(i)) == q['answer'])
        result = dict(score=score,total=total,percent=round(score/total*100,1),finished=datetime.now(timezone.utc).isoformat())
        with self.engine.begin() as c:
            c.execute(text('UPDATE attempts SET result=:result WHERE id=:id AND email=:email AND result IS NULL'), dict(result=json.dumps(result),id=aid,email=email))
        return self.attempt(email,aid)['result']

    def results(self, email, teacher=False):
        if teacher:
            self.require_teacher(email)
            return self.rows('SELECT a.*,u.name FROM attempts a JOIN users u ON a.email=u.email WHERE a.result IS NOT NULL ORDER BY started DESC')
        return self.rows('SELECT * FROM attempts WHERE email=:email AND result IS NOT NULL ORDER BY started DESC',email=email)
