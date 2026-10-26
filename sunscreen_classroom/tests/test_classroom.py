"""Behavioral checks against an isolated temporary database; never touches classroom data."""
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TESTDIR = tempfile.TemporaryDirectory(prefix='sunscreen-tests-')
os.environ['DATABASE_URL'] = f'sqlite:///{Path(TESTDIR.name).as_posix()}/test.db'
os.environ['TEACHER_USERNAME'] = 'testteacher'
os.environ['TEACHER_PASSWORD'] = 'test-password-only'
os.environ['COOKIE_SECURE'] = 'false'

from backend.app import app, catalog, engine, FG


@pytest.fixture(scope='module')
def teacher_client():
    with TestClient(app) as client:
        assert client.post('/api/auth/teacher', json={'username':'testteacher','password':'test-password-only'}).status_code == 200
        yield client
    engine.dispose()
    TESTDIR.cleanup()


def create_room(teacher, total=10):
    res=teacher.post('/api/teacher/classes',json={'name':'隔离测试课堂','total_groups':total})
    assert res.status_code==200,res.text
    return res.json()


def control(teacher, room, phase, action='open'):
    res=teacher.post(f'/api/teacher/classes/{room["id"]}/control',json={'phase':phase,'action':action})
    assert res.status_code==200,res.text
    return res.json()


def student(room,number):
    client=TestClient(app)
    res=client.post('/api/auth/join',json={'code':room['code'],'number':number,'reporter':f'测试同学{number}'})
    assert res.status_code==200,res.text
    return client


ROW1=[{'id':'carboxyl','count':1},{'id':'alkene','count':1}]
ROW2=[{'id':'ester','count':1},{'id':'alkene','count':1}]
ROW3=[{'id':'hydroxyl','count':2},{'id':'alkyne','count':1}]


def send(client,rows,revision=0):
    return client.put('/api/student/hypothesis',json={'rows':rows,'revision':revision})


def test_access_control_and_join_rules(teacher_client):
    room=create_room(teacher_client)
    anon=TestClient(app)
    assert anon.get('/api/teacher/classes').status_code==401
    assert anon.post('/api/auth/join',json={'code':room['code'],'number':11,'reporter':'同学'}).status_code==422
    client=student(room,1)
    assert client.get('/api/teacher/classes').status_code==403
    assert client.post(f'/api/teacher/classes/{room["id"]}/control',json={'phase':2,'action':'open'}).status_code==403
    assert client.get('/api/student/stats/2').status_code==403
    assert send(client,[ROW1,ROW2]).status_code==409
    assert anon.post('/api/auth/join',json={'code':room['code'],'number':1,'reporter':'其他人'}).status_code==409
    assert teacher_client.patch(f'/api/teacher/classes/{room["id"]}',json={'name':'调整','total_groups':12}).status_code==409
    client.close();anon.close()


def test_eighty_percent_deduplication_and_replacement(teacher_client):
    room=create_room(teacher_client)
    control(teacher_client,room,2)
    clients=[student(room,i) for i in range(1,11)]
    for i,client in enumerate(clients):
        assert send(client,[ROW1,ROW2] if i<8 else [ROW2,ROW3]).status_code==200
    url=f'/api/teacher/classes/{room["id"]}/stats/2'
    result=teacher_client.get(url).json()
    card=next(c for c in result['cards'] if c['label']=='碳碳双键＋羧基')
    assert result['submitted']==10
    assert card['count']==8 and card['fraction']==.8 and len(card['groups'])==8
    # Same groups in another order must not count as a distinct guess.
    assert send(clients[0],[ROW1,list(reversed(ROW1))],1).status_code==422
    assert send(clients[0],[ROW1],1).status_code==422
    assert send(clients[0],[ROW2,ROW3],1).status_code==200
    updated=teacher_client.get(url).json()
    assert updated['submitted']==10
    assert next(c for c in updated['cards'] if c['label']=='碳碳双键＋羧基')['count']==7
    assert send(clients[0],[ROW1,ROW2],1).status_code==409
    anon_stats=clients[0].get('/api/student/stats/2').json()
    assert 'reporter' not in str(anon_stats) and 'groups' not in anon_stats['cards'][0]
    export=teacher_client.get(f'/api/teacher/classes/{room["id"]}/export').json()
    assert len(export['history'])==11
    assert teacher_client.get(f'/api/teacher/classes/{room["id"]}/export?format=csv').status_code==200
    for client in clients: client.close()


