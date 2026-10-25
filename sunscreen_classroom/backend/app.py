from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import threading
import time
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response, Path as ApiPath
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, event, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{(DATA / "classroom.db").as_posix()}')
if os.getenv('RENDER') and (not os.getenv('DATABASE_URL') or DATABASE_URL.startswith('sqlite')):
    raise RuntimeError('Render classroom deployments require an external PostgreSQL DATABASE_URL.')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False, 'timeout': 30} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_config(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')

SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Classroom(Base):
    __tablename__ = 'classrooms'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    total_groups: Mapped[int] = mapped_column(Integer, default=10)
    phase: Mapped[int] = mapped_column(Integer, default=2)
    task2: Mapped[str] = mapped_column(String(16), default='not_open')
    task3: Mapped[str] = mapped_column(String(16), default='not_open')
    demo: Mapped[int] = mapped_column(Integer, default=0)
    created: Mapped[str] = mapped_column(String(40), default=lambda: now())


class Group(Base):
    __tablename__ = 'groups'
    __table_args__ = (UniqueConstraint('classroom_id', 'number'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey('classrooms.id'))
    number: Mapped[int] = mapped_column(Integer)
    reporter: Mapped[str] = mapped_column(String(40))
    created: Mapped[str] = mapped_column(String(40), default=lambda: now())


class Submission(Base):
    __tablename__ = 'submissions'
    __table_args__ = (UniqueConstraint('group_id', 'task'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey('classrooms.id'))
    group_id: Mapped[int] = mapped_column(ForeignKey('groups.id'))
    task: Mapped[int] = mapped_column(Integer)
    payload: Mapped[str] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated: Mapped[str] = mapped_column(String(40), default=lambda: now())


class SubmissionVersion(Base):
    __tablename__ = 'submission_versions'
    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey('submissions.id'))
    revision: Mapped[int] = mapped_column(Integer)
    payload: Mapped[str] = mapped_column(Text)
    created: Mapped[str] = mapped_column(String(40), default=lambda: now())


class LoginSession(Base):
    __tablename__ = 'login_sessions'
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(12))
    group_id: Mapped[int | None] = mapped_column(ForeignKey('groups.id'), nullable=True)
    expires: Mapped[int] = mapped_column(Integer)


def now():
    return datetime.now(timezone.utc).isoformat()


def local_credentials():
    username = os.getenv('TEACHER_USERNAME', 'gxl')
    password = os.getenv('TEACHER_PASSWORD')
    if not password:
        if os.getenv('RENDER'):
            raise RuntimeError('Set TEACHER_PASSWORD in the Render environment.')
        path = DATA / 'local-credentials.json'
        if path.exists():
            config = json.loads(path.read_text(encoding='utf-8'))
            password = config['password']
        else:
            password = 'Sun-' + secrets.token_urlsafe(8)
            path.write_text(json.dumps({'username': username, 'password': password}, indent=2), encoding='utf-8')
    return username, password


TEACHER_USERNAME, TEACHER_PASSWORD = local_credentials()
COOKIE = 'sunscreen_session'
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'true' if os.getenv('RENDER') else 'false').lower() == 'true'
FG = {'carboxyl': '羧基', 'aldehyde': '醛基', 'ester': '酯基', 'hydroxyl': '羟基', 'alkene': '碳碳双键', 'alkyne': '碳碳三键'}
CATALOG_FILE = ROOT / 'frontend/public/molecules/catalog.json'


def catalog():
    return json.loads(CATALOG_FILE.read_text(encoding='utf-8')) if CATALOG_FILE.exists() else []


@asynccontextmanager
async def lifespan(_):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title='防晒霜互动课堂', lifespan=lifespan, docs_url=None, redoc_url=None)


