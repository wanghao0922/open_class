"""Build content-addressed WebP derivatives without changing source PNGs.

Run with a development Python environment containing Pillow.
"""
import hashlib
import json
from io import BytesIO
from pathlib import Path

from PIL import Image


def main():
    directory = Path(__file__).resolve().parents[1] / 'frontend/public/molecules'
    catalog_path = directory / 'catalog.json'
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    original_bytes = optimized_bytes = 0
    for item in catalog:
        source = directory / f"{item['id']}.png"
        output = BytesIO()
        with Image.open(source) as image:
            image.save(output, format='WEBP', quality=90, method=6)
        data = output.getvalue()
        digest = hashlib.sha256(data).hexdigest()[:16]
        filename = f"{item['id']}.{digest}.webp"
        (directory / filename).write_bytes(data)
        # Keep the original address (including its existing cache version).
        item.setdefault('cloud_fallback', item['cloud'])
        item['cloud'] = f'/molecules/{filename}'
        original_bytes += source.stat().st_size
        optimized_bytes += len(data)
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(catalog)} clouds: {original_bytes:,} -> {optimized_bytes:,} bytes '
          f'({1 - optimized_bytes / original_bytes:.1%} smaller)')


if __name__ == '__main__':
    main()
