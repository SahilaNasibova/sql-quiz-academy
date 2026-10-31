"""Run with a Python that has Playwright installed and an available Chromium."""
import json
import os
import re
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
PYTHON=str(ROOT/'.venv/bin/python') if (ROOT/'.venv/bin/python').exists() else sys.executable


def main():
    with tempfile.TemporaryDirectory(prefix='academy-browser-') as folder:
        env=dict(os.environ,DATABASE_URL=f'sqlite:///{folder}/browser.db',TEACHER_EMAIL='teacher@example.com',TEACHER_PASSWORD='browser-teacher-password')
        seed="""import json, os
from core import Academy
from pathlib import Path
x=Academy(os.environ['DATABASE_URL'],os.environ['TEACHER_EMAIL'])
x.provision_teacher(os.environ['TEACHER_PASSWORD'])
x.register('Test Student','student@example.com','browser-student-password')
for q in json.loads(Path('sample_questions.json').read_text()):
    x.save_question('teacher@example.com',q)
"""
        subprocess.run([PYTHON,'-c',seed],env=env,cwd=ROOT,check=True)
        # Count database operations without recording SQL parameters or credentials.
        query_log=Path(folder)/'queries.log'
        (Path(folder)/'sitecustomize.py').write_text(
            "from sqlalchemy import event\nfrom sqlalchemy.engine import Engine\n"
            "@event.listens_for(Engine, 'before_cursor_execute')\n"
            "def count_query(*args):\n"
            f"    with open({str(query_log)!r}, 'a') as log: log.write('query\\n')\n"
        )
        # Simulate a hosting proxy that hides cookie headers from Streamlit.
        with (Path(folder)/'sitecustomize.py').open('a') as patch:
            patch.write("from streamlit.runtime.context import ContextProxy, StreamlitCookies\n")
            patch.write("ContextProxy.cookies = property(lambda self: StreamlitCookies({}))\n")
        env['PYTHONPATH']=folder+os.pathsep+env.get('PYTHONPATH','')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        with open(Path(folder)/'server.log','w') as log:
            server=subprocess.Popen([PYTHON,'-m','streamlit','run','app.py','--server.address','127.0.0.1','--server.port',str(port),'--browser.gatherUsageStats','false'],cwd=ROOT,env=env,stdout=log,stderr=log)
            try:
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(base+'/_stcore/health',timeout=.3) as response:
                            if response.status==200: break
                    except OSError: time.sleep(.1)
                else: raise AssertionError('Server failed to start')
                with sync_playwright() as p:
                    executable=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium')
                    browser=p.chromium.launch(headless=True,executable_path=executable,args=['--no-sandbox'])
                    context=browser.new_context()
                    page=context.new_page()
                    page.goto(base)
                    for email,password in [('teacher@example.com','browser-teacher-password'),('student@example.com','browser-student-password')]:
                        print('Checking browser session for', 'teacher' if email.startswith('teacher') else 'student', flush=True)
                        page.get_by_role('textbox',name='E-poçt',exact=True).first.fill(email)
                        page.get_by_role('textbox',name='Şifrə',exact=True).fill(password)
                        page.get_by_role('button',name='Daxil ol',exact=True).click()
                        expect(page.get_by_role('heading',name='SQL öyrən, biliklərini sına!')).to_be_visible(timeout=15000)
                        page.wait_for_function("document.cookie.includes('sql_academy_session=')")
                        original=next(c for c in context.cookies() if c['name']=='sql_academy_session')
                        assert original['sameSite']=='Lax' and original['expires']>time.time()+6*86400
                        # Prove recovery even when only browser local storage survives.
                        context.clear_cookies()
                        for _ in range(2):
                            page.reload()
                            expect(page.get_by_role('heading',name='SQL öyrən, biliklərini sına!')).to_be_visible(timeout=15000)
                        other=context.new_page()
                        other.goto(base)
                        expect(other.get_by_role('heading',name='SQL öyrən, biliklərini sına!')).to_be_visible(timeout=15000)
                        other.close()
                        if email.startswith('teacher'):
                            page.get_by_text('Müəllim paneli',exact=True).click()
                            expect(page.get_by_role('heading',name='Müəllim paneli',exact=True)).to_be_visible()
                            page.get_by_role('tab',name='Statistika',exact=True).click()
                            expect(page.get_by_text('Hələ tamamlanmış test yoxdur.',exact=True)).to_be_visible()
                            page.get_by_role('tab',name='Excel / CSV',exact=True).click()
                            expect(page.get_by_role('button',name='CSV şablonunu endir')).to_be_visible()
                            page.get_by_role('tab',name='Suallar və test',exact=True).click()
                            expect(page.get_by_role('heading',name='Sualı sil',exact=True)).to_be_visible()
                            page.get_by_role('button',name='▱ SQL Quiz Academy',exact=True).click()
                            expect(page.get_by_role('heading',name='SQL öyrən, biliklərini sına!')).to_be_visible()
                        if email.startswith('student'):
                            page.get_by_role('button',name='▶ Testə başla').first.click()
                            expect(page.get_by_text('Qalan vaxt',exact=True)).to_be_visible()
                            before=page.get_by_role('radio').count()
                            page.wait_for_timeout(1000)
                            initial_queries=len(query_log.read_text().splitlines())
                            page.wait_for_timeout(2200)
                            assert len(query_log.read_text().splitlines())==initial_queries, 'Idle timer must not query the database'
                            assert page.get_by_role('radio').count()==before
                            page.get_by_text(re.compile(r'^A\. ')).last.click()
                            expect(page.get_by_text(re.compile('Cavablandırılıb: 1 /'))).to_be_visible()
                            page.reload()
                            expect(page.get_by_role('heading',name='SQL öyrən, biliklərini sına!')).to_be_visible(timeout=15000)
                        page.get_by_role('button',name='Çıxış',exact=True).click()
                        expect(page.get_by_role('button',name='Daxil ol',exact=True)).to_be_visible(timeout=15000)
                        page.wait_for_function("!document.cookie.includes('sql_academy_session=') && !localStorage.getItem('sql_academy_session')")
                        page.reload()
                        expect(page.get_by_role('button',name='Daxil ol',exact=True)).to_be_visible(timeout=15000)
                        # A copied cookie must remain invalid after logout.
                        context.add_cookies([original])
                        page.reload()
                        expect(page.get_by_role('button',name='Daxil ol',exact=True)).to_be_visible(timeout=15000)
                        page.evaluate("localStorage.removeItem('sql_academy_session')")
                        context.clear_cookies()
                    # Mobile-sized browser: the login page remains usable.
                    page.set_viewport_size({'width':390,'height':844})
                    page.reload()
                    expect(page.get_by_role('button',name='Daxil ol',exact=True)).to_be_visible(timeout=15000)
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    browser.close()
                print('Browser checks passed: teacher/student refresh, new tab, logout, revoked-cookie replay, quiz timer, mobile login.')
            finally:
                server.terminate()
                server.wait(timeout=15)


if __name__=='__main__':
    main()
