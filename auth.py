"""Opaque, revocable database sessions persisted through a same-origin cookie."""
import secrets
import time
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from core import SESSION_SECONDS

COOKIE_NAME = 'sql_academy_session'
_cookie_writer = components.declare_component(
    'academy_session_storage_v2', path=str(Path(__file__).parent / 'components' / 'session_cookie')
)


def sync_login(db):
    # Read browser storage on each new WebSocket. Hosting proxies may omit
    # cookies from the headers exposed by st.context.cookies.
    if not st.session_state.get('_browser_ready') and '_cookie_command' not in st.session_state:
        st.session_state['_cookie_command'] = dict(id=secrets.token_hex(8), action='read')
    command = st.session_state.get('_cookie_command')
    acknowledgement = _cookie_writer(command=command, key='academy_cookie', default=None)
    if command:
        if not acknowledgement or acknowledgement.get('id') != command['id']:
            st.info('Giriş yadda saxlanılır…' if command['action']=='set' else 'Giriş yoxlanılır…')
            st.stop()
        del st.session_state['_cookie_command']
        st.session_state['_browser_ready'] = True
        if command['action'] == 'read':
            st.session_state['_browser_token'] = acknowledgement.get('token')
        elif command['action'] == 'delete':
            st.session_state.pop('_browser_token', None)
        if not acknowledgement.get('ok'):
            st.warning('Brauzer girişi yadda saxlaya bilmədi. Bu sayt üçün kukilərə və brauzer yaddaşına icazə verin.')

    token = st.session_state.get('_session_token') or st.session_state.get('_browser_token')
    due = time.time() - st.session_state.get('_session_checked', 0) >= 300
    if token and ('user' not in st.session_state or due):
        user = db.session_user(token)
        st.session_state['_session_checked'] = time.time()
        if user:
            st.session_state.user = user
            st.session_state['_session_token'] = token
        else:
            st.session_state.pop('user', None)
            st.session_state.pop('_session_token', None)
            st.session_state.pop('_browser_token', None)


def remember_login(db, user):
    old = st.session_state.get('_session_token')
    if old:
        db.revoke_session(old)
    token = db.create_session(user['email'])
    st.session_state.user = user
    st.session_state['_session_token'] = token
    st.session_state['_session_checked'] = time.time()
    st.session_state['_cookie_command'] = dict(
        id=secrets.token_hex(8), action='set', token=token, max_age=SESSION_SECONDS
    )


def logout(db):
    token = st.session_state.get('_session_token') or st.session_state.get('_browser_token')
    if token:
        db.revoke_session(token)
    st.session_state.clear()
    st.session_state['_cookie_command'] = dict(id=secrets.token_hex(8), action='delete')
