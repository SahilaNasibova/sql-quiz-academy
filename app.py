import io
import json
import os
import time
from pathlib import Path
import pandas as pd
import streamlit as st
from sqlalchemy.exc import IntegrityError
from core import Academy
from ui import CSS, dashboard
from auth import sync_login, remember_login, logout

st.set_page_config(page_title='SQL Quiz Academy', page_icon='🎓', layout='wide')
st.markdown(CSS, unsafe_allow_html=True)

def config(key, default=''):
    value = os.environ.get(key)
    if value is not None:
        return value
    try:
        return st.secrets.get(key, default)
    except FileNotFoundError:
        return default

@st.cache_resource
def database(url, teacher, teacher_password):
    academy = Academy(url, teacher)
    if teacher_password:
        academy.provision_teacher(teacher_password)
    return academy

url = config('DATABASE_URL', f'sqlite:///{Path(__file__).resolve().parent / "academy.db"}')
try:
    db = database(url, config('TEACHER_EMAIL', 'sahila.nasibova1@gmail.com'), config('TEACHER_PASSWORD'))
except Exception:
    st.error('Verilənlər bazasına bağlantı qurulmadı. Administrator DATABASE_URL konfiqurasiyasını yoxlamalıdır.')
    st.stop()

st.sidebar.markdown('<div class="brand"><span>▱</span>SQL Quiz<br>Academy</div>', unsafe_allow_html=True)

sync_login(db)

if 'user' not in st.session_state:
    st.title('SQL Quiz Academy')
    st.caption('Oracle SQL və PL/SQL üzrə öyrənmə məkanınız')
    login, register = st.tabs(['Giriş', 'Qeydiyyat'])
    with login:
        st.caption('Giriş bu brauzerdə 7 gün yadda saxlanır. Ortaq cihazda işiniz bitdikdə Çıxış edin.')
        with st.form('login'):
            email = st.text_input('E-poçt')
            password = st.text_input('Şifrə', type='password')
            submitted = st.form_submit_button('Daxil ol', type='primary')
        if submitted:
            now = time.time()
            if now < st.session_state.get('login_after', 0):
                st.error('Növbəti cəhddən əvvəl bir neçə saniyə gözləyin.')
            else:
                st.session_state.login_after = now + 3
                user = db.login(email,password)
                if user:
                    remember_login(db, user)
                    st.rerun()
                st.error('E-poçt və ya şifrə yanlışdır.')
    with register:
        with st.form('register'):
            name = st.text_input('Ad və soyad')
            email = st.text_input('E-poçt', key='reg_email')
            password = st.text_input('Şifrə (ən azı 10 simvol)', type='password', key='reg_password')
            confirmation = st.text_input('Şifrəni təkrar edin', type='password')
            submitted = st.form_submit_button('Qeydiyyatdan keç')
        if submitted:
            try:
                if password != confirmation:
                    raise ValueError('Şifrələr uyğun deyil.')
                db.register(name,email,password)
                st.success('Qeydiyyat tamamlandı. Giriş bölməsindən daxil olun.')
            except ValueError as e:
                st.error(str(e))
            except IntegrityError:
                st.error('Bu e-poçt artıq qeydiyyatdadır.')
    st.stop()

user = st.session_state.user
st.sidebar.write(f"**{user['name']}**")
st.sidebar.caption('Müəllim' if user['teacher'] else 'Tələbə')
if st.sidebar.button('Çıxış'):
    logout(db)
    st.rerun()
page = st.sidebar.radio('Bölmələr', ['İcmal','Testlər','Nəticələr'] + (['Müəllim paneli'] if user['teacher'] else []), key='navigation')


def show_result(a):
    r = a['result']
    c1,c2 = st.columns(2)
    c1.metric('Bal',f"{r['score']} / {r['total']}")
    c2.metric('Nəticə',f"{r['percent']}%")
    for i,q in enumerate(a['questions']):
        with st.expander(f"{i+1}. {q['topic']} · {q['points']} bal"):
            st.markdown(q['prompt'])
            opts = json.loads(q['options'])
            chosen = a['answers'].get(str(i))
            st.write('Sizin cavabınız: ' + (opts[chosen] if chosen is not None else 'Cavablandırılmayıb'))
            st.success('Düzgün cavab: ' + opts[q['answer']])
            st.write(q['explanation'])


if page == 'İcmal':
    def start_topic(topic):
        st.session_state.attempt_id = db.start(user['email'], topic)
        st.session_state.question_index = 0
        st.session_state.navigation = 'Testlər'
    dashboard(db, user, start_topic)

