import {useEffect, useRef, useState} from 'react';
import type {PointerEvent as ReactPointerEvent} from 'react';
import {X,Users,ScanLine,MousePointer2,Check,Copy,ArrowUpRight,FlaskConical} from 'lucide-react';
import {QRCodeSVG} from 'qrcode.react';
import {FG_NAMES, PHASES} from './types';
import type {FGId,Molecule,Row,Stats,StatCard,Classroom} from './types';

export function FGDiagram({id,small=false}:{id:FGId;small?:boolean}){
 const base={fill:'none',stroke:'currentColor',strokeWidth:2.2,strokeLinecap:'round' as const};
 let content;
 if(id==='alkene')content=<><path {...base} d="M61 37 L99 37 M61 43 L99 43 M43 30 L27 16 M43 50 L27 64 M117 30 L133 16 M117 50 L133 64"/><text x="51" y="47">C</text><text x="109" y="47">C</text></>;
 else if(id==='alkyne')content=<><path {...base} d="M61 34 H99 M61 40 H99 M61 46 H99 M43 40 H21 M117 40 H139"/><text x="51" y="47">C</text><text x="109" y="47">C</text></>;
 else if(id==='carboxyl')content=<><path {...base} d="M35 43 H58 M73 26 V13 M79 26 V13 M88 43 H103"/><text x="76" y="51">C</text><text x="76" y="12" className="oxygen">O</text><text x="126" y="51" className="oxygen">OH</text></>;
 else if(id==='aldehyde')content=<><path {...base} d="M35 43 H58 M73 26 V13 M79 26 V13 M88 43 H109"/><text x="76" y="51">C</text><text x="76" y="12" className="oxygen">O</text><text x="125" y="51">H</text></>;
 else if(id==='ester')content=<><path {...base} d="M20 43 H47 M62 26 V13 M68 26 V13 M77 43 H95 M119 43 H145"/><text x="65" y="51">C</text><text x="65" y="12" className="oxygen">O</text><text x="107" y="51" className="oxygen">O</text></>;
 else content=<><path {...base} d="M33 40 H63"/><text x="99" y="48" className="oxygen">OH</text></>;
 return <svg className={'fg-diagram '+(small?'small':'')} viewBox="0 -5 160 80" role="img" aria-label={FG_NAMES[id]+'结构简式'}><g textAnchor="middle" fontSize="23" fontFamily="Arial,sans-serif" fill="currentColor">{content}</g></svg>;
}

export function PhaseNav({phase,view,onChange}:{phase:number;view:number;onChange:(n:number)=>void}){
 return <nav className="phases" aria-label="课堂环节">{PHASES.map((name,i)=><button key={name} className={'phase '+(view===i+1?'selected ':'')+(phase===i+1?'current':'')} onClick={()=>onChange(i+1)}><span className="phase-index">{i+1<phase?<Check size={15}/>:String(i+1).padStart(2,'0')}</span><span><small>环节{['一','二','三','四'][i]}</small><strong>{name}</strong></span>{phase===i+1&&<i title="当前课堂环节"/>}</button>)}</nav>;
}

export function Modal({title,onClose,children}:{title:string;onClose:()=>void;children:React.ReactNode}){
 const closeRef=useRef<HTMLButtonElement>(null);
 useEffect(()=>{const original=document.activeElement as HTMLElement;closeRef.current?.focus();const handler=(e:KeyboardEvent)=>{if(e.key==='Escape')onClose();if(e.key==='Tab'){const items=Array.from(closeRef.current?.closest('[role="dialog"]')?.querySelectorAll<HTMLElement>('button,a,input,select')||[]);const first=items[0],last=items[items.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}};document.addEventListener('keydown',handler);return()=>{document.removeEventListener('keydown',handler);original?.focus();}},[onClose]);
 return <div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)onClose();}}><section className="modal" role="dialog" aria-modal="true" aria-label={title}><header><h2>{title}</h2><button ref={closeRef} className="icon-button" onClick={onClose} aria-label="关闭"><X/></button></header>{children}</section></div>;
}

export function JoinModal({room,onClose}:{room:Classroom;onClose:()=>void}){
 const [origin,setOrigin]=useState(location.origin);
 const [copied,setCopied]=useState(false);
 const url=`${origin.replace(/\/$/,'')}/?class=${room.code}`;
 return <Modal title="邀请小组加入课堂" onClose={onClose}><div className="qr-layout"><div className="qr-box"><QRCodeSVG value={url} size={184} level="M" marginSize={3}/></div><div><span className="eyebrow">CLASSROOM CODE</span><div className="big-code">{room.code}</div><p>学生扫码后填写小组号和汇报人姓名。</p><p className="muted">每组使用一个设备汇报即可。</p></div></div><label className="field">学生访问地址<input value={origin} onChange={e=>setOrigin(e.target.value)} placeholder="https://你的服务.onrender.com"/></label>{/localhost|127\.0\.0\.1/.test(origin)&&<div className="info-note">当前二维码仅适合本机演示。其他设备访问时，将上方地址改为可访问的局域网地址或公网域名。</div>}<button className="button primary full" onClick={()=>navigator.clipboard.writeText(url).then(()=>setCopied(true)).catch(()=>setCopied(false))}><Copy size={16}/>{copied?'已复制课堂链接':'复制学生入口链接'}</button></Modal>;
}