def test_phase_switch_and_molecule_validation(teacher_client):
    room=create_room(teacher_client)
    assert room['phase']==2 and room['task2']=='not_open'
    for removed_phase in [1,4]:
        assert teacher_client.post(f'/api/teacher/classes/{room["id"]}/control',json={'phase':removed_phase,'action':'show'}).status_code==422
    client=student(room,1)
    control(teacher_client,room,2)
    assert send(client,[ROW1,ROW2]).status_code==200
    state=control(teacher_client,room,3)
    assert state['task2']=='closed' and state['task3']=='open'
    assert send(client,[ROW1,ROW3],1).status_code==409
    assert client.put('/api/student/molecule',json={'molecule_id':'invalid','revision':0}).status_code==422
    assert client.put('/api/student/molecule',json={'molecule_id':'none__acid','revision':0}).status_code==422
    assert client.put('/api/student/molecule',json={'molecule_id':'methoxy_para__ethylhexyl','revision':0}).status_code==200
    state=control(teacher_client,room,3,'close')
    assert state['task3']=='closed'
    assert client.put('/api/student/molecule',json={'molecule_id':'methoxy_para__methyl','revision':1}).status_code==409
    control(teacher_client,room,3)
    for retired in ['methoxy_para__ethyl','methoxy_para__hexyl','methyl_para__acid','amino_para__acid']:
        assert client.put('/api/student/molecule',json={'molecule_id':retired,'revision':1}).status_code==422
    assert client.put('/api/student/molecule',json={'molecule_id':'methoxy_para__methyl','revision':1}).status_code==200
    saved=client.get('/api/me').json()
    assert saved['submissions']['3']['revision']==2
    client.close()


def test_thirty_groups_in_parallel(teacher_client):
    room=create_room(teacher_client,30)
    control(teacher_client,room,2)
    clients=[student(room,i) for i in range(1,31)]
    with ThreadPoolExecutor(max_workers=30) as pool:
        responses=list(pool.map(lambda c:send(c,[ROW1,ROW2]),clients))
    assert all(r.status_code==200 for r in responses),[(r.status_code,r.text) for r in responses if r.status_code!=200]
    result=teacher_client.get(f'/api/teacher/classes/{room["id"]}/stats/2').json()
    assert result['submitted']==30 and all(c['count']==30 and c['fraction']==1 for c in result['cards'])
    for client in clients:client.close()


def test_catalog_connectivity_and_trans_configuration():
    from rdkit import Chem
    from rdkit.Chem import rdMolDescriptors
    entries=catalog()
    assert len(entries)==44 and len({m['smiles'] for m in entries})==44
    available=[item for item in entries if item['available']]
    assert len(available)==12
    assert {item['ring'] for item in available}=={'none','methoxy'}
    assert {item['ester'] for item in available}=={'acid','methyl','ethylhexyl'}
    root=Path(__file__).resolve().parents[1]/'frontend/public'
    for item in entries:
        mol=Chem.MolFromSmiles(item['smiles'])
        assert mol is not None
        assert rdMolDescriptors.CalcMolFormula(mol)==item['formula']
        assert any(b.GetStereo()==Chem.BondStereo.STEREOE for b in mol.GetBonds())
        assert (root/item['structure'].lstrip('/')).exists()
        assert set(item['hotspots'])=={'ortho','meta','para','ester'}
    target=next(x for x in entries if x['id']=='methoxy_para__ethylhexyl')
    assert target['formula']=='C18H26O3'
    methyl_esters=[item for item in available if item['ester']=='methyl']
    assert len(methyl_esters)==4
    for item in methyl_esters:
        mol=Chem.MolFromSmiles(item['smiles'])
        assert mol.HasSubstructMatch(Chem.MolFromSmarts('[C](=O)[O][CH3]'))
        assert item['formula']==('C10H10O2' if item['ring']=='none' else 'C11H12O3')
    provenance=__import__('json').loads((root/'molecules/asset-provenance.json').read_text(encoding='utf-8'))
    assert len(provenance)==44
    from PIL import Image
    import hashlib
    for item in provenance:
        image_path=root/'molecules'/f'{item["id"]}.png'
        with Image.open(image_path) as img:assert img.size==(1536,1024)
        assert hashlib.sha256(image_path.read_bytes()).hexdigest()==item['final_sha256']


