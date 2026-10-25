export type FGId = 'carboxyl' | 'aldehyde' | 'ester' | 'hydroxyl' | 'alkene' | 'alkyne';
export type FGCount = {id: FGId; count: number};
export type Row = FGCount[];
export type Molecule = {id:string; name:string; ring:string; position:string|null; ester:string; formula:string; smiles:string; structure:string; cloud:string; hotspots:Record<string,number[]>; image_status:string; image_kind:string};
export type Classroom = {id:number;code:string;name:string;total_groups:number;phase:number;task2:string;task3:string;demo:boolean;joined:number;submitted2:number;submitted3:number;created:string};
export type Answer = {payload:{rows?:Row[];molecule_id?:string};revision:number;updated:string};
export type Group = {id:number|null;number:number;reporter:string;answers:Record<string,Answer>};
export type Identity = {role:'teacher'|'student';classroom?:Classroom;group?:{id:number;number:number;reporter:string};submissions?:Record<string,Answer>};
export type StatCard = {key:string;label:string;items?:Row;molecule_id?:string;count:number;fraction:number;groups?:{id:number;number:number;reporter:string}[]};
export type Stats = {total_groups:number;submitted:number;cards:StatCard[]};

export class ApiError extends Error {status:number; constructor(message:string,status:number){super(message);this.status=status;}}
export async function api<T>(path:string,method='GET',data?:unknown):Promise<T>{
  let res:Response;
  try {res=await fetch('/api'+path,{method,credentials:'same-origin',headers:data?{'Content-Type':'application/json'}:{},body:data?JSON.stringify(data):undefined,signal:AbortSignal.timeout(12000)});}
  catch {throw new ApiError('连接暂时中断，答案已保留。请检查网络后重试。',0);}
  if(!res.ok){const result=await res.json().catch(()=>({}));const detail=result.detail;throw new ApiError(typeof detail==='string'?detail:'填写内容有误，请检查后重试。',res.status);}
  return res.json();
}
export const FG_NAMES:Record<FGId,string>={carboxyl:'羧基',aldehyde:'醛基',ester:'酯基',hydroxyl:'羟基',alkene:'碳碳双键',alkyne:'碳碳三键'};
export const FG_IDS=Object.keys(FG_NAMES) as FGId[];
export const rowKey=(row:Row)=>JSON.stringify([...row].sort((a,b)=>a.id.localeCompare(b.id)));
export const rowName=(row:Row)=>row.map(x=>(x.count>1?`${x.count}个`:'')+FG_NAMES[x.id]).join('＋');
export const PHASES=['了解肉桂酸的性能','探究肉桂酸的结构','修饰肉桂酸分子','设计合成路线'];