@app.middleware('http')
async def response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
    elif request.url.path.startswith('/assets/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif request.url.path.startswith('/molecules/'):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    return response


@app.exception_handler(HTTPException)
async def http_error(_, exc):
    return JSONResponse({'detail': exc.detail}, status_code=exc.status_code)


def db_session():
    with SessionLocal() as db:
        yield db


def auth(request: Request, db: Session = Depends(db_session)):
    token = request.cookies.get(COOKIE, '')
    sess = db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest()) if token else None
    if not sess or sess.expires < time.time():
        raise HTTPException(401, '请先登录或重新加入课堂')
    return sess


def teacher(user=Depends(auth)):
    if user.role != 'teacher':
        raise HTTPException(403, '此操作仅对教师开放')
    return user


def student(user=Depends(auth)):
    if user.role != 'student':
        raise HTTPException(403, '请使用小组学习端')
    return user


def issue_session(response, db, role, group_id=None):
    token = secrets.token_urlsafe(40)
    db.add(LoginSession(digest=hashlib.sha256(token.encode()).hexdigest(), role=role, group_id=group_id, expires=int(time.time()) + 12 * 3600))
    db.commit()
    response.set_cookie(COOKIE, token, httponly=True, secure=COOKIE_SECURE, samesite='lax', max_age=43200, path='/')


def classroom_or_404(db, cid):
    obj = db.get(Classroom, cid)
    if not obj:
        raise HTTPException(404, '课堂不存在')
    return obj


def group_of(db, user):
    group = db.get(Group, user.group_id)
    if not group:
        raise HTTPException(401, '小组身份已失效，请重新加入')
    return group


def class_json(db, obj):
    groups = db.scalars(select(Group).where(Group.classroom_id == obj.id)).all()
    counts = Counter(db.scalars(select(Submission.task).where(Submission.classroom_id == obj.id)).all())
    return {'id': obj.id, 'code': obj.code, 'name': obj.name, 'total_groups': obj.total_groups,
            'phase': 3 if obj.phase in [3, 4] else 2, 'task2': obj.task2, 'task3': obj.task3, 'demo': bool(obj.demo),
            'joined': len(groups), 'submitted2': counts[2], 'submitted3': counts[3], 'created': obj.created}


class TeacherLogin(BaseModel):
    username: str = Field(max_length=80)
    password: str = Field(max_length=200)


login_attempts = defaultdict(list)
login_lock = threading.Lock()


@app.post('/api/auth/teacher')
def teacher_login(data: TeacherLogin, request: Request, response: Response, db: Session = Depends(db_session)):
    ip = request.client.host if request.client else 'local'
    with login_lock:
        login_attempts[ip] = [t for t in login_attempts[ip] if t > time.time() - 60]
        if len(login_attempts[ip]) >= 10:
            raise HTTPException(429, '尝试次数过多，请一分钟后重试')
        login_attempts[ip].append(time.time())
    if not (hmac.compare_digest(data.username.encode(), TEACHER_USERNAME.encode()) and hmac.compare_digest(data.password.encode(), TEACHER_PASSWORD.encode())):
        raise HTTPException(401, '教师账号或密码不正确')
    issue_session(response, db, 'teacher')
    return {'role': 'teacher'}


class Join(BaseModel):
    code: str = Field(min_length=4, max_length=12)
    number: int = Field(ge=1, le=100)
    reporter: str = Field(min_length=1, max_length=40)


@app.post('/api/auth/join')
def join(data: Join, response: Response, db: Session = Depends(db_session)):
    room = db.scalar(select(Classroom).where(Classroom.code == data.code.strip().upper()))
    if not room:
        raise HTTPException(404, '课堂码不正确，请向老师确认')
    if data.number > room.total_groups:
        raise HTTPException(422, f'小组号应在1至{room.total_groups}之间')
    reporter = data.reporter.strip()
    if not reporter:
        raise HTTPException(422, '请输入汇报人姓名')
    group = db.scalar(select(Group).where(Group.classroom_id == room.id, Group.number == data.number))
    if group:
        if group.reporter != reporter:
            raise HTTPException(409, '此小组已加入，请填写原汇报人姓名；如需更名，请联系教师')
    else:
        group = Group(classroom_id=room.id, number=data.number, reporter=reporter)
        db.add(group)
        try:
            db.flush()
        except Exception:
            db.rollback()
            raise HTTPException(409, '小组正在加入，请重试')
    issue_session(response, db, 'student', group.id)
    return {'role': 'student', 'classroom': class_json(db, room), 'group': {'id': group.id, 'number': group.number, 'reporter': group.reporter}}


