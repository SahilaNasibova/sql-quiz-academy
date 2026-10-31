"""Opaque, revocable database sessions persisted through a same-origin cookie."""
import secrets
import time
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from core import SESSION_SECONDS

COOKIE_NAME = 'sql_academy_session'
_cookie_writer = components.declare_component(
    'academy_session_cookie', path=str(Path(__file__).parent / 'components' / 'session_cookie')
)


def sync_login(db):
    command = st.session_state.get('_cookie_command')
    acknowledgement = _cookie_writer(command=command, key='academy_cookie', default=None)
    if command and acknowledgement and acknowledgement.get('id') == command['id']:
        del st.session_state['_cookie_command']
        if not acknowledgement.get('ok'):
            st.warning('Brauzer giriş kukisini saxlaya bilmədi. Kukilərə icazə verin; əks halda səhifə yenilənəndə yenidən giriş lazım olacaq.')

    # Request cookies are captured when the browser opens a new WebSocket.
    # Restore identity from the database, never from an email or role in the cookie.
    token = st.session_state.get('_session_token') or st.context.cookies.get(COOKIE_NAME)
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
    token = st.session_state.get('_session_token') or st.context.cookies.get(COOKIE_NAME)
    if token:
        db.revoke_session(token)
    st.session_state.clear()
    st.session_state['_cookie_command'] = dict(id=secrets.token_hex(8), action='delete')
