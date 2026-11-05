"""Ephemeral login browser. Credentials stay in process environment/memory."""
import asyncio
import json
import os
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
from ...config import get_settings
from ...services.xhs_service import normalize_xhs_cookie

router = APIRouter()
lock = asyncio.Lock()
browser = context = page = driver = task = None
last_sync = None
status = "not_logged_in"
manual_override = False

async def authorize(authorization: str = Header(default="")):
    token = os.getenv("ADMIN_TOKEN", "")
    if not token or not secrets.compare_digest(authorization, "Bearer " + token):
        raise HTTPException(401, "Set ADMIN_TOKEN and supply a valid Bearer token")

@router.get('/api/public/config.js')
async def public_config():
    cfg = json.dumps({"amapKey": os.getenv('VITE_AMAP_WEB_JS_KEY', '')})
    security = json.dumps({"securityJsCode": os.getenv('VITE_AMAP_SECURITY_JS_CODE', '')})
    return Response(f'window.__TRAVEL_CONFIG__={cfg};window._AMapSecurityConfig={security};', media_type='application/javascript', headers={'Cache-Control':'no-store'})

@router.get('/account')
async def account_page():
    return FileResponse(Path(__file__).with_name('account.html'))

async def sync():
    global last_sync, status
    if manual_override:
        return
    cookies = await context.cookies('https://www.xiaohongshu.com')
    if any(c['name'] == 'web_session' and c['value'] for c in cookies):
        value = '; '.join(f"{c['name']}={c['value']}" for c in cookies)
        changed = value != get_settings().xhs_cookie
        os.environ['XHS_COOKIE'] = value
        get_settings().xhs_cookie = value
        last_sync = datetime.now(timezone.utc).isoformat()
        if changed or status in ('login_required', 'not_logged_in'):
            status = 'cookie_synced_unverified'
    else:
        status = 'login_required'

async def watch():
    while True:
        await asyncio.sleep(30)
        async with lock:
            if context is None:
                return
            try:
                await sync()
            except Exception:
                continue

@router.post('/api/account/login', dependencies=[Depends(authorize)])
async def login():
    global driver, browser, context, page, task, status, manual_override
    async with lock:
        manual_override = False
        try:
            if page is None:
                from playwright.async_api import async_playwright
                driver = await async_playwright().start()
                browser = await driver.chromium.launch(headless=True, args=['--no-sandbox'])
                context = await browser.new_context(viewport={'width':1000,'height':750}, locale='zh-CN')
                page = await context.new_page()
                task = asyncio.create_task(watch())
            await page.goto('https://www.xiaohongshu.com', wait_until='domcontentloaded', timeout=45000)
            await sync()
        except Exception as exc:
            raise HTTPException(502, f'登录浏览器启动或页面访问失败：{type(exc).__name__}: {exc}') from exc
    return {'status':status}

class CookieImport(BaseModel):
    cookie: str = Field(min_length=1, max_length=20000)

@router.post('/api/account/cookie', dependencies=[Depends(authorize)])
async def import_cookie(data: CookieImport):
    """Manual fallback when the headless login page cannot complete verification."""
    global status, last_sync, manual_override
    value = normalize_xhs_cookie(data.cookie)
    pairs = dict(part.strip().split('=', 1) for part in value.split(';') if '=' in part)
    if not pairs.get('web_session'):
        raise HTTPException(422, 'Cookie 缺少 web_session，请从已登录的小红书网页复制完整 Cookie')
    async with lock:
        manual_override = True
        os.environ['XHS_COOKIE'] = value
        get_settings().xhs_cookie = value
        last_sync = datetime.now(timezone.utc).isoformat()
        status = 'cookie_synced_unverified'
    return {'status': status, 'configured': True}

@router.get('/api/account/screenshot', dependencies=[Depends(authorize)])
async def screenshot():
    async with lock:
        if page is None:
            raise HTTPException(409, 'Start login first')
        return Response(await page.screenshot(type='png'), media_type='image/png', headers={'Cache-Control':'no-store'})

class Action(BaseModel):
    x: float = Field(default=0, ge=0, le=1000)
    y: float = Field(default=0, ge=0, le=750)
    text: str = Field(default='', max_length=500)
    kind: str = 'click'

@router.post('/api/account/action', dependencies=[Depends(authorize)])
async def action(data: Action):
    async with lock:
        if page is None:
            raise HTTPException(409, 'Start login first')
        if data.kind == 'click':
            await page.mouse.click(data.x, data.y)
        elif data.kind == 'text':
            await page.keyboard.insert_text(data.text)
        else:
            raise HTTPException(400, 'Unknown action')
        await sync()
    return {'status':status}

@router.get('/api/account/status', dependencies=[Depends(authorize)])
async def state():
    if context is not None:
        async with lock:
            await sync()
    return {'status':status, 'last_sync':last_sync, 'configured':bool(get_settings().xhs_cookie)}

@router.post('/api/account/check', dependencies=[Depends(authorize)])
async def check():
    global status
    from ...services.xhs_service import get_xhs_client, XHSCookieExpiredError
    try:
        await asyncio.to_thread(get_xhs_client().search_notes, '杭州旅游', page_size=1)
        status = 'available'
    except XHSCookieExpiredError:
        status = 'login_or_verification_required'
    except Exception:
        status = 'request_failed'
    return {'status':status}

@router.delete('/api/account/login', dependencies=[Depends(authorize)])
async def logout():
    global driver, browser, context, page, task, status, last_sync, manual_override
    async with lock:
        if task:
            task.cancel()
        if browser:
            await browser.close()
        if driver:
            await driver.stop()
        driver = browser = context = page = task = None
        get_settings().xhs_cookie = ''
        os.environ.pop('XHS_COOKIE', None)
        status, last_sync = 'not_logged_in', None
        manual_override = False
    return {'status':status}