@app.post('/api/auth/logout')
def logout(request: Request, response: Response, db: Session = Depends(db_session)):
    token = request.cookies.get(COOKIE, '')
    sess = db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest()) if token else None
    if sess:
        db.delete(sess); db.commit()
    response.delete_cookie(COOKIE, path='/')
    return {'ok': True}


@app.get('/api/me')
def me(user=Depends(auth), db: Session = Depends(db_session)):
    if user.role == 'teacher':
        return {'role': 'teacher'}
    group = group_of(db, user)
    room = classroom_or_404(db, group.classroom_id)
    submissions = db.scalars(select(Submission).where(Submission.group_id == group.id)).all()
    return {'role': 'student', 'classroom': class_json(db, room), 'group': {'id': group.id, 'number': group.number, 'reporter': group.reporter},
            'submissions': {str(x.task): {'payload': json.loads(x.payload), 'revision': x.revision, 'updated': x.updated} for x in submissions}}


class CreateClass(BaseModel):
    name: str = Field(default='探秘防晒霜的主要成分', min_length=1, max_length=120)
    total_groups: int = Field(default=10, ge=1, le=100)


def new_class(db, name, total, demo=False):
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    while True:
        code = ''.join(secrets.choice(alphabet) for _ in range(6))
        if not db.scalar(select(Classroom.id).where(Classroom.code == code)):
            break
    room = Classroom(code=code, name=name.strip(), total_groups=total, demo=int(demo))
    db.add(room); db.flush()
    return room


@app.get('/api/teacher/classes', dependencies=[Depends(teacher)])
def list_classes(db: Session = Depends(db_session)):
    return [class_json(db, x) for x in db.scalars(select(Classroom).order_by(Classroom.id.desc())).all()]


@app.post('/api/teacher/classes', dependencies=[Depends(teacher)])
def create_class(data: CreateClass, db: Session = Depends(db_session)):
    if not data.name.strip():
        raise HTTPException(422, '请输入课堂名称')
    room = new_class(db, data.name, data.total_groups)
    db.commit()
    return class_json(db, room)


class Control(BaseModel):
    phase: Literal[2, 3]
    action: Literal['open', 'close', 'show']


@app.post('/api/teacher/classes/{cid}/control', dependencies=[Depends(teacher)])
def control(cid: int, data: Control, db: Session = Depends(db_session)):
    with write_lock:
        return apply_control(cid, data, db)


def apply_control(cid, data, db):
    room = db.scalar(select(Classroom).where(Classroom.id == cid).with_for_update())
    if not room:
        raise HTTPException(404, '课堂不存在')
    if data.action == 'open' and data.phase not in [2, 3]:
        raise HTTPException(422, '仅环节二和环节三支持答题')
    if data.action == 'close':
        if data.phase in [2, 3] and getattr(room, f'task{data.phase}') == 'open':
            setattr(room, f'task{data.phase}', 'closed')
    else:
        room.phase = data.phase
        for task in [2, 3]:
            if getattr(room, f'task{task}') == 'open':
                setattr(room, f'task{task}', 'closed')
        if data.action == 'open':
            setattr(room, f'task{data.phase}', 'open')
    db.commit()
    return class_json(db, room)


class ClassEdit(BaseModel):
    total_groups: int = Field(ge=1, le=100)
    name: str = Field(min_length=1, max_length=120)


