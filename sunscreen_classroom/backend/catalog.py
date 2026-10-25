"""Shared material catalog and currently selectable classroom structures."""
import json
from pathlib import Path


def load_catalog(path: Path):
    entries = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    return [{**item, 'available': item['ring'] in {'none', 'methoxy'}
             and item['ester'] in {'acid', 'methyl', 'ethylhexyl'}} for item in entries]
