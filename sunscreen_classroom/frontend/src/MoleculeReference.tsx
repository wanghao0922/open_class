import {BookOpen} from 'lucide-react';
import type {Molecule} from './types';
import './molecule-reference.css';

export function MoleculeReference({molecule}:{molecule:Molecule}){
  if(molecule.id!=='methoxy_para__methyl')return null;

  return <aside className="molecule-reference" aria-label="对甲氧基肉桂酸甲酯资料卡片">
    <div className="molecule-reference-heading"><BookOpen size={17} aria-hidden="true"/><h4>资料卡片 · 对甲氧基肉桂酸甲酯</h4></div>
    <p><strong>熔点：</strong>约为90℃</p>
    <p>在油相中的溶解度较低，化妆品中添加需要考虑溶解和低温析晶问题。</p>
  </aside>;
}
