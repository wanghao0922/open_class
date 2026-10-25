"""One API request per missing image; never automatically retry a failed/ambiguous call.

Reads the locally configured skill key without printing it. API secrets never enter output files.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
SKILL=Path.home()/'.codex/skills/diffusion-image-gen'
OUT=ROOT/'frontend/public/molecules'
WORK=ROOT/'work'; WORK.mkdir(exist_ok=True)
parser=argparse.ArgumentParser(); parser.add_argument('--baseline',action='store_true'); parser.add_argument('--workers',type=int,default=4)
args=parser.parse_args()
catalog=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
env=os.environ.copy()
if not env.get('DIFFUSION_IMAGE_API_KEY'):
    skill_text=(SKILL/'SKILL.md').read_text(encoding='utf-8')
    match=re.search(r'api_key\s*=\s*(sk-[A-Za-z0-9_-]+)',skill_text)
    if not match: raise SystemExit('Set DIFFUSION_IMAGE_API_KEY locally.')
    env['DIFFUSION_IMAGE_API_KEY']=match.group(1)
positions={'ortho':'at the adjacent upper-right ring carbon (ortho, position 2)',
           'meta':'at the upper-left ring carbon (meta, position 3)',
           'para':'at the far left ring carbon (para, position 4)'}
groups={'methyl':'a methyl -CH3 group, via its carbon','methoxy':'a methoxy -O-CH3 group, via its oxygen','amino':'an amino -NH2 group, via nitrogen'}
chains={'ethyl':'ethyl -CH2CH3','hexyl':'n-hexyl -CH2CH2CH2CH2CH2CH3','ethylhexyl':'2-ethylhexyl -CH2-CH(CH2CH3)-CH2-CH2-CH2-CH3'}

def generate(item):
    dest=OUT/f'{item["id"]}.png'; log=WORK/f'{item["id"]}.result.json'
    if dest.exists(): return item['id'],'existing'
    if log.exists(): return item['id'],'previous attempt recorded; no retry'
    ring=('No additional substituent on the benzene ring.' if item['ring']=='none' else
          f'Exactly one additional ring substituent: {groups[item["ring"]]} {positions[item["position"]]}.')
    tail=('Terminal carboxylic acid -C(=O)OH.' if item['ester']=='acid' else
          f'Terminal carboxylate ester -C(=O)-O-R, where R is {chains[item["ester"]]}. Do not show a terminal O-H bond.')
    prompt=f'''Create a single polished scientific educational illustration of {item['name']}, exact chemical connectivity SMILES {item['smiles']}.
An E/trans cinnamic acid derivative. {ring} {tail}
White background. Landscape 3:2 composition. Strictly consistent camera: benzene lies flat in image plane on the LEFT, centered at 34 percent image width and 50 percent height. A clearly recognizable regular six-carbon benzene ring occupies x=24 to 44 percent, y=34 to 66 percent. Its cinnamoyl side chain starts on the rightmost ring carbon (44%,50%) and extends RIGHT through trans -CH=CH-C(=O)-O. Carbonyl reaction site centered at (79%,48%). All atoms remain visible with plenty of margins. Orient longer ester tails toward the lower right and keep the entire molecule inside frame.
Ball-and-stick model, charcoal/teal carbons, red oxygen, blue nitrogen if present, small pale hydrogen spheres. Wrap the molecule in a translucent soft blue-violet electron-cloud-like envelope with subtle coral areas around oxygen. Surface opacity only 20 percent so the actual six-membered ring and connecting sticks remain clear. Clean high-end textbook 3D rendering, soft ambient lighting, consistent scale. This is a QUALITATIVE teaching illustration, not a calculated orbital, spectrum or quantitative electron density. No title, no text, no labels, no arrows, no numbers, no watermark, no extra molecules. Do not add unexpected heteroatoms or extra benzene rings.'''
    promptfile=WORK/f'{item["id"]}.prompt.txt'; promptfile.write_text(prompt,encoding='utf-8')
    # Record the attempt BEFORE calling, so an interrupted paid request is never silently repeated.
    log.write_text(json.dumps({'id':item['id'],'started':time.time(),'status':'started'}),encoding='utf-8')
    proc=subprocess.run([sys.executable,str(SKILL/'scripts/generate.py'),'--prompt-file',str(promptfile),'--size','1536x1024','--timeout','300','--out',str(dest)],env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
    result={'id':item['id'],'returncode':proc.returncode,'status':'ready' if proc.returncode==0 else 'failed','output':proc.stdout.strip(),'error':proc.stderr.strip()}
    log.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return item['id'],result['status']

items=catalog[:1] if args.baseline else catalog[1:]
with ThreadPoolExecutor(max_workers=args.workers) as pool:
    for future in as_completed([pool.submit(generate,item) for item in items]):
        ident,status=future.result(); print(ident,status,flush=True)