elif page == 'Testlər':
    st.header('Biliklərini yoxla')
    aid = st.session_state.get('attempt_id')
    if not aid:
        active = db.rows('SELECT id FROM attempts WHERE email=:email AND result IS NULL ORDER BY started DESC', email=user['email'])
        if active:
            aid = active[0]['id']
            st.session_state.attempt_id = aid
    if not aid:
        questions = db.questions()
        if not questions:
            st.info('Hələ test əlavə edilməyib. Müəllim panelindən nümunə sualları əlavə etmək olar.')
        else:
            topics = ['Hamısı'] + sorted({q['topic'] for q in questions})
            topic = st.selectbox('Mövzu',topics)
            st.write(f'Müddət: {db.duration()} dəqiqə. Test başlayanda vaxt serverdə qeydə alınır.')
            if st.button('Testə başla',type='primary'):
                st.session_state.attempt_id = db.start(user['email'],topic)
                st.session_state.question_index = 0
                st.rerun()
    else:
        @st.fragment(run_every=1.0)
        def countdown(deadline):
            if time.time() >= deadline:
                db.finish(user['email'], aid)
                st.rerun()
            remaining = max(0, int(deadline-time.time()))
            st.metric('Qalan vaxt', f'{remaining//60:02d}:{remaining%60:02d}')

        def quiz():
            a = db.public_attempt(user['email'],aid)
            if a['result'] is None and time.time() >= a['deadline']:
                db.finish(user['email'],aid)
                st.rerun()
            if a['result'] is not None:
                show_result(a)
                if st.button('Yeni test'):
                    del st.session_state.attempt_id
                    st.rerun()
                return
            countdown(a['deadline'])
            i = min(st.session_state.get('question_index',0),len(a['questions'])-1)
            q = a['questions'][i]
            st.progress((i+1)/len(a['questions']), text=f"Sual {i+1} / {len(a['questions'])}")
            st.caption(f"{q['topic']} · {q['points']} bal")
            st.markdown(q['prompt'])
            opts = json.loads(q['options'])
            chosen = st.radio('Cavabınızı seçin', range(4), index=a['answers'].get(str(i)), format_func=lambda x:f"{'ABCD'[x]}. {opts[x]}", key=f'{aid}_{i}')
            if chosen is not None and chosen != a['answers'].get(str(i)):
                db.answer(user['email'],aid,i,chosen)
            left, middle, right = st.columns(3)
            if left.button('← Geri', disabled=i==0):
                st.session_state.question_index = i-1
                st.rerun()
            if middle.button('İrəli →', disabled=i==len(a['questions'])-1):
                st.session_state.question_index = i+1
                st.rerun()
            confirm = st.checkbox('Testi bitirmək istəyirəm')
            if right.button('Testi bitir', disabled=not confirm, type='primary'):
                db.finish(user['email'],aid)
                st.rerun()
        quiz()

elif page == 'Nəticələr':
    st.header('Nəticələrim')
    rows = db.results(user['email'])
    if not rows:
        st.info('Hələ tamamlanmış test yoxdur.')
    for row in rows:
        r = json.loads(row['result'])
        with st.expander(f"{r['finished'][:16]} UTC · {r['percent']}% · {r['score']}/{r['total']}"):
            show_result(db.attempt(user['email'],row['id']))

