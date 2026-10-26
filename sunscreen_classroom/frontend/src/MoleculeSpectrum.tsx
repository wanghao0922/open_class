import {useState} from 'react';
import {Maximize2} from 'lucide-react';
import {Modal} from './components';
import type {Molecule} from './types';
import cinnamicAcid from './assets/spectra/cinnamic-acid.png';
import paraMethyl from './assets/spectra/para-methoxy-methyl.png';
import orthoEthylhexyl from './assets/spectra/ortho-methoxy-ethylhexyl.png';
import metaEthylhexyl from './assets/spectra/meta-methoxy-ethylhexyl.png';
import paraEthylhexyl from './assets/spectra/para-methoxy-ethylhexyl.png';
import metaMethyl from './assets/spectra/meta-methoxy-methyl.png';
import orthoMethyl from './assets/spectra/ortho-methoxy-methyl.png';
import orthoAcid from './assets/spectra/ortho-methoxy-acid.png';
import metaAcid from './assets/spectra/meta-methoxy-acid.png';
import paraAcid from './assets/spectra/para-methoxy-acid.png';
import cinnamicMethyl from './assets/spectra/cinnamic-methyl.png';
import cinnamicEthylhexyl from './assets/spectra/cinnamic-ethylhexyl.png';

// User-supplied original images. Match complete structures, including ester and position.
const SPECTRA:Record<string,{image:string;kind:'文献数据重绘'|'计算预测'|'峰位约束拟合预测'|'文献峰位约束拟合预测'}>={
  none__acid:{image:cinnamicAcid,kind:'文献数据重绘'},
  none__methyl:{image:cinnamicMethyl,kind:'文献峰位约束拟合预测'},
  none__ethylhexyl:{image:cinnamicEthylhexyl,kind:'文献峰位约束拟合预测'},
  methoxy_para__methyl:{image:paraMethyl,kind:'文献数据重绘'},
  methoxy_ortho__ethylhexyl:{image:orthoEthylhexyl,kind:'文献数据重绘'},
  methoxy_meta__ethylhexyl:{image:metaEthylhexyl,kind:'文献数据重绘'},
  methoxy_para__ethylhexyl:{image:paraEthylhexyl,kind:'文献数据重绘'},
  methoxy_meta__methyl:{image:metaMethyl,kind:'计算预测'},
  methoxy_ortho__methyl:{image:orthoMethyl,kind:'计算预测'},
  methoxy_ortho__acid:{image:orthoAcid,kind:'文献数据重绘'},
  methoxy_meta__acid:{image:metaAcid,kind:'峰位约束拟合预测'},
  methoxy_para__acid:{image:paraAcid,kind:'文献数据重绘'},
};

export function MoleculeSpectrum({molecule}:{molecule:Molecule}){
  const [expanded,setExpanded]=useState(false);
  const spectrum=SPECTRA[molecule.id];
  const title=molecule.name+'紫外吸收光谱';
  return <section className="molecule-spectrum" aria-label="紫外吸收光谱" data-molecule-id={molecule.id}>
    <div className="spectrum-heading">
      <h3>紫外吸收光谱</h3>
      {spectrum&&<span className={'spectrum-kind '+(spectrum.kind==='文献数据重绘'?'':'predicted')}>{spectrum.kind}</span>}
    </div>
    {spectrum?<>
      <button type="button" className="spectrum-preview" onClick={()=>setExpanded(true)} aria-label={'放大查看'+title}>
        <img src={spectrum.image} alt={title+'（'+spectrum.kind+'）'} draggable={false}/>
        <span className="spectrum-enlarge"><Maximize2 size={14}/>点击放大查看原图</span>
      </button>
      {expanded&&<Modal title={title} className="spectrum-modal" onClose={()=>setExpanded(false)}>
        <div className="spectrum-original"><img src={spectrum.image} alt={title+'原图'}/></div>
        <a className="text-button spectrum-original-link" href={spectrum.image} target="_blank" rel="noreferrer">在新窗口查看原图<Maximize2 size={14}/></a>
      </Modal>}
    </>:<p className="spectrum-empty">暂无对应光谱</p>}
  </section>;
}
