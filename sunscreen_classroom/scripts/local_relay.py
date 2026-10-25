"""Connect outward to Render; run classroom requests against local SQLite only."""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def log(message):
    print(datetime.now(timezone.utc).isoformat(), message, flush=True)


async def serve_request(message, websocket, classroom_app):
    path = message.get('path', '')
    if not path.startswith('/api/') or message.get('method') not in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}:
        return
    try:
        # Each request owns its cookie jar; group sessions must never leak across requests.
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=classroom_app), base_url='http://classroom.local') as client:
            response = await client.request(
                message['method'], path + ('?' + message['query'] if message.get('query') else ''),
                headers=message.get('headers', {}), content=base64.b64decode(message.get('body', '')),
            )
        result = {'type': 'response', 'id': message['id'], 'status': response.status_code,
                  'headers': list(response.headers.multi_items()),
                  'body': base64.b64encode(response.content).decode('ascii')}
    except Exception as error:
        log('Request failed: ' + type(error).__name__)
        result = {'type': 'response', 'id': message['id'], 'status': 503,
                  'headers': [['content-type', 'application/json; charset=utf-8']],
                  'body': base64.b64encode(json.dumps({'detail': '本地课堂处理暂时失败，请重试。'}).encode()).decode()}
    await websocket.send(json.dumps(result))


async def run(config):
    from backend.app import app as classroom_app, engine

    if engine.dialect.name != 'sqlite':
        raise RuntimeError('Local classroom relay requires the local SQLite database.')
    origin = urlsplit(config['origin'])
    if origin.scheme != 'https' or not origin.hostname or origin.username or origin.password or origin.path not in {'', '/'}:
        raise ValueError('Set origin to the HTTPS classroom origin without a path.')
    endpoint = 'wss://' + origin.netloc + '/relay/connect'
    retry_delay = 2
    async with classroom_app.router.lifespan_context(classroom_app):
        while True:
            try:
                async with connect(endpoint, additional_headers={'Authorization': 'Bearer ' + config['token']},
                                   open_timeout=60, ping_interval=20, ping_timeout=30, max_size=16 * 1024 * 1024) as websocket:
                    ready = json.loads(await websocket.recv())
                    if ready.get('type') != 'ready':
                        raise RuntimeError('Classroom connection was not accepted.')
                    retry_delay = 2
                    log('Connected. Classroom records are stored on this computer.')
                    tasks = set()
                    try:
                        async for raw in websocket:
                            message = json.loads(raw)
                            if message.get('type') == 'request':
                                task = asyncio.create_task(serve_request(message, websocket, classroom_app))
                                tasks.add(task)
                                task.add_done_callback(tasks.discard)
                    finally:
                        # Finish transactions that have already reached the local database.
                        if tasks:
                            await asyncio.gather(*tasks, return_exceptions=True)
            except (OSError, TimeoutError, RuntimeError, ValueError) as error:
                log('Disconnected (' + type(error).__name__ + '); reconnecting automatically.')
            except Exception as error:
                log('Connection interrupted (' + type(error).__name__ + '); reconnecting automatically.')
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=ROOT / 'data/relay-config.json')
    args = parser.parse_args()
    try:
        asyncio.run(run(json.loads(args.config.read_text(encoding='utf-8'))))
    except KeyboardInterrupt:
        pass
