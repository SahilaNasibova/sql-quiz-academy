import json
import time
import pytest
from core import Academy

@pytest.fixture
def db(tmp_path):
    academy=Academy(f'sqlite:///{tmp_path}/test.db','teacher@example.com')
    academy.provision_teacher('teacher-password')
    academy.register('Student One','student@example.com','student-password')
    academy.save_question('teacher@example.com',dict(topic='SQL',prompt='SELECT 1 FROM dual',options=['1','2','3','4'],answer=0,points=3,explanation='One'))
    return academy


def test_registration_and_authorization(db):
    assert db.login('student@example.com','wrong') is None
    assert not db.login('student@example.com','student-password')['teacher']
    assert db.login('teacher@example.com','teacher-password')['teacher']
    with pytest.raises(ValueError):
        db.register('Fake Teacher','TEACHER@example.com','fake-password')
    with pytest.raises(PermissionError):
        db.set_duration('student@example.com',50)
    with pytest.raises(PermissionError):
        db.results('student@example.com',teacher=True)


def test_score_privacy_and_idempotency(db):
    aid=db.start('student@example.com','SQL')
    assert db.start('student@example.com','SQL')==aid
    q=db.public_attempt('student@example.com',aid)['questions'][0]
    assert 'answer' not in q and 'explanation' not in q
    with pytest.raises(PermissionError):
        db.attempt('other@example.com',aid)
    assert db.answer('student@example.com',aid,0,0)
    result=db.finish('student@example.com',aid)
    assert result['score']==3 and result['percent']==100
    assert not db.answer('student@example.com',aid,0,1)
    assert db.finish('student@example.com',aid)==result
    assert db.public_attempt('student@example.com',aid)['questions'][0]['answer']==0


def test_deadline_is_enforced_server_side(db):
    aid=db.start('student@example.com','SQL')
    with db.engine.begin() as c:
        from sqlalchemy import text
        c.execute(text('UPDATE attempts SET deadline=:deadline WHERE id=:id'),dict(deadline=time.time()-1,id=aid))
    assert not db.answer('student@example.com',aid,0,0)
    assert db.finish('student@example.com',aid)['score']==0


def test_question_snapshot_survives_edit(db):
    aid=db.start('student@example.com','SQL')
    q=db.questions()[0]
    q['options']=json.loads(q['options'])
    q['answer']=1
    db.save_question('teacher@example.com',q)
    db.answer('student@example.com',aid,0,0)
    assert db.finish('student@example.com',aid)['score']==3


def test_wrong_answer_and_teacher_results(db):
    aid=db.start('student@example.com','SQL')
    db.answer('student@example.com',aid,0,3)
    assert db.finish('student@example.com',aid)['percent']==0
    assert len(db.results('teacher@example.com',teacher=True))==1
    assert len(db.results('student@example.com'))==1


def test_session_persists_across_database_instances_and_stores_only_hash(db):
    token=db.create_session('student@example.com')
    stored=db.rows('SELECT * FROM sessions')
    assert stored[0]['token_hash'] != token
    assert token not in json.dumps(stored)
    restored=Academy(str(db.engine.url),'teacher@example.com')
    assert restored.session_user(token)==dict(email='student@example.com',name='Student One',teacher=False)
    assert restored.session_user('student@example.com') is None
    assert restored.session_user(token+'tampered') is None
    db.revoke_session(token)
    assert restored.session_user(token) is None


def test_expired_session_is_rejected_and_cleaned_up(db):
    from sqlalchemy import text
    token=db.create_session('teacher@example.com')
    assert db.session_user(token)['teacher']
    with db.engine.begin() as c:
        c.execute(text('UPDATE sessions SET expires=:now'),{'now':time.time()-1})
    assert db.session_user(token) is None
    db.create_session('student@example.com')
    assert len(db.rows('SELECT * FROM sessions'))==1


