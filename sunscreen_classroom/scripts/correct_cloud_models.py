"""Correct AI-image chemistry, preserving generated cloud coloration as illustration texture.

AI originals are archived unchanged in work/ai-originals. Heavy-atom connectivity and
hydrogen counts are validated against the catalog with RDKit. The output is a hybrid
educational raster illustration, never a calculated density or electrostatic potential.
"""
import hashlib
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'frontend/public/molecules'
ORIGINALS=ROOT/'work/ai-originals';ORIGINALS.mkdir(parents=True,exist_ok=True)
CATALOG=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
W,H=1536,1024


def graph(item):
    atoms=[];bonds=[]
    def atom(symbol,x,y):
        atoms.append((symbol,x,y));return len(atoms)-1
    def bond(a,b,order=1):bonds.append((a,b,order))
    # Clockwise ring numbering: attachment point=1, then ortho, meta, para.
    for x,y in [(1,0),(.5,-.866),(-.5,-.866),(-1,0),(-.5,.866),(.5,.866)]:atom('C',x,y)
    for i in range(6):bond(i,(i+1)%6,2 if i%2==0 else 1)
    alpha=atom('C',2.2,-.36);beta=atom('C',3.4,.36);carbonyl=atom('C',4.6,0)
    oxo=atom('O',5.1,-1.12);single=atom('O',5.55,.72)
    bond(0,alpha);bond(alpha,beta,2);bond(beta,carbonyl);bond(carbonyl,oxo,2);bond(carbonyl,single)
    if item['ring']!='none':
        idx={'ortho':1,'meta':2,'para':3}[item['position']]
        _,x,y=atoms[idx]
        nx,ny=x,y
        sym={'methyl':'C','methoxy':'O','amino':'N'}[item['ring']]
        sub=atom(sym,x+nx*1.22,y+ny*1.22);bond(idx,sub)
        if item['ring']=='methoxy':
            # Bend the methoxy carbon away from the ring instead of adding an O-H.
            _,ox,oy=atoms[sub]
            methyl=atom('C',ox+nx*.7-ny*.85,oy+ny*.7+nx*.85);bond(sub,methyl)
    if item['ester']!='acid':
        count=2 if item['ester']=='ethyl' else 6
        chain=[]
        for i in range(count):
            cx=6.65+i*1.02;cy=.72+(0 if i%2 else .55)+i*.22
            node=atom('C',cx,cy);bond(single if i==0 else chain[-1],node);chain.append(node)
        if item['ester']=='ethylhexyl':
            _,x,y=atoms[chain[1]]
            branch=atom('C',x-.12,y+1.12);bond(chain[1],branch)
            end=atom('C',x+.83,y+1.75);bond(branch,end)
    rw=Chem.RWMol()
    for sym,_,_ in atoms:rw.AddAtom(Chem.Atom(sym))
    for a,b,order in bonds:rw.AddBond(a,b,Chem.BondType.DOUBLE if order==2 else Chem.BondType.SINGLE)
    mol=rw.GetMol();Chem.SanitizeMol(mol)
    reference=Chem.MolFromSmiles(item['smiles'])
    assert Chem.MolToSmiles(mol,isomericSmiles=False)==Chem.MolToSmiles(reference,isomericSmiles=False),item['id']
    assert rdMolDescriptors.CalcMolFormula(mol)==item['formula']
    # Explicit hydrogens placed into vacant angular sectors; counts come from chemistry.
    for i in range(len(atoms)):
        count=mol.GetAtomWithIdx(i).GetTotalNumHs()
        _,x,y=atoms[i]
        neighbors=[b if a==i else a for a,b,_ in bonds if a==i or b==i]
        angles=[math.atan2(atoms[n][2]-y,atoms[n][1]-x) for n in neighbors]
        for _ in range(count):
            choices=[j*math.pi/90 for j in range(180)]
            def distance(angle):return min(abs(math.atan2(math.sin(angle-a),math.cos(angle-a))) for a in angles)
            angle=max(choices,key=distance);angles.append(angle)
            node=atom('H',x+.58*math.cos(angle),y+.58*math.sin(angle));bond(i,node)
    return atoms,bonds,{'ortho':1,'meta':2,'para':3,'ester':carbonyl}