@app.patch('/api/teacher/classes/{cid}', dependencies=[Depends(teacher)])
def edit_class(cid: int, data: ClassEdit, db: Session = Depends(db_session)):
    room = classroom_or_404(db, cid)
    if db.scalar(select(Group.id).where(Group.classroom_id == cid).limit(1)):
        raise HTTPException(409, '已有小组加入，课堂名称和小组总数已锁定；请另建课堂')
    if not data.name.strip():
        raise HTTPException(422, '请输入课堂名称')
    room.name = data.name.strip(); room.total_groups = data.total_groups
    db.commit()
    return class_json(db, room)


class Rename(BaseModel):
    reporter: str = Field(min_length=1, max_length=40)


@app.patch('/api/teacher/classes/{cid}/groups/{gid}', dependencies=[Depends(teacher)])
def rename(cid: int, gid: int, data: Rename, db: Session = Depends(db_session)):
    group = db.get(Group, gid)
    if not group or group.classroom_id != cid:
        raise HTTPException(404, '小组不存在')
    if not data.reporter.strip():
        raise HTTPException(422, '姓名不能为空')
    group.reporter = data.reporter.strip(); db.commit()
    return {'ok': True}


class FGCount(BaseModel):
    id: Literal['carboxyl', 'aldehyde', 'ester', 'hydroxyl', 'alkene', 'alkyne']
    count: int = Field(default=1, ge=1, le=12)


class Hypothesis(BaseModel):
    rows: list[list[FGCount]] = Field(min_length=2, max_length=7)
    revision: int = Field(default=0, ge=0)


def canonical_rows(rows):
    normalized = []
    for row in rows:
        counts = Counter()
        for item in row:
            counts[item.id] += item.count
        if not counts:
            continue
        if sum(counts.values()) > 12:
            raise HTTPException(422, '每条猜想最多放入12个官能团')
        normalized.append([{'id': k, 'count': v} for k, v in sorted(counts.items())])
    keys = [json.dumps(x, sort_keys=True) for x in normalized]
    if len(set(keys)) < 2:
        raise HTTPException(422, '请至少填写两条不同的猜想组合')
    if len(set(keys)) != len(keys):
        raise HTTPException(422, '有重复组合，请调整后再提交')
    return normalized


# Serialize state transitions and writes inside the single-process classroom deployment.
# PostgreSQL row locks additionally coordinate workers if a deployment is scaled later.
write_lock = threading.RLock()


def save_submission(db, user, task, payload, revision):
    group = group_of(db, user)
    with write_lock:
        room = db.scalar(select(Classroom).where(Classroom.id == group.classroom_id).with_for_update())
        if getattr(room, f'task{task}') != 'open':
            raise HTTPException(409, '本任务暂未开放或已结束，当前答案已保留在本机')
        current = db.scalar(select(Submission).where(Submission.group_id == group.id, Submission.task == task))
        if (current.revision if current else 0) != revision:
            raise HTTPException(409, '本组答案已在其他页面更新，请刷新后再修改')
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if current:
            current.payload = text; current.revision += 1; current.updated = now()
        else:
            current = Submission(classroom_id=room.id, group_id=group.id, task=task, payload=text, revision=1)
            db.add(current); db.flush()
        db.add(SubmissionVersion(submission_id=current.id, revision=current.revision, payload=text))
        db.commit()
        return {'ok': True, 'revision': current.revision, 'updated': current.updated, 'payload': payload}


@app.put('/api/student/hypothesis')
def submit_hypothesis(data: Hypothesis, user=Depends(student), db: Session = Depends(db_session)):
    return save_submission(db, user, 2, {'rows': canonical_rows(data.rows)}, data.revision)


class MoleculeAnswer(BaseModel):
    molecule_id: str = Field(max_length=80)
    revision: int = Field(default=0, ge=0)