def test_existing_teacher_does_not_rehash_password(db,monkeypatch):
    def unexpected_hash(*args,**kwargs):
        raise AssertionError('Existing teacher should not be hashed again')
    monkeypatch.setattr('core.password_hash',unexpected_hash)
    db.provision_teacher('another-long-password')


def test_topic_catalog_and_result_summaries(db):
    assert db.topic_catalog()==[{'topic':'SQL','count':1}]
    aid=db.start('student@example.com','SQL')
    db.finish('student@example.com',aid)
    rows=db.result_summaries('student@example.com')
    assert len(rows)==1 and set(rows[0])=={'result'}



def test_deletion_purges_active_and_completed_attempts_and_regrades(db):
    db.save_question('teacher@example.com',dict(topic='SQL',prompt='Keep this question',options=['A','B','C','D'],answer=2,points=2,explanation='Keep explanation'))
    delete_id=next(q['id'] for q in db.questions() if q['prompt']=='SELECT 1 FROM dual')
    finished=db.start('student@example.com','SQL')
    for i,q in enumerate(db.attempt('student@example.com',finished)['questions']):
        db.answer('student@example.com',finished,i,0 if q['id']==delete_id else 1)
    assert db.finish('student@example.com',finished)['score']==3
    active=db.start('teacher@example.com','SQL')
    for i,q in enumerate(db.attempt('teacher@example.com',active)['questions']):
        db.answer('teacher@example.com',active,i,q['answer'])
    db.remove_question('teacher@example.com',delete_id)
    for email,aid in [('student@example.com',finished),('teacher@example.com',active)]:
        attempt=db.attempt(email,aid)
        assert len(attempt['questions'])==1
        assert delete_id not in json.dumps(attempt['questions'])
        assert set(attempt['answers'])=={'0'}
    result=db.attempt('student@example.com',finished)['result']
    assert result['score']==0 and result['total']==2 and result['percent']==0
    assert db.finish('teacher@example.com',active)['score']==2
    assert db.topic_catalog()==[{'topic':'SQL','count':1}]
    assert all(delete_id not in row['questions'] for row in db.results('teacher@example.com',teacher=True))


def test_deleting_last_question_removes_empty_results_and_requires_teacher(db):
    aid=db.start('student@example.com','SQL')
    db.finish('student@example.com',aid)
    q=db.questions()[0]
    with pytest.raises(PermissionError):
        db.remove_question('student@example.com',q['id'])
    assert db.questions()
    db.remove_question('teacher@example.com',q['id'])
    assert not db.questions() and not db.topic_catalog()
    assert not db.results('student@example.com') and not db.result_summaries('student@example.com')
    with pytest.raises(PermissionError):
        db.attempt('student@example.com',aid)
    q['options']=json.loads(q['options'])
    with pytest.raises(ValueError):
        db.save_question('teacher@example.com',q)


def test_legacy_deleted_questions_are_cleaned_on_upgrade(db):
    from sqlalchemy import text
    aid=db.start('student@example.com','SQL')
    with db.engine.begin() as c:
        c.execute(text('UPDATE questions SET active=0'))
        c.execute(text("DELETE FROM maintenance WHERE name='purge_deleted_v1'"))
    restored=Academy(str(db.engine.url),'teacher@example.com')
    assert restored.active_attempt('student@example.com') is None
    with pytest.raises(PermissionError):
        restored.attempt('student@example.com',aid)


def test_answer_from_stale_question_cannot_apply_to_another_question(db):
    db.save_question('teacher@example.com',dict(topic='SQL',prompt='Keep',options=['A','B','C','D'],answer=2,points=2,explanation=''))
    aid=db.start('student@example.com','SQL')
    first=db.attempt('student@example.com',aid)['questions'][0]
    db.remove_question('teacher@example.com',first['id'])
    assert not db.answer('student@example.com',aid,0,1,question_id=first['id'])
    assert db.attempt('student@example.com',aid)['answers']=={}
