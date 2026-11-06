export type Connection={port:number;token:string};
declare global {interface Window {__TAURI__?:{core:{invoke:<T>(command:string,args?:Record<string,unknown>)=>Promise<T>}}}}
export const desktop=()=>Boolean(window.__TAURI__);
export async function invoke<T>(command:string,args?:Record<string,unknown>):Promise<T>{
 if(!window.__TAURI__)throw new Error('Desktop service is unavailable');
 return window.__TAURI__.core.invoke<T>(command,args);
}
export async function request<T>(connection:Connection,path:string,options:RequestInit={}):Promise<T>{
 const response=await fetch('http://127.0.0.1:'+connection.port+'/api'+path,{...options,
  headers:{'Content-Type':'application/json',Authorization:'Bearer '+connection.token,...options.headers}});
 if(!response.ok){
  let detail='Request failed ('+response.status+')';
  try{const body=await response.json();if(typeof body.detail==='string')detail=body.detail;}catch{}
  throw new Error(detail);
 }
 return response.json() as Promise<T>;
}
export const post=<T>(connection:Connection,path:string,body:unknown={})=>request<T>(connection,path,{method:'POST',body:JSON.stringify(body)});
export async function exportRun(connection:Connection,id:string,format:'json'|'csv'){
 const response=await fetch('http://127.0.0.1:'+connection.port+'/api/jobs/'+id+'/export?format='+format,{headers:{Authorization:'Bearer '+connection.token}});
 if(!response.ok)throw new Error('Export failed');
 const contents=await response.text(); const filename=id+'.'+format;
 if(desktop())return invoke<string>('save_export',{filename,contents});
 const url=URL.createObjectURL(new Blob([contents],{type:format==='json'?'application/json':'text/csv'}));
 const anchor=document.createElement('a');anchor.href=url;anchor.download=filename;anchor.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000);return 'Downloaded '+filename;
}