def render(item):
    dest=OUT/f'{item["id"]}.png';original=ORIGINALS/dest.name
    if not original.exists():original.write_bytes(dest.read_bytes())
    source=Image.open(original).convert('RGBA')
    white=Image.new('RGBA',source.size,'white');white.alpha_composite(source)
    # Blur removes AI-drawn bonds/atoms entirely; retain generated colors as a cloud texture.
    texture=white.convert('RGB').resize((W,H)).filter(ImageFilter.GaussianBlur(70))
    texture=Image.blend(texture,Image.new('RGB',(W,H),'#e2e1ff'),.72)
    atoms,bonds,anchors=graph(item)
    xs=[a[1] for a in atoms];ys=[a[2] for a in atoms]
    xmin,xmax=min(xs)-.7,max(xs)+.7;ymin,ymax=min(ys)-.7,max(ys)+.7
    scale=min((W-200)/(xmax-xmin),(H-190)/(ymax-ymin),160)
    offsetx=(W-(xmax-xmin)*scale)/2-xmin*scale
    offsety=(H-(ymax-ymin)*scale)/2-ymin*scale
    points=[(offsetx+x*scale,offsety+y*scale) for _,x,y in atoms]
    cloudmask=Image.new('L',(W,H));md=ImageDraw.Draw(cloudmask)
    for i,(sym,_,_) in enumerate(atoms):
        x,y=points[i];r=scale*(.42 if sym=='H' else .68)
        md.ellipse((x-r,y-r,x+r,y+r),fill=185)
    for a,b,_ in bonds:md.line((points[a],points[b]),fill=185,width=int(scale*.92))
    cloudmask=cloudmask.filter(ImageFilter.GaussianBlur(12))
    canvas=Image.new('RGB',(W,H),'white');canvas.paste(texture,(0,0),cloudmask)
    draw=ImageDraw.Draw(canvas)
    # All bonds follow the graph. Stereo layout is E: aryl and carbonyl are opposite.
    for a,b,order in bonds:
        x1,y1=points[a];x2,y2=points[b];dx=x2-x1;dy=y2-y1;length=math.hypot(dx,dy)
        off=scale*.045 if order==2 else 0
        offsets=[-off,off] if order==2 else [0]
        for shift in offsets:
            nx=-dy/length*shift;ny=dx/length*shift
            p1=(x1+nx,y1+ny);p2=(x2+nx,y2+ny)
            width=max(3,int(scale*(.035 if atoms[a][0]=='H' or atoms[b][0]=='H' else .055)))
            draw.line((p1,p2),fill='#416873',width=width+3)
            draw.line(((p1[0]-1,p1[1]-1),(p2[0]-1,p2[1]-1)),fill='#90abb3',width=max(1,width//3))
    colors={'C':(45,95,108),'O':(207,58,65),'N':(65,96,200),'H':(219,227,235)}
    for i,(sym,_,_) in enumerate(atoms):
        x,y=points[i];radius=scale*(.105 if sym=='H' else .205)
        r,g,b=colors[sym]
        # Concentric shaded discs and a small highlight create consistent ball-and-stick depth.
        for layer in range(max(2,int(radius)),0,-1):
            t=1-layer/radius;light=.68+.55*t
            rgb=tuple(min(255,int(v*light)) for v in (r,g,b))
            dr=layer;cx=x-t*radius*.20;cy=y-t*radius*.24
            draw.ellipse((cx-dr,cy-dr,cx+dr,cy+dr),fill=rgb)
        hr=radius*.16
        draw.ellipse((x-radius*.37-hr,y-radius*.41-hr,x-radius*.37+hr,y-radius*.41+hr),fill=tuple(int(v*.4+255*.6) for v in colors[sym]))
    canvas.save(dest,optimize=True)
    item['hotspots']={name:[round(points[index][0]/W*100,3),round(points[index][1]/H*100,3)] for name,index in anchors.items()}
    item['image_status']='ready'
    item['image_kind']='AI云层纹理＋化学连接校正球棍模型；定性教学示意，非量子化学计算'
    return {'id':item['id'],'model_requested':'gpt-image-2','source_size':list(source.size),'final_size':[W,H],
            'original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
            'final_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),
            'postprocessing':'AI raster colors blurred into cloud texture; molecule connectivity and hydrogen counts corrected from validated molecular graph; qualitative illustration only.'}

report=[render(item) for item in CATALOG]
(OUT/'catalog.json').write_text(json.dumps(CATALOG,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'asset-provenance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Corrected {len(report)} raster models against catalog connectivity; dimensions {W}x{H}; hotspots calibrated from atom coordinates.')