const PALETTE=[['#3467be','#dce9ff'],['#077f82','#d9f0ed'],['#8b5bb2','#eee3f7'],['#c07929','#fff0da'],['#b85074','#fae1eb'],['#597550','#e5efdf'],['#587b99','#e0edf4'],['#ac694b','#f6e6dc']];
function colorFor(key:string){let h=0;for(const c of key)h=(Math.imul(h,31)+c.charCodeAt(0))|0;return PALETTE[(h>>>0)%PALETTE.length];}

export function StatsGrid({stats,task,molecules,teacher=false}:{stats:Stats;task:number;molecules:Molecule[];teacher?:boolean}){
 const [detail,setDetail]=useState<StatCard|null>(null);
 const liveDetail=detail?stats.cards.find(x=>x.key===detail.key)||detail:null;
 return <><div className="stats-caption"><span><span className="live-dot"/>全班实时汇总</span><span><b>{stats.submitted}</b> / {stats.total_groups} 组已提交</span></div>{stats.cards.length===0?<div className="empty-state"><Users size={34}/><h3>等待第一份探索结果</h3><p>小组提交后，统计卡片会自动出现在这里。</p></div>:<div className={'stats-grid '+(task===3?'molecule-stats':'')}>{stats.cards.map((card,index)=>{const [edge,fill]=colorFor(card.key);const mol=molecules.find(x=>x.id===card.molecule_id);return <button type="button" className={'stat-card '+(task===3?'molecule-card':'')} style={{'--card-edge':edge,'--card-fill':fill} as React.CSSProperties} key={card.key} onClick={()=>teacher&&setDetail(card)} disabled={!teacher} aria-label={card.label+'，'+card.count+'组'}><div className="stat-fill" style={{height:`${card.fraction*100}%`}}/><div className="stat-content"><div className="card-top"><span className="rank">{String(index+1).padStart(2,'0')}</span>{teacher&&<ArrowUpRight size={16}/>}</div><h3>{card.label}</h3>{task===2?<div className="combo-structures">{card.items?.map((x,i)=><span key={x.id}>{i>0&&<b className="plus">＋</b>}<span>{x.count>1&&<small>×{x.count}</small>}<FGDiagram id={x.id} small/></span></span>)}</div>:mol&&<><img className="molecule-thumb" src={mol.cloud} alt={mol.name+'电子云教学示意'}/><img className="structure-thumb" src={mol.structure} alt={mol.name+'结构简式'}/></>}<div className="stat-count"><strong>{card.count}<small>组</small></strong><span>{card.count}/{stats.total_groups}组 · {Math.round(card.fraction*100)}%</span></div></div></button>;})}</div>}{liveDetail&&teacher&&<Modal title={liveDetail.label} onClose={()=>setDetail(null)}><p className="muted">提到这一结果的小组</p><div className="member-list">{liveDetail.groups?.map(g=><div key={g.id}><span className="group-dot">{g.number}</span><strong>第{g.number}组</strong><span>{g.reporter}</span></div>)}</div></Modal>}</>;
}

// Pointer-based dragging works on touch devices; a tap remains a selection fallback.
export function useCardDrag(onDrop:(item:string,target:string)=>void,onInvalid:()=>void){
 const [drag,setDrag]=useState<{item:string;x:number;y:number}|null>(null);
 const suppress=useRef(false); const cleanup=useRef<()=>void>(()=>{});
 const callback=useRef(onDrop);callback.current=onDrop;
 const invalid=useRef(onInvalid);invalid.current=onInvalid;
 useEffect(()=>()=>cleanup.current(),[]);
 function begin(e:ReactPointerEvent,item:string){
   if(e.button!==0)return;
   cleanup.current();
   const sx=e.clientX,sy=e.clientY;let moved=false;let pointerY=sy;let scroller:number|undefined;
   const move=(event:PointerEvent)=>{pointerY=event.clientY;if(Math.hypot(event.clientX-sx,event.clientY-sy)>7){moved=true;suppress.current=true;setDrag({item,x:event.clientX,y:event.clientY});if(scroller===undefined)scroller=window.setInterval(()=>{if(pointerY<60)window.scrollBy(0,-16);else if(pointerY>window.innerHeight-60)window.scrollBy(0,16);},30);}};
   const finish=(event:PointerEvent)=>{window.clearInterval(scroller);window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',finish);window.removeEventListener('pointercancel',cancel);setDrag(null);if(moved){const target=document.elementFromPoint(event.clientX,event.clientY)?.closest<HTMLElement>('[data-drop]');if(target?.dataset.drop)callback.current(item,target.dataset.drop);else invalid.current();setTimeout(()=>{suppress.current=false;},100);}};
   const cancel=()=>{window.clearInterval(scroller);window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',finish);window.removeEventListener('pointercancel',cancel);setDrag(null);suppress.current=false;};
   cleanup.current=cancel;window.addEventListener('pointermove',move);window.addEventListener('pointerup',finish);window.addEventListener('pointercancel',cancel);
 }
 return {begin,suppress,ghost:drag?<div className="drag-ghost" style={{left:drag.x,top:drag.y}}><FlaskConical size={16}/>{FG_NAMES[drag.item as FGId]||({methyl:'甲基',methoxy:'甲氧基',amino:'氨基',ethyl:'乙醇',hexyl:'正己醇',ethylhexyl:'2-乙基己醇'} as Record<string,string>)[drag.item]}</div>:null};
}

export function InteractionHint(){return <span className="interaction-hint"><MousePointer2 size={14}/>拖拽卡片，或点选卡片后点击目标位置</span>;}
export function StatusPill({status}:{status:string}){return <span className={'status-pill '+status}><span/>{status==='open'?'正在进行':status==='closed'?'已结束':'尚未开放'}</span>;}
