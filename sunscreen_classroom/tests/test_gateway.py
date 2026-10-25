"""Verify request isolation and disconnect behavior without a public connection."""
import asyncio
import base64
import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

os.environ.setdefault('LOCAL_RELAY_TOKEN', 'test-only-relay-token-at-least-32-characters')
from backend import gateway
from scripts.local_relay import serve_request


def response_for(message, body, headers=None):
    return {'type': 'response', 'id': message['id'], 'status': 200,
            'headers': headers or [['content-type', 'application/json']],
            'body': base64.b64encode(json.dumps(body).encode()).decode()}


def test_offline_static_catalog_and_connection_auth():
    with TestClient(gateway.app) as client:
        assert client.get('/healthz').json()['computer_connected'] is False
        materials = client.get('/api/catalog').json()
        assert len(materials) == 44
        available = [item for item in materials if item['available']]
        assert len(available) == 12
        assert {item['ester'] for item in available} == {'acid', 'methyl', 'ethylhexyl'}
        assert {item['ring'] for item in available} == {'none', 'methoxy'}
        assert client.get('/api/me').status_code == 503
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/relay/connect', headers={'Authorization': 'Bearer wrong'}):
                pass


def test_multiplex_30_requests_and_secure_cookie():
    with TestClient(gateway.app) as client:
        with client.websocket_connect('/relay/connect', headers={'Authorization': 'Bearer ' + gateway.TOKEN}) as websocket:
            assert websocket.receive_json()['type'] == 'ready'
            assert client.get('/healthz').json()['computer_connected']
            with ThreadPoolExecutor(max_workers=30) as pool:
                futures = [pool.submit(client.get, f'/api/check?group={number}') for number in range(30)]
                requests = [websocket.receive_json() for _ in range(30)]
                assert len({message['id'] for message in requests}) == 30
                for message in reversed(requests):
                    websocket.send_json(response_for(message, {'query': message['query']},
                                                     [['content-type', 'application/json'], ['set-cookie', 'session=test; HttpOnly; Path=/']]))
                for number, future in enumerate(futures):
                    response = future.result(timeout=5)
                    assert response.json()['query'] == f'group={number}'
                    assert '; Secure' in response.headers['set-cookie']
                    assert response.headers['x-classroom-storage'] == 'local'
        assert not client.get('/healthz').json()['computer_connected']
        assert client.get('/api/me').status_code == 503


def test_relay_cookie_jars_do_not_cross_groups():
    classroom = FastAPI()

    @classroom.post('/api/login')
    def login(response: Response):
        response.set_cookie('student_session', 'group-one')
        return {'ok': True}

    @classroom.get('/api/me')
    def me(request: Request):
        return {'cookie': request.cookies.get('student_session')}

    class Socket:
        def __init__(self):
            self.messages = []

        async def send(self, message):
            self.messages.append(json.loads(message))

    async def check():
        socket = Socket()
        await serve_request({'id': '1', 'method': 'POST', 'path': '/api/login'}, socket, classroom)
        await serve_request({'id': '2', 'method': 'GET', 'path': '/api/me'}, socket, classroom)
        assert json.loads(base64.b64decode(socket.messages[1]['body']))['cookie'] is None
        await serve_request({'id': '3', 'method': 'GET', 'path': '/api/me',
                             'headers': {'cookie': 'student_session=group-one'}}, socket, classroom)
        assert json.loads(base64.b64decode(socket.messages[2]['body']))['cookie'] == 'group-one'

    asyncio.run(check())
