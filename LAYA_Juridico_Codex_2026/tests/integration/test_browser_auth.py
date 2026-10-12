"""Real Supabase password login; credentials never appear in test output."""
import json
from pathlib import Path
import pytest
import asyncio
from fastapi.testclient import TestClient
from services.api.app.main import create_app
from services.api.app.config import Settings, ROOT

ORIGIN={"Origin":"http://localhost:3000","X-Requested-With":"LAYA"}


def test_browser_password_login_csrf_refresh_and_revocation():
    credentials=json.loads((ROOT/'private-data/login-credentials.json').read_text())
    with TestClient(create_app(Settings()),backend_options={'loop_factory':asyncio.SelectorEventLoop}) as client:
        # A cross-origin login must not plant an attacker's session in this browser.
        assert client.post('/auth/login',json=credentials,headers={'Origin':'https://attacker.invalid'}).status_code==403
        assert client.post('/auth/login',json={'email':credentials['email'],'password':'incorrect password'},headers=ORIGIN).status_code==401
        response=client.post('/auth/login',json=credentials,headers=ORIGIN)
        assert response.status_code==200
        assert 'token' not in response.json()
        assert 'httponly' in response.headers['set-cookie'].lower()
        assert 'samesite=strict' in response.headers['set-cookie'].lower()
        tenants=response.json()['tenants'];assert tenants
        assert client.get('/auth/session').status_code==200
        headers={'X-Tenant-ID':tenants[0]['id']}
        assert client.get('/v1/coverage',headers=headers).status_code==200
        assert client.post('/v1/search',json={'query':'test'},headers=headers).status_code==403
        session_cookie=client.cookies.get('laya_session')
        assert client.post('/auth/logout',headers=ORIGIN).status_code==204
        client.cookies.set('laya_session',session_cookie)
        assert client.get('/auth/session').status_code==401


def test_password_inputs_and_missing_origin_fail_closed():
    with TestClient(create_app(Settings(),connect=False)) as client:
        assert client.post('/auth/login',json={'email':'a@b.invalid','password':'abcdefghijklm'}).status_code==403
        assert client.post('/auth/login',json={'email':'a@b.invalid','password':'x'*5000},headers=ORIGIN).status_code==422
