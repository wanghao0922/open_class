"""Shared material catalog and currently selectable classroom structures."""
import json
import mimetypes
import re
from pathlib import Path

mimetypes.add_type('image/webp', '.webp')


def molecule_cache_control(path: str):
    if re.fullmatch(r'/molecules/[a-z_]+\.[0-9a-f]{16}\.webp', path):
        return 'public, max-age=31536000, immutable'
    return 'public, max-age=86400'


def load_catalog(path: Path):
    entries = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    return [{**item, 'available': item['ring'] in {'none', 'methoxy'}
             and item['ester'] in {'acid', 'methyl', 'ethylhexyl'}} for item in entries]
