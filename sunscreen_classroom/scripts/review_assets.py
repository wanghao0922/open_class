"""Validate delivered files and make review contact sheets; never generates paid assets."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'frontend/public/molecules';WORK=ROOT/'work';WORK.mkdir(exist_ok=True)
catalog=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
report=[]
for start in [0,20]:
    sheet=Image.new('RGB',(2000,1216),'#f1f4f8');draw=ImageDraw.Draw(sheet)
    for n,item in enumerate(catalog[start:start+20]):
        p=OUT/f'{item["id"]}.png'
        with Image.open(p) as im:
            im.load();im.thumbnail((390,265));x=(n%5)*400+(400-im.width)//2;y=(n//5)*304
            sheet.paste(im,(x,y));draw.text(((n%5)*400+10,y+270),f'{start+n:02d} {item["id"]}',font=font,fill='#173960')
        with Image.open(p) as im: size=im.size
        item['image_status']='ready'
        report.append({'id':item['id'],'size':size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    sheet.save(WORK/f'cloud-review-{start//20+1}.jpg',quality=95)
(OUT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
(WORK/'asset-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(f'{len(report)} images validated; unique hashes: {len({x["sha256"] for x in report})}')
