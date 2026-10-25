"""Exercise 30 concurrent groups over real HTTP in a disposable server/database."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import httpx

ROOT=Path(__file__).resolve().parents[1]


async def check(base):
    async with httpx.AsyncClient(base_url=base,timeout=30) as teacher:
        login=await teacher.post('/api/auth/teacher',json={'username':'network-test','password':'isolated-network-password'})
        login.raise_for_status()
        room=(await teacher.post('/api/teacher/classes',json={'name':'隔离网络验收','total_groups':30})).json()
        control=await teacher.post(f'/api/teacher/classes/{room["id"]}/control',json={'phase':2,'action':'open'});control.raise_for_status()
        clients=[httpx.AsyncClient(base_url=base,timeout=30) for _ in range(30)]
        try:
            async def join(i):
                res=await clients[i].post('/api/auth/join',json={'code':room['code'],'number':i+1,'reporter':f'验收同学{i+1}'});res.raise_for_status()
            await asyncio.gather(*(join(i) for i in range(30)))
            payload={'rows':[[{'id':'carboxyl','count':1},{'id':'alkene','count':1}],[{'id':'ester','count':1},{'id':'alkene','count':1}]],'revision':0}
            start=time.perf_counter()
            results=await asyncio.gather(*(c.put('/api/student/hypothesis',json=payload) for c in clients))
            seconds=time.perf_counter()-start
            for res in results:res.raise_for_status()
            stats=(await teacher.get(f'/api/teacher/classes/{room["id"]}/stats/2')).json()
            assert stats['submitted']==30 and all(c['count']==30 for c in stats['cards'])
            assert (await teacher.get('/')).status_code==200
            catalog=(await teacher.get('/api/catalog')).json()
            for item in catalog:
                assert (await teacher.get(item['cloud'])).status_code==200
                assert (await teacher.get(item['structure'])).status_code==200
            return {'concurrent_groups':30,'successful_submissions':len(results),'elapsed_seconds':round(seconds,3),
                'all_counts_correct':True,'molecules_served':len(catalog),'database':'isolated temporary SQLite',
                'validation':'Real HTTP requests to temporary localhost uvicorn instance; no formal classroom data used.'}
        finally:
            await asyncio.gather(*(c.aclose() for c in clients))


def main():
    with tempfile.TemporaryDirectory(prefix='sunscreen-http-') as temp:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env=os.environ.copy();env.update({'DATABASE_URL':f'sqlite:///{Path(temp).as_posix()}/test.db','TEACHER_USERNAME':'network-test','TEACHER_PASSWORD':'isolated-network-password','COOKIE_SECURE':'false'})
        env.pop('RENDER',None)
        log=open(Path(temp)/'server.log','w',encoding='utf-8')
        process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=log,stderr=log)
        try:
            base=f'http://127.0.0.1:{port}'
            for _ in range(60):
                try:
                    with urllib.request.urlopen(base+'/api/health',timeout=.5) as response:
                        if response.status==200:break
                except Exception:
                    if process.poll() is not None:raise RuntimeError('Isolated verification server failed.')
                    time.sleep(.2)
            else:raise RuntimeError('Isolated verification server did not become ready.')
            report=asyncio.run(check(base))
            (ROOT/'outputs').mkdir(exist_ok=True)
            (ROOT/'outputs/network-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report,ensure_ascii=False,indent=2))
        finally:
            if os.name=='nt':
                # A Windows venv launcher owns a child Python; stop this test's whole tree.
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,check=False)
            else:
                process.terminate()
            process.wait(timeout=15);log.close()
            time.sleep(.2)


if __name__=='__main__':main()