else:
    st.header('Müəllim paneli')
    questions_tab, import_tab, stats_tab = st.tabs(['Suallar və test','Excel / CSV','Statistika'], key='teacher_tabs', on_change='rerun')
    with questions_tab:
        if questions_tab.open:
            duration = st.number_input('Test müddəti (dəqiqə)',1,180,db.duration())
            if st.button('Müddəti yadda saxla'):
                db.set_duration(user['email'],duration)
                st.success('Yadda saxlanıldı.')
            qs = db.questions()
            st.subheader('Sualı sil')
            if qs:
                question_by_id = {item['id']: item for item in qs}
                delete_id = st.selectbox(
                    'Silmək üçün sual', list(question_by_id),
                    format_func=lambda value: f"{question_by_id[value]['topic']} — {question_by_id[value]['prompt'][:100]}",
                    key='delete_question_id',
                )
                st.caption('Sual yeni testlərdən çıxarılacaq. Əvvəlki test nəticələri saxlanacaq.')
                confirmed = st.checkbox(
                    'Seçilmiş sualı silməyi təsdiqləyirəm', key=f'confirm_delete_{delete_id}'
                )
                if st.button('Sualı sil', disabled=not confirmed):
                    db.remove_question(user['email'], delete_id)
                    st.session_state.question_deleted = True
                    st.rerun()
            else:
                st.info('Silmək üçün sual yoxdur.')
            if st.session_state.pop('question_deleted', False):
                st.success('Sual silindi.')
            st.divider()
            st.subheader('Sual əlavə et və ya redaktə et')
            selected = st.selectbox('Redaktə üçün sual', ['Yeni sual']+[q['id'] for q in qs], format_func=lambda x: x if x=='Yeni sual' else next(q['prompt'][:75] for q in qs if q['id']==x))
            q = next((q for q in qs if q['id']==selected),None)
            with st.form(f'question_{selected}'):
                topic = st.text_input('Mövzu',q['topic'] if q else 'Oracle SQL')
                prompt = st.text_area('Sual (Markdown və ```sql kod blokları dəstəklənir)',q['prompt'] if q else '')
                opts = json.loads(q['options']) if q else ['']*4
                options = [st.text_input(f'{letter} variantı',opts[i]) for i,letter in enumerate('ABCD')]
                answer = st.selectbox('Düzgün cavab',range(4),index=q['answer'] if q else 0,format_func=lambda x:'ABCD'[x])
                points = st.number_input('Bal',1,100,int(q['points']) if q else 1)
                explanation = st.text_area('İzah',q['explanation'] if q else '')
                save = st.form_submit_button('Sualı yadda saxla')
            if save:
                try:
                    db.save_question(user['email'],dict(id=q['id'] if q else None,topic=topic,prompt=prompt,options=options,answer=answer,points=points,explanation=explanation))
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
            if st.button('Nümunə sualları əlavə et',disabled=bool(qs)):
                for item in json.loads(Path(__file__).with_name('sample_questions.json').read_text()):
                    db.save_question(user['email'],item)
                st.rerun()
    with import_tab:
        if import_tab.open:
            st.write('Sütunlar: topic, prompt, A, B, C, D, answer (A–D), points, explanation. Yeni suallar əlavə edilir.')
            template = pd.DataFrame([dict(topic='Oracle SQL',prompt='SELECT 1 FROM dual nə qaytarır?',A='1',B='0',C='NULL',D='Xəta',answer='A',points=1,explanation='DUAL bir sətirli cədvəldir.')])
            st.download_button('CSV şablonunu endir',template.to_csv(index=False).encode('utf-8-sig'),'questions.csv','text/csv')
            upload = st.file_uploader('Excel və ya CSV',type=['xlsx','csv'])
            if upload and st.button('Sualları yüklə'):
                try:
                    if upload.size > 5_000_000:
                        raise ValueError('Fayl ən çox 5 MB olmalıdır.')
                    frame = (pd.read_csv(upload,keep_default_na=False) if upload.name.endswith('.csv') else pd.read_excel(upload,keep_default_na=False))
                    required = {'topic','prompt','A','B','C','D','answer','points','explanation'}
                    if not required.issubset(frame.columns) or not 1 <= len(frame) <= 500:
                        raise ValueError('Sütunları yoxlayın; 1–500 sual yükləyə bilərsiniz.')
                    items = []
                    for _,r in frame.iterrows():
                        ans = str(r['answer']).strip().upper()
                        if ans not in list('ABCD') or not all(str(r[k]).strip() for k in ['topic','prompt','A','B','C','D']) or not 1 <= int(r['points']) <= 100:
                            raise ValueError('Variantlar, mövzu, sual, cavab və balı yoxlayın.')
                        items.append(dict(topic=str(r['topic']),prompt=str(r['prompt']),options=[str(r[k]) for k in 'ABCD'],answer='ABCD'.index(ans),points=int(r['points']),explanation=str(r['explanation'])))
                    for item in items:
                        db.save_question(user['email'],item)
                    st.success(f'{len(items)} sual əlavə edildi.')
                except Exception:
                    st.error('Fayl yüklənmədi. Şablona uyğunluğu yoxlayın.')
    with stats_tab:
        if stats_tab.open:
            rows = db.results(user['email'],teacher=True)
            summary, difficulty = [],{}
            for row in rows:
                r = json.loads(row['result'])
                summary.append(dict(Tələbə=row['name'],Email=row['email'],Bal=r['score'],Maksimum=r['total'],Faiz=r['percent'],Tarix=r['finished']))
                answers = json.loads(row['answers'])
                for i,q in enumerate(json.loads(row['questions'])):
                    item = difficulty.setdefault(q['id'],dict(Sual=q['prompt'],Cəhd=0,Düzgün=0))
                    item['Cəhd'] += 1
                    item['Düzgün'] += int(answers.get(str(i)) == q['answer'])
            if summary:
                frame = pd.DataFrame(summary)
                st.dataframe(frame,hide_index=True,use_container_width=True)
                out = io.BytesIO()
                with pd.ExcelWriter(out,engine='openpyxl',engine_kwargs={}) as writer:
                    # Export user-controlled cells as literal text to prevent spreadsheet formulas.
                    safe = frame.map(lambda v: "'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v)
                    safe.to_excel(writer,index=False,sheet_name='Nəticələr')
                st.download_button('Excel nəticələrini endir',out.getvalue(),'results.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                st.subheader('Sualların çətinliyi')
                st.dataframe(pd.DataFrame([dict(**v,Faiz=round(100*v['Düzgün']/v['Cəhd'],1)) for v in difficulty.values()]).sort_values('Faiz'),hide_index=True)
            else:
                st.info('Hələ tamamlanmış test yoxdur.')