@app.put('/api/student/molecule')
def submit_molecule(data: MoleculeAnswer, user=Depends(student), db: Session = Depends(db_session)):
    if data.molecule_id not in {x['id'] for x in catalog()}:
        raise HTTPException(422, '请选择有效的分子结构')
    if data.molecule_id == 'none__acid':
        raise HTTPException(422, '请至少完成一项修饰后再提交')
    return save_submission(db, user, 3, {'molecule_id': data.molecule_id}, data.revision)


def row_label(row):
    return '＋'.join((f'{x["count"]}个' if x['count'] > 1 else '') + FG[x['id']] for x in row)


def stats(db, room, task, include_groups=False):
    submissions = db.scalars(select(Submission).where(Submission.classroom_id == room.id, Submission.task == task)).all()
    groups = {x.id: x for x in db.scalars(select(Group).where(Group.classroom_id == room.id)).all()}
    buckets = {}
    molecules = {x['id']: x for x in catalog()}
    for submission in submissions:
        data = json.loads(submission.payload)
        entries = data['rows'] if task == 2 else [data['molecule_id']]
        for entry in entries:
            key = json.dumps(entry, sort_keys=True, ensure_ascii=False) if task == 2 else entry
            if key not in buckets:
                buckets[key] = {'key': key, 'label': row_label(entry) if task == 2 else molecules[entry]['name'],
                                **({'items': entry} if task == 2 else {'molecule_id': entry}), 'count': 0, 'groups': []}
            bucket = buckets[key]; bucket['count'] += 1
            group = groups[submission.group_id]
            bucket['groups'].append({'id': group.id, 'number': group.number, 'reporter': group.reporter})
    result = sorted(buckets.values(), key=lambda x: (-x['count'], x['key']))
    for bucket in result:
        bucket['fraction'] = bucket['count'] / room.total_groups
        if include_groups:
            bucket['groups'].sort(key=lambda x: x['number'])
        else:
            del bucket['groups']
    return {'total_groups': room.total_groups, 'submitted': len(submissions), 'cards': result}


@app.get('/api/student/stats/{task}')
def student_stats(task: int = ApiPath(ge=2, le=3), user=Depends(student), db: Session = Depends(db_session)):
    group = group_of(db, user)
    if not db.scalar(select(Submission.id).where(Submission.group_id == group.id, Submission.task == task)):
        raise HTTPException(403, '提交本组答案后可查看全班统计')
    return stats(db, classroom_or_404(db, group.classroom_id), task)


@app.get('/api/teacher/classes/{cid}/stats/{task}', dependencies=[Depends(teacher)])
def teacher_stats(cid: int, task: int = ApiPath(ge=2, le=3), db: Session = Depends(db_session)):
    return stats(db, classroom_or_404(db, cid), task, True)


@app.get('/api/teacher/classes/{cid}/groups', dependencies=[Depends(teacher)])
def group_details(cid: int, db: Session = Depends(db_session)):
    room = classroom_or_404(db, cid)
    groups = {x.number: x for x in db.scalars(select(Group).where(Group.classroom_id == cid)).all()}
    submissions = db.scalars(select(Submission).where(Submission.classroom_id == cid)).all()
    lookup = {(x.group_id, x.task): x for x in submissions}
    result = []
    for number in range(1, room.total_groups + 1):
        group = groups.get(number)
        result.append({'id': group.id if group else None, 'number': number, 'reporter': group.reporter if group else '',
            'answers': {str(task): {'payload': json.loads(lookup[(group.id, task)].payload), 'revision': lookup[(group.id, task)].revision,
                                  'updated': lookup[(group.id, task)].updated}
                        for task in [2, 3] if group and (group.id, task) in lookup}})
    return result