def test_demo_is_separate_from_formal_classes(teacher_client):
    formal=create_room(teacher_client)
    demo=teacher_client.post('/api/teacher/demo').json()
    assert demo['demo'] is True and demo['code']!=formal['code']
    assert demo['submitted2']==10 and demo['submitted3']==10
    assert teacher_client.get(f'/api/teacher/classes/{formal["id"]}/stats/2').json()['submitted']==0


def test_delete_restore_keeps_answers_and_blocks_student_access(teacher_client):
    room=create_room(teacher_client)
    other=create_room(teacher_client)
    control(teacher_client,room,2)
    learner=student(room,1)
    assert send(learner,[ROW1,ROW2]).status_code==200
    base=f'/api/teacher/classes/{room["id"]}'
    before=teacher_client.get(base+'/export').json()
    assert learner.delete(base).status_code==403
    assert learner.get('/api/teacher/trash').status_code==403
    assert learner.post(base+'/restore').status_code==403
    with TestClient(app) as anonymous:
        assert anonymous.delete(base).status_code==401
        assert anonymous.post(base+'/restore').status_code==401
    assert teacher_client.delete(base).status_code==200
    assert teacher_client.delete(base).status_code==200
    active=teacher_client.get('/api/teacher/classes').json()
    assert room['id'] not in {r['id'] for r in active}
    assert other['id'] in {r['id'] for r in active}
    deleted=teacher_client.get('/api/teacher/trash').json()
    saved=next(r for r in deleted if r['id']==room['id'])
    assert saved['submitted2']==1 and saved['task2']=='closed' and saved['deleted_at']
    assert learner.get('/api/me').status_code==401
    assert learner.get('/api/student/stats/2').status_code==401
    assert send(learner,[ROW1,ROW3],1).status_code==401
    with TestClient(app) as newcomer:
        assert newcomer.post('/api/auth/join',json={'code':room['code'],'number':2,'reporter':'测试'}).status_code==404
    assert teacher_client.post(base+'/control',json={'phase':2,'action':'open'}).status_code==404
    assert teacher_client.patch(base,json={'name':'更改','total_groups':10}).status_code==404
    assert teacher_client.get(base+'/export').status_code==404
    assert teacher_client.get(base+'/groups').status_code==404
    assert teacher_client.get(base+'/stats/2').status_code==404
    restored=teacher_client.post(base+'/restore').json()
    assert restored['code']==room['code'] and restored['task2']=='closed'
    assert restored['joined']==1 and restored['submitted2']==1
    after=teacher_client.get(base+'/export').json()
    assert after['groups']==before['groups'] and after['history']==before['history']
    assert room['id'] not in {r['id'] for r in teacher_client.get('/api/teacher/trash').json()}
    assert learner.get('/api/me').status_code==200
    assert send(learner,[ROW1,ROW3],1).status_code==409
    control(teacher_client,room,2)
    assert send(learner,[ROW1,ROW3],1).status_code==200
    learner.close()
