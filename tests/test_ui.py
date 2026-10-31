import json
import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from core import Academy


@pytest.fixture(autouse=True)
def browser_storage_stub(monkeypatch):
    # AppTest does not run component JavaScript. Real browser coverage is separate.
    def acknowledge(command, **kwargs):
        return dict(id=command['id'], ok=True, token=None) if command else None
    monkeypatch.setattr('auth._cookie_writer', acknowledge)


def test_login_dashboard_quiz_and_results(tmp_path,monkeypatch):
    url=f'sqlite:///{tmp_path}/ui.db'
    monkeypatch.setenv('DATABASE_URL',url)
    monkeypatch.setenv('TEACHER_EMAIL','teacher@example.com')
    db=Academy(url,'teacher@example.com')
    db.register('Student One','student@example.com','student-password')
    db.provision_teacher('teacher-password')
    for q in json.loads(Path('sample_questions.json').read_text()):
        db.save_question('teacher@example.com',q)
    app=AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py').run(timeout=20)
    assert not app.exception
    app.text_input[0].set_value('student@example.com')
    app.text_input[1].set_value('student-password')
    app.button[0].click().run()
    assert not app.exception
    assert app.title[0].value=='SQL öyrən, biliklərini sına!'
    next(b for b in app.button if b.label=='▶  Testə başla').click().run()
    assert app.sidebar.radio[0].value=='Testlər'
    assert not app.exception
    assert any('Qalan vaxt'==m.label for m in app.metric)
    answer=next(r for r in app.radio if r.label=='Cavabınızı seçin')
    answer.set_value(0).run()
    next(c for c in app.checkbox if c.label=='Testi bitirmək istəyirəm').check().run()
    next(b for b in app.button if b.label=='Testi bitir').click().run()
    assert not app.exception
    assert any(m.label=='Nəticə' for m in app.metric)


def test_teacher_panel(tmp_path,monkeypatch):
    teacher_result_queries=[]
    original_results=Academy.results
    def tracked_results(self,email,teacher=False):
        if teacher:
            teacher_result_queries.append(email)
        return original_results(self,email,teacher=teacher)
    monkeypatch.setattr(Academy,'results',tracked_results)
    monkeypatch.setenv('DATABASE_URL',f'sqlite:///{tmp_path}/teacher.db')
    monkeypatch.setenv('TEACHER_EMAIL','teacher@example.com')
    monkeypatch.setenv('TEACHER_PASSWORD','teacher-password')
    app=AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py').run()
    app.text_input[0].set_value('teacher@example.com')
    app.text_input[1].set_value('teacher-password')
    app.button[0].click().run()
    app.sidebar.radio[0].set_value('Müəllim paneli').run()
    assert not app.exception
    next(b for b in app.button if b.label=='Nümunə sualları əlavə et').click().run()
    assert not app.exception
    edit = next(widget for widget in app.selectbox if widget.label=='Redaktə üçün sual')
    assert len(edit.options)==7
    delete = next(button for button in app.button if button.label=='Sualı sil')
    assert delete.disabled
    next(widget for widget in app.checkbox if widget.label=='Seçilmiş sualı silməyi təsdiqləyirəm').check().run()
    delete = next(button for button in app.button if button.label=='Sualı sil')
    assert not delete.disabled
    delete.click().run()
    assert not app.exception
    edit = next(widget for widget in app.selectbox if widget.label=='Redaktə üçün sual')
    assert len(edit.options)==6
    assert any(message.value=='Sual silindi.' for message in app.success)
    assert next(button for button in app.button if button.label=='Sualı sil').disabled

    assert not teacher_result_queries, 'Closed statistics tab must not load all results'



def test_logo_returns_home_and_question_bank_search(tmp_path,monkeypatch):
    monkeypatch.setenv('DATABASE_URL',f'sqlite:///{tmp_path}/navigation.db')
    monkeypatch.setenv('TEACHER_EMAIL','teacher@example.com')
    monkeypatch.setenv('TEACHER_PASSWORD','teacher-password')
    app=AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py').run()
    next(t for t in app.text_input if t.label=='E-poçt').set_value('teacher@example.com')
    next(t for t in app.text_input if t.label=='Şifrə').set_value('teacher-password')
    next(b for b in app.button if b.label=='Daxil ol').click().run()
    app.sidebar.radio[0].set_value('Müəllim paneli').run()
    next(b for b in app.button if b.label=='Nümunə sualları əlavə et').click().run()
    next(t for t in app.text_input if t.label=='Sual axtar').set_value('NVL').run()
    delete_selector=next(t for t in app.selectbox if t.label=='Silmək üçün sual')
    assert len(delete_selector.options)==1 and 'NVL' in delete_selector.options[0]
    next(b for b in app.sidebar.button if b.label=='▱ SQL Quiz Academy').click().run()
    assert app.sidebar.radio[0].value=='İcmal'
    assert app.title[0].value=='SQL öyrən, biliklərini sına!'
    assert not app.exception


def test_removed_active_quiz_recovers_without_error(tmp_path,monkeypatch):
    url=f'sqlite:///{tmp_path}/removed.db'
    monkeypatch.setenv('DATABASE_URL',url)
    monkeypatch.setenv('TEACHER_EMAIL','teacher@example.com')
    db=Academy(url,'teacher@example.com')
    db.register('Test Student','student@example.com','student-password')
    db.save_question('teacher@example.com',dict(topic='SQL',prompt='Remove me',options=['A','B','C','D'],answer=0,points=1,explanation=''))
    qid=db.questions()[0]['id']
    app=AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py').run()
    next(t for t in app.text_input if t.label=='E-poçt').set_value('student@example.com')
    next(t for t in app.text_input if t.label=='Şifrə').set_value('student-password')
    next(b for b in app.button if b.label=='Daxil ol').click().run()
    next(b for b in app.button if b.label=='▶  Testə başla').click().run()
    db.remove_question('teacher@example.com',qid)
    app.run()
    assert not app.exception
    assert any('bütün sualları' in message.value for message in app.info)
    assert not any('Remove me' in value.value for value in app.markdown)


def test_stale_imported_database_class_is_reloaded(tmp_path,monkeypatch):
    import core
    import hashlib
    monkeypatch.setenv('DATABASE_URL',f'sqlite:///{tmp_path}/upgrade.db')
    monkeypatch.setenv('TEACHER_PASSWORD','')
    # Reproduce an older imported module surviving a deployed source update.
    monkeypatch.setattr(core,'SOURCE_REVISION','old-deployment')
    monkeypatch.setattr(core,'Academy',type('LegacyAcademy',(),{}))
    app=AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py').run()
    assert not app.exception and not app.error
    assert hasattr(core.Academy,'active_attempt')
    assert core.SOURCE_REVISION==hashlib.sha256(Path(core.__file__).read_bytes()).hexdigest()
    assert any(button.label=='Daxil ol' for button in app.button)
