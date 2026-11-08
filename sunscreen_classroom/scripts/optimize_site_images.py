"""Generate lightweight spectrum previews and fingerprint vector structures.

Original spectra remain untouched and are loaded when the user opens the viewer.
Requires Pillow in the development environment, not on Render.
"""
import hashlib
import json
from pathlib import Path

from PIL import Image


def main():
    root = Path(__file__).resolve().parents[1] / 'frontend'
    assets = root / 'src/assets/spectra'
    before = after = 0
    for source in sorted(assets.iterdir()):
        if source.suffix.lower() not in {'.jpg', '.png'}:
            continue
        with Image.open(source) as image:
            image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            target = source.with_suffix('.webp')
            image.save(target, format='WEBP', quality=90, method=6)
        before += source.stat().st_size
        after += target.stat().st_size
    directory = root / 'public/molecules'
    path = directory / 'catalog.json'
    catalog = json.loads(path.read_text(encoding='utf-8'))
    for item in catalog:
        data = (directory / f"{item['id']}.svg").read_bytes()
        digest = hashlib.sha256(data).hexdigest()[:16]
        name = f"{item['id']}.{digest}.svg"
        (directory / name).write_bytes(data)
        item['structure'] = '/molecules/' + name
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Spectrum previews: {before:,} -> {after:,} bytes ({1-after/before:.1%} smaller)')
    print(f'{len(catalog)} vector structures fingerprinted; originals preserved')


if __name__ == '__main__':
    main()
