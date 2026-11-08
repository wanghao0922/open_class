import {useState} from 'react';
import {Maximize2} from 'lucide-react';
import {Modal} from './components';
import {OptimizedImage} from './OptimizedImage';
import type {Molecule} from './types';
import cinnamicAcid from './assets/spectra/cinnamic-acid.webp';
import cinnamicAcidOriginal from './assets/spectra/cinnamic-acid.jpg';
import paraMethyl from './assets/spectra/para-methoxy-methyl.webp';
import paraMethylOriginal from './assets/spectra/para-methoxy-methyl.jpg';
import orthoEthylhexyl from './assets/spectra/ortho-methoxy-ethylhexyl.webp';
import orthoEthylhexylOriginal from './assets/spectra/ortho-methoxy-ethylhexyl.jpg';
import metaEthylhexyl from './assets/spectra/meta-methoxy-ethylhexyl.webp';
import metaEthylhexylOriginal from './assets/spectra/meta-methoxy-ethylhexyl.jpg';
import paraEthylhexyl from './assets/spectra/para-methoxy-ethylhexyl.webp';
import paraEthylhexylOriginal from './assets/spectra/para-methoxy-ethylhexyl.jpg';
import metaMethyl from './assets/spectra/meta-methoxy-methyl.webp';
import metaMethylOriginal from './assets/spectra/meta-methoxy-methyl.jpg';
import orthoMethyl from './assets/spectra/ortho-methoxy-methyl.webp';
import orthoMethylOriginal from './assets/spectra/ortho-methoxy-methyl.jpg';
import orthoAcid from './assets/spectra/ortho-methoxy-acid.webp';
import orthoAcidOriginal from './assets/spectra/ortho-methoxy-acid.jpg';
import metaAcid from './assets/spectra/meta-methoxy-acid.webp';
import metaAcidOriginal from './assets/spectra/meta-methoxy-acid.jpg';
import paraAcid from './assets/spectra/para-methoxy-acid.webp';
import paraAcidOriginal from './assets/spectra/para-methoxy-acid.jpg';
import cinnamicMethyl from './assets/spectra/cinnamic-methyl.webp';
import cinnamicMethylOriginal from './assets/spectra/cinnamic-methyl.jpg';
import cinnamicEthylhexyl from './assets/spectra/cinnamic-ethylhexyl.webp';
import cinnamicEthylhexylOriginal from './assets/spectra/cinnamic-ethylhexyl.png';

// User-supplied original images. Match complete structures, including ester and position.
const SPECTRA:Record<string,{image:string;original:string;kind:'文献数据重绘'|'计算预测'|'峰位约束拟合预测'|'文献峰位约束拟合预测'}>={
  none__acid:{image:cinnamicAcid,original:cinnamicAcidOriginal,kind:'文献数据重绘'},
  none__methyl:{image:cinnamicMethyl,original:cinnamicMethylOriginal,kind:'文献峰位约束拟合预测'},
  none__ethylhexyl:{image:cinnamicEthylhexyl,original:cinnamicEthylhexylOriginal,kind:'文献峰位约束拟合预测'},
  methoxy_para__methyl:{image:paraMethyl,original:paraMethylOriginal,kind:'文献数据重绘'},
  methoxy_ortho__ethylhexyl:{image:orthoEthylhexyl,original:orthoEthylhexylOriginal,kind:'文献数据重绘'},
  methoxy_meta__ethylhexyl:{image:metaEthylhexyl,original:metaEthylhexylOriginal,kind:'文献数据重绘'},
  methoxy_para__ethylhexyl:{image:paraEthylhexyl,original:paraEthylhexylOriginal,kind:'文献数据重绘'},
  methoxy_meta__methyl:{image:metaMethyl,original:metaMethylOriginal,kind:'计算预测'},
  methoxy_ortho__methyl:{image:orthoMethyl,original:orthoMethylOriginal,kind:'计算预测'},
  methoxy_ortho__acid:{image:orthoAcid,original:orthoAcidOriginal,kind:'文献数据重绘'},
  methoxy_meta__acid:{image:metaAcid,original:metaAcidOriginal,kind:'峰位约束拟合预测'},
  methoxy_para__acid:{image:paraAcid,original:paraAcidOriginal,kind:'文献数据重绘'},
};

export const SPECTRUM_IMAGES=Object.values(SPECTRA).map(item=>item.image);

export function MoleculeSpectrum({molecule}:{molecule:Molecule}){
  const [expanded,setExpanded]=useState(false);
  const spectrum=SPECTRA[molecule.id];
  const title=molecule.name+'紫外吸收光谱';
  return <section className="panel molecule-spectrum" aria-label="紫外吸收光谱" data-molecule-id={molecule.id}>
    <div className="spectrum-heading">
      <h3>紫外吸收光谱</h3>
      {spectrum&&<span className={'spectrum-kind '+(spectrum.kind==='文献数据重绘'?'':'predicted')}>{spectrum.kind}</span>}
    </div>
    {spectrum?<>
      <button type="button" className="spectrum-preview" onClick={()=>setExpanded(true)} aria-label={'放大查看'+title}>
        <OptimizedImage src={spectrum.image} fallbackSrc={spectrum.original} fetchPriority="high" alt={title+'（'+spectrum.kind+'）'} draggable={false}/>
        <span className="spectrum-enlarge"><Maximize2 size={14}/>点击放大查看原图</span>
      </button>
      {expanded&&<Modal title={title} className="spectrum-modal" onClose={()=>setExpanded(false)}>
        <div className="spectrum-original"><img decoding="async" fetchPriority="high" src={spectrum.original} alt={title+'原图'}/></div>
        <a className="text-button spectrum-original-link" href={spectrum.original} target="_blank" rel="noreferrer">在新窗口查看原图<Maximize2 size={14}/></a>
      </Modal>}
    </>:<p className="spectrum-empty">暂无对应光谱</p>}
  </section>;
}
