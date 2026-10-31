import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
from core import Academy


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
    app.sidebar.radio[0].set_value('Testlər').run()
    next(b for b in app.button if b.label=='Testə başla').click().run()
    assert not app.exception
    assert any('Qalan vaxt'==m.label for m in app.metric)
    answer=next(r for r in app.radio if r.label=='Cavabınızı seçin')
    answer.set_value(0).run()
    next(c for c in app.checkbox if c.label=='Testi bitirmək istəyirəm').check().run()
    next(b for b in app.button if b.label=='Testi bitir').click().run()
    assert not app.exception
    assert any(m.label=='Nəticə' for m in app.metric)


def test_teacher_panel(tmp_path,monkeypatch):
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
    assert len(app.selectbox[0].options)==7
