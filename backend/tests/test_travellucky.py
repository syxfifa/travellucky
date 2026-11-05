"""Offline regression checks for credential boundaries and AMap response parsing."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.routes import account, settings
from app.config import get_settings
from app.services.amap_service import AmapService


def client():
    app = FastAPI()
    app.include_router(account.router)
    app.include_router(settings.router, prefix='/api')
    return TestClient(app)


def test_account_denies_missing_and_wrong_token(monkeypatch):
    monkeypatch.setenv('ADMIN_TOKEN', 'test-only-token')
    with client() as c:
        assert c.get('/api/account/status').status_code == 401
        assert c.get('/api/account/status', headers={'Authorization':'Bearer wrong'}).status_code == 401
        assert c.get('/api/account/status', headers={'Authorization':'Bearer test-only-token'}).status_code == 200


def test_public_config_does_not_return_server_credentials(monkeypatch):
    monkeypatch.setenv('LLM_API_KEY', 'private-model-token')
    monkeypatch.setenv('XHS_COOKIE', 'private-cookie')
    monkeypatch.setenv('VITE_AMAP_WEB_KEY', 'private-map-token')
    monkeypatch.setenv('VITE_AMAP_WEB_JS_KEY', 'public-browser-key')
    with client() as c:
        response = c.get('/api/public/config.js')
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'no-store'
        assert 'public-browser-key' in response.text
        assert 'private-' not in response.text
        assert c.put('/api/settings', json={'xhs_cookie':'secret'}).status_code == 405


def test_poi_skips_missing_location_and_parses_coordinates(monkeypatch):
    monkeypatch.setattr(get_settings(), 'vite_amap_web_key', 'test-only')
    svc = AmapService()
    monkeypatch.setattr(svc, '_request', lambda *a, **kw: {'pois':[
        {'id':'a','name':'故宫','location':'116.397,39.918','type':'景点','address':'北京'},
        {'id':'b','name':'未知','location':''}]})
    result = svc.search_poi('故宫','北京')
    assert len(result) == 1
    assert result[0].location.longitude == 116.397


def test_missing_route_coordinates_do_not_fabricate_route(monkeypatch):
    monkeypatch.setattr(get_settings(), 'vite_amap_web_key', 'test-only')
    svc = AmapService()
    monkeypatch.setattr(svc, 'geocode', lambda *args: None)
    assert svc.plan_route('missing','missing') == {}