@app.get('/api/teacher/classes/{cid}/export', dependencies=[Depends(teacher)])
def export(cid: int, format: Literal['json', 'csv'] = 'json', db: Session = Depends(db_session)):
    room = classroom_or_404(db, cid)
    groups = group_details(cid, db)
    if format == 'csv':
        buffer = io.StringIO(); writer = csv.writer(buffer)
        writer.writerow(['小组', '汇报人', '官能团猜想', '分子修饰', '环节二版本', '环节三版本'])
        molecules = {x['id']: x['name'] for x in catalog()}
        def safe_cell(value):
            # Protect CSV files opened in Excel from spreadsheet-formula input.
            value = str(value)
            return "'" + value if value.startswith(('=', '+', '-', '@', '\t', '\r')) else value
        for group in groups:
            a = group['answers']; hypothesis = '；'.join(row_label(x) for x in a.get('2', {}).get('payload', {}).get('rows', []))
            molecule = molecules.get(a.get('3', {}).get('payload', {}).get('molecule_id'), '')
            writer.writerow([group['number'], safe_cell(group['reporter']), hypothesis, molecule, a.get('2', {}).get('revision', ''), a.get('3', {}).get('revision', '')])
        content = '\ufeff' + buffer.getvalue(); media = 'text/csv; charset=utf-8'
    else:
        versions = db.execute(select(SubmissionVersion, Submission).join(Submission, Submission.id == SubmissionVersion.submission_id).where(Submission.classroom_id == cid)).all()
        content = json.dumps({'classroom': class_json(db, room), 'groups': groups,
            'history': [{'group_id': submission.group_id, 'task': submission.task, 'revision': version.revision,
                         'payload': json.loads(version.payload), 'created': version.created} for version, submission in versions]}, ensure_ascii=False, indent=2)
        media = 'application/json'
    return StreamingResponse(iter([content.encode('utf-8')]), media_type=media,
        headers={'Content-Disposition': f'attachment; filename="classroom-{room.code}.{format}"'})


@app.post('/api/teacher/demo', dependencies=[Depends(teacher)])
def demo(db: Session = Depends(db_session)):
    room = new_class(db, '演示课堂 · 探秘防晒霜的主要成分', 10, True)
    room.phase = 2; room.task2 = 'open'
    ids = ['methoxy_para__ethylhexyl', 'methoxy_ortho__ethyl', 'amino_para__acid', 'methyl_meta__hexyl']
    for number in range(1, 11):
        group = Group(classroom_id=room.id, number=number, reporter=f'演示同学{number}'); db.add(group); db.flush()
        row1 = [{'id': 'alkene', 'count': 1}, {'id': 'carboxyl', 'count': 1}] if number <= 8 else [{'id': 'alkyne', 'count': 1}, {'id': 'hydroxyl', 'count': 2}]
        row2 = [{'id': 'alkene', 'count': 1}, {'id': 'ester', 'count': 1}]
        for task, payload in [(2, {'rows': [row1, row2]}), (3, {'molecule_id': ids[(number-1) % len(ids)]})]:
            text = json.dumps(payload, ensure_ascii=False)
            submission = Submission(classroom_id=room.id, group_id=group.id, task=task, payload=text, revision=1)
            db.add(submission); db.flush(); db.add(SubmissionVersion(submission_id=submission.id, revision=1, payload=text))
    db.commit()
    return class_json(db, room)


@app.get('/api/catalog')
def get_catalog():
    return catalog()


@app.get('/api/health')
def health():
    with engine.connect() as conn:
        conn.exec_driver_sql('SELECT 1')
    return {'status': 'ok', 'molecules': len(catalog())}


PUBLIC = ROOT / 'frontend/public'
DIST = ROOT / 'frontend/dist'
if (PUBLIC / 'molecules').exists():
    app.mount('/molecules', StaticFiles(directory=PUBLIC / 'molecules'), name='molecules')
if (DIST / 'assets').exists():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')


@app.get('/{path:path}')
def frontend(path: str):
    if path.startswith('api/'):
        raise HTTPException(404, '接口不存在')
    index = DIST / 'index.html'
    if not index.exists():
        return JSONResponse({'detail': '请先在frontend目录执行npm install和npm run build'}, status_code=503)
    return FileResponse(index)
