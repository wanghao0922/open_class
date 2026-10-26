import {useEffect, useState} from 'react';
import {Download,RotateCcw,Trash2} from 'lucide-react';
import {api} from './types';
import type {Classroom} from './types';
import {Modal} from './components';

export function DeleteClassModal({room,onClose,onDeleted}:{room:Classroom;onClose:()=>void;onDeleted:(id:number)=>void}){
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 async function remove(){
  setBusy(true);setError('');
  try{await api(`/teacher/classes/${room.id}`,'DELETE');onDeleted(room.id);onClose();}
  catch(e){setError((e as Error).message);}
  finally{setBusy(false);}
 }
 return <Modal title="删除课堂" onClose={()=>{if(!busy)onClose();}}>
  <div className="class-delete-summary"><Trash2 size={24}/><div><strong>{room.name}</strong><p>课堂码 {room.code} · {room.joined} 组已加入</p></div></div>
  <p>确认将这个课堂移入“已删除课堂”？删除后，课堂将从“我的课堂”移除，学生无法继续加入和作答。</p>
  <div className="info-note">小组答案和历史记录会保留，可在“已删除课堂”中恢复。恢复后需由老师重新开放任务。</div>
  <p className="muted">需要留存文件时，可先导出课堂记录。</p>
  <div className="button-row class-delete-exports"><a className="button small" href={`/api/teacher/classes/${room.id}/export?format=csv`}><Download size={15}/>导出CSV</a><a className="button small" href={`/api/teacher/classes/${room.id}/export?format=json`}>导出完整记录</a></div>
  {error&&<div className="info-note warning" role="alert">{error}</div>}
  <div className="button-row class-delete-actions"><button className="button" disabled={busy} onClick={onClose}>取消</button><button className="button danger" disabled={busy} onClick={remove}><Trash2 size={16}/>{busy?'正在删除…':'确认删除课堂'}</button></div>
 </Modal>;
}

type DeletedClass=Classroom&{deleted_at:string};
export function DeletedClassesModal({onClose,onRestored}:{onClose:()=>void;onRestored:(room:Classroom)=>void}){
 const [rooms,setRooms]=useState<DeletedClass[]>([]);
 const [loading,setLoading]=useState(true);
 const [busy,setBusy]=useState<number|null>(null);
 const [error,setError]=useState('');
 useEffect(()=>{let live=true;api<DeletedClass[]>('/teacher/trash').then(result=>{if(live)setRooms(result);}).catch(e=>{if(live)setError((e as Error).message);}).finally(()=>{if(live)setLoading(false);});return()=>{live=false;};},[]);
 async function restore(room:DeletedClass){
  setBusy(room.id);setError('');
  try{const restored=await api<Classroom>(`/teacher/classes/${room.id}/restore`,'POST');setRooms(prev=>prev.filter(x=>x.id!==room.id));onRestored(restored);}
  catch(e){setError((e as Error).message);}
  finally{setBusy(null);}
 }
 return <Modal title="已删除课堂" onClose={onClose}>
  <p className="muted">恢复后，课堂码、小组答案和历史记录保持原样。需要继续作答时，请重新开放任务。</p>
  {error&&<div className="info-note warning" role="alert">{error}</div>}
  {loading?<p role="status">正在读取…</p>:rooms.length===0?<div className="trash-empty">暂无已删除的课堂</div>:<div className="deleted-class-list">{rooms.map(room=><div className="deleted-class-row" key={room.id}><div><strong>{room.name}</strong><small>{room.code} · {room.total_groups}组{room.demo?' · 演示课堂':''}</small><small>删除于 {new Date(room.deleted_at).toLocaleString('zh-CN')}</small></div><button className="button small" disabled={busy!==null} onClick={()=>restore(room)} aria-label={`恢复课堂 ${room.code}`}><RotateCcw size={14}/>{busy===room.id?'恢复中…':'恢复'}</button></div>)}</div>}
 </Modal>;
}
