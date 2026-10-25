"""Build chemically validated E-cinnamate structures and an aligned teaching catalog."""
import json
from pathlib import Path
from rdkit import Chem
from rdkit.Chem import rdDepictor, rdMolDescriptors
from rdkit.Chem.Draw import rdMolDraw2D

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'frontend' / 'public' / 'molecules'
RINGS = [('none', '', None, None)] + [
    (key, label, pos, tag) for key, label, tag in [('methyl','甲基','C'),('methoxy','甲氧基','OC'),('amino','氨基','N')]
    for pos in ['ortho','meta','para']]
ESTERS = [('acid','',''),('ethyl','乙','CC'),('hexyl','正己','CCCCCC'),('ethylhexyl','2-乙基己','CC(CC)CCCC'),('methyl','甲','C')]
POS_LABEL = {'ortho':'邻','meta':'间','para':'对'}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    previous={x['id']:x for x in json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))} if (OUT/'catalog.json').exists() else {}
    catalog=[]
    # Number ring positions from the cinnamoyl-bearing carbon, keeping drawing orientation fixed.
    template=Chem.MolFromSmiles('O=C(O)/C=C/c1ccccc1')
    rdDepictor.Compute2DCoords(template)
    for key,label,pos,tag in RINGS:
        for ester,elabel,chain in ESTERS:
            if ester=='methyl' and key not in ['none','methoxy']:
                continue
            ring = 'c1ccccc1'
            if pos=='ortho': ring='c1c(X)cccc1'
            if pos=='meta': ring='c1cc(X)ccc1'
            if pos=='para': ring='c1ccc(X)cc1'
            ring=ring.replace('X',tag or '')
            smiles=f'O=C(O{chain})/C=C/{ring}'
            mol=Chem.MolFromSmiles(smiles)
            if mol is None: raise ValueError(smiles)
            Chem.SanitizeMol(mol)
            rdDepictor.GenerateDepictionMatching2DStructure(mol,template)
            ident=f'{key}{"_"+pos if pos else ""}__{ester}'
            name=(POS_LABEL.get(pos,'')+label if key!='none' else '')+'肉桂酸'+(f'-{elabel}酯' if ester!='acid' else '')
            drawer=rdMolDraw2D.MolDraw2DSVG(900,340)
            opts=drawer.drawOptions(); opts.clearBackground=False; opts.bondLineWidth=2.4; opts.minFontSize=15
            drawer.DrawMolecule(mol); drawer.FinishDrawing()
            if ident not in previous:
                (OUT/f'{ident}.svg').write_text(drawer.GetDrawingText(),encoding='utf-8')
            old=previous.get(ident,{})
            catalog.append({'id':ident,'name':name,'ring':key,'position':pos,'ester':ester,
                'smiles':Chem.MolToSmiles(mol,isomericSmiles=True),'formula':rdMolDescriptors.CalcMolFormula(mol),
                'structure':f'/molecules/{ident}.svg','cloud':f'/molecules/{ident}.png',
                'hotspots':old.get('hotspots',{'ortho':[42,39],'meta':[30,34],'para':[24,50],'ester':[79,48]}),
                'image_status':'ready' if (OUT/f'{ident}.png').exists() else 'pending',
                'image_kind':old.get('image_kind','AI教学示意，非量子化学计算')})
    (OUT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Validated {len(catalog)} structures; target:',next(x for x in catalog if x['id']=='methoxy_para__ethylhexyl'))

if __name__=='__main__': main()
