// Each worker advances independently: one slow request cannot stall the queue.
export function preloadImages(urls:string[],timeoutMs=12000){
 const queue=[...new Set(urls.filter(Boolean))];
 let cancelled=false;let next=0;
 const pending=new Set<()=>void>();
 function load(url:string){return new Promise<void>(resolve=>{
  const image=new Image();image.decoding='async';image.fetchPriority='low';
  const finish=()=>{clearTimeout(timer);image.onload=null;image.onerror=null;pending.delete(stop);resolve();};
  const stop=()=>{image.removeAttribute('src');finish();};
  const timer=setTimeout(stop,timeoutMs);
  pending.add(stop);image.onload=finish;image.onerror=finish;
  image.src=new URL(url,location.origin).href;
 });}
 async function worker(){while(!cancelled&&next<queue.length){await load(queue[next++]);}}
 const done=Promise.all(Array.from({length:Math.min(3,queue.length)},()=>worker()));
 return {done,cancel:()=>{cancelled=true;for(const stop of [...pending])stop();}};
}
