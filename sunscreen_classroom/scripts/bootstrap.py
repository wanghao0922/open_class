"""Initialize local credentials without printing secrets, and optionally load demo data."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app import Base, SessionLocal, engine, demo

parser=argparse.ArgumentParser();parser.add_argument('--demo',action='store_true');args=parser.parse_args()
Base.metadata.create_all(engine)
print('Local teacher credentials: '+str(ROOT/'data/local-credentials.json'))
if args.demo:
    with SessionLocal() as db:
        room=demo(db=db)
        print('Independent demo classroom: '+room['code'])
