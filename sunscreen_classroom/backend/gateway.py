"""Render serves static assets and relays API calls to the teaching computer."""
from __future__ import annotations

import asyncio
import base64
import hmac
import json
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from backend.catalog import load_catalog

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'frontend/public'
DIST = ROOT / 'frontend/dist'
TOKEN = os.getenv('LOCAL_RELAY_TOKEN', '')
if len(TOKEN) < 32:
    raise RuntimeError('Configure LOCAL_RELAY_TOKEN with at least 32 random characters.')

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
connection: WebSocket | None = None
pending: dict[str, asyncio.Future] = {}
send_lock = asyncio.Lock()
OFFLINE = '授课电脑尚未连接，请老师在电脑上打开“开启公网课堂”。已保存的记录仍在授课电脑中。'


@app.middleware('http')
async def headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'same-origin'
    if request.url.path.startswith('/api') or request.url.path == '/healthz':
        response.headers['Cache-Control'] = 'no-store'
    elif request.url.path.startswith('/assets/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif request.url.path.startswith('/molecules/'):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    return response


@app.get('/healthz')
def health():
    return {'status': 'ok', 'storage': 'local', 'computer_connected': connection is not None}


@app.websocket('/relay/connect')
async def connect(websocket: WebSocket):
    global connection
    authorization = websocket.headers.get('authorization', '')
    if not hmac.compare_digest(authorization.encode(), ('Bearer ' + TOKEN).encode()):
        await websocket.close(code=1008)
        return
    if connection is not None:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    connection = websocket
    try:
        await websocket.send_json({'type': 'ready'})
        while True:
            message = await websocket.receive_json()
            if message.get('type') == 'response':
                future = pending.get(message.get('id'))
                if future is not None and not future.done():
                    future.set_result(message)
    except (WebSocketDisconnect, RuntimeError, ValueError):
        pass
    finally:
        if connection is websocket:
            connection = None
            for future in list(pending.values()):
                if not future.done():
                    future.set_exception(ConnectionError('Teaching computer disconnected.'))


@app.get('/api/catalog')
def catalog():
    return load_catalog(PUBLIC / 'molecules/catalog.json')


@app.api_route('/api/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
async def proxy(path: str, request: Request):
    websocket = connection
    if websocket is None:
        return JSONResponse({'detail': OFFLINE}, status_code=503)
    if len(pending) >= 256:
        return JSONResponse({'detail': '课堂请求较多，请稍后重试。'}, status_code=503)
    body = await request.body()
    if len(body) > 512 * 1024:
        return JSONResponse({'detail': '提交内容过大。'}, status_code=413)
    request_id = secrets.token_hex(16)
    future = asyncio.get_running_loop().create_future()
    pending[request_id] = future
    try:
        async with send_lock:
            await websocket.send_json({
                'type': 'request', 'id': request_id, 'method': request.method,
                'path': '/api/' + path, 'query': request.url.query,
                'headers': {key: value for key, value in request.headers.items()
                            if key.lower() in {'cookie', 'content-type'}},
                'body': base64.b64encode(body).decode('ascii'),
            })
        result = await asyncio.wait_for(future, timeout=20)
        response = Response(base64.b64decode(result['body']), status_code=result['status'])
        for key, value in result['headers']:
            key = key.lower()
            if key in {'content-length', 'transfer-encoding', 'connection', 'content-encoding'}:
                continue
            if key == 'set-cookie' and '; secure' not in value.lower():
                value += '; Secure'
            response.raw_headers.append((key.encode('latin-1'), value.encode('latin-1')))
        response.headers['X-Classroom-Storage'] = 'local'
        return response
    except (ConnectionError, RuntimeError, TimeoutError):
        return JSONResponse({'detail': '授课电脑连接暂时中断，请稍后重试。'}, status_code=503)
    finally:
        pending.pop(request_id, None)
        if not future.done():
            future.cancel()


app.mount('/molecules', StaticFiles(directory=PUBLIC / 'molecules'), name='molecules')
if (DIST / 'assets').exists():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')


@app.get('/{path:path}')
def frontend(path: str):
    if path.startswith(('api/', 'relay/')):
        return JSONResponse({'detail': '接口不存在'}, status_code=404)
    return FileResponse(DIST / 'index.html')
