import {useEffect,useState} from 'react';
import {Connection,desktop,invoke,request,post,exportRun} from './api';
import {Dataset,RecordRow,Job,Result,Evaluation,Stage,active,resumable,label,assessmentValue,percent} from './domain';

type View='Workspace'|'Datasets'|'Assessments'|'Validation'|'Run history'|'Settings';
const views:View[]=['Workspace','Datasets','Assessments','Validation','Run history','Settings'];
const icons=['◈','▤','✓','◎','◷','⚙'];
function Pill({value}:{value:string}){return <span className={'pill '+value}>{label(value)}</span>}
export default function App(){
 const [connection,setConnection]=useState<Connection|null>(null),[port,setPort]=useState('8765'),[token,setToken]=useState('');
 const [booting,setBooting]=useState(desktop()),[view,setView]=useState<View>('Workspace');
 const [datasets,setDatasets]=useState<Dataset[]>([]),[jobs,setJobs]=useState<Job[]>([]);
 const [datasetId,setDatasetId]=useState(''),[records,setRecords]=useState<RecordRow[]>([]),[offset,setOffset]=useState(0);
 const [jobId,setJobId]=useState(''),[results,setResults]=useState<Result[]>([]),[evaluation,setEvaluation]=useState<Evaluation|null>(null);
 const [stage,setStage]=useState<Stage>('article'),[mode,setMode]=useState('demo'),[model,setModel]=useState('');
 const [consent,setConsent]=useState(false),[fetchRepos,setFetchRepos]=useState(false),[key,setKey]=useState('');
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[loading,setLoading]=useState(false);
 const dataset=datasets.find(d=>d.id===datasetId),job=jobs.find(j=>j.id===jobId);
 const [detail,setDetail]=useState<string|null>(null);
 const refresh=async(c=connection)=>{if(c){const [d,j]=await Promise.all([request<Dataset[]>(c,'/datasets'),request<Job[]>(c,'/jobs')]);setDatasets(d);setJobs(j);}};
 async function connect(c:Connection){await request(c,'/health');setConnection(c);setToken('');setError('');await refresh(c);}
 async function bootstrap(){
  setBooting(true);setError('');
  try{
   const c=await invoke<Connection>('backend_info');
   let ready=false;
   for(let i=0;i<40;i++){try{await connect(c);ready=true;break;}catch{await new Promise(r=>setTimeout(r,250));}}
   if(!ready)throw new Error('The local backend did not become ready. Restart the application; interrupted runs will remain available.');
  }catch(e){setError((e as Error).message);}finally{setBooting(false);}
 }
 useEffect(()=>{if(desktop())void bootstrap();},[]);
 useEffect(()=>{if(!connection)return;const timer=setInterval(()=>{void refresh().catch(e=>setError(e.message));},1500);return()=>clearInterval(timer);},[connection]);
 useEffect(()=>{
  if(!connection||!datasetId){setRecords([]);return;}
  let current=true;setLoading(true);
  request<{records:RecordRow[]}>(connection,'/datasets/'+datasetId+'?offset='+offset+'&limit=25')
   .then(data=>{if(current)setRecords(data.records)}).catch(e=>{if(current)setError(e.message)}).finally(()=>{if(current)setLoading(false)});
  return()=>{current=false};
 },[connection,datasetId,offset]);
 useEffect(()=>{
  if(!connection||!jobId){setResults([]);setEvaluation(null);return;}
  let current=true;
  const load=async()=>{const [r,e]=await Promise.all([request<Result[]>(connection,'/jobs/'+jobId+'/results'),request<Evaluation>(connection,'/jobs/'+jobId+'/evaluation')]);if(current){setResults(r);setEvaluation(e);}};
  void load().catch(e=>setError(e.message));
  const timer=setInterval(()=>void load().catch(e=>setError(e.message)),1500);
  return()=>{current=false;clearInterval(timer)};
 },[connection,jobId]);
 async function action(work:()=>Promise<void>){setBusy(true);setError('');setNotice('');try{await work()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 function chooseDataset(id:string){setDatasetId(id);setRecords([]);setOffset(0);setDetail(null)}
 async function loadDemo(){const d=await post<Dataset>(connection!,'/datasets/demo');await refresh();chooseDataset(d.id);setMode('demo');setNotice('Synthetic demonstration loaded. No network inference is used.');}
 async function importFile(file:File){
  if(file.size>25*1024*1024)throw new Error('The import limit is 25 MiB.');
  const base64=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('Cannot read file'));reader.readAsDataURL(file)});
  const d=await post<Dataset>(connection!,'/datasets/import',{filename:file.name,content_base64:base64});await refresh();chooseDataset(d.id);setMode('live');setView('Datasets');
 }
 async function start(){
  const j=await post<Job>(connection!,'/jobs',{dataset_id:datasetId,stage,mode,model:mode==='demo'?'recorded-demo-v1':model,allow_network:consent,fetch_repositories:fetchRepos});
  setJobId(j.id);await refresh();setView('Assessments');
 }
 function chooseJob(j:Job){setJobId(j.id);chooseDataset(j.dataset_id);setStage(j.config.stage);setView('Assessments')}
 if(!connection)return <main className="connect"><div className="brandmark">T<span>C</span></div><p className="eyebrow">TRIPODCODE WORKSPACE</p><h1>Research, with a record.</h1><p>Assess articles and code repositories in a workspace that keeps every input, decision, and result traceable.</p>
  {booting?<p role="status">Starting the local research service…</p>:desktop()?<button onClick={()=>void bootstrap()}>Retry connection</button>:<form onSubmit={e=>{e.preventDefault();void action(()=>connect({port:Number(port),token}))}}>
  <label>Local backend port<input value={port} inputMode="numeric" onChange={e=>setPort(e.target.value)} required/></label>
  <label>Session token<input type="password" value={token} onChange={e=>setToken(e.target.value)} autoComplete="off" required/></label>
  <p className="hint">For development, use the port and token in your workspace’s session.json. The installed desktop app connects automatically.</p><button disabled={busy}>Connect to workspace</button></form>}
  {error&&<p className="error" role="alert">{error}</p>}</main>;
 return <div className="shell">
 <aside><a className="brand" href="#" onClick={e=>{e.preventDefault();setView('Workspace')}}><span className="brandmark small">T<span>C</span></span><span>TRIPOD<span className="brandlight">Code</span><small>RESEARCH WORKSPACE</small></span></a>
 <div className="navlabel">WORKBENCH</div><nav aria-label="Main navigation">{views.map((v,i)=><button key={v} aria-current={view===v?'page':undefined} className={view===v?'selected':''} onClick={()=>setView(v)}><span aria-hidden="true">{icons[i]}</span>{v}</button>)}</nav>
 <div className="sidefoot"><span className="dot"/> Local service connected<small>Workspace v0.1 · Research preview</small><p>Your data stays on this device.<br/>Live AI assessment sends selected content to OpenAI.</p></div></aside>
 <div className="main"><header><span>Research / <strong>{view}</strong></span><span className="header-status"><span className="dot"/>{jobs.filter(j=>active(j.state)).length} active runs</span></header>
 <main><div className="pageheading"><div><p className="eyebrow">EVIDENCE · CODE · REPRODUCIBILITY</p><h1>{view==='Workspace'?'Your research workspace':view}</h1><p className="subtitle">{view==='Workspace'?'A clear path from source material to reviewable evidence.':'Inspect the evidence. Keep the distinctions that matter.'}</p></div><button className="secondary" disabled={busy} onClick={()=>void action(loadDemo)}>Load offline demo <span>↗</span></button></div>
 {error&&<div className="alert error" role="alert">{error}<button aria-label="Dismiss error" onClick={()=>setError('')}>×</button></div>}
 {notice&&<div className="alert" role="status">{notice}<button aria-label="Dismiss notification" onClick={()=>setNotice('')}>×</button></div>}
 {dataset?.kind==='demo'&&<div className="demo-banner"><strong>Synthetic demonstration</strong><span>Recorded example outputs. No AI call, downloaded repository, or research conclusion.</span></div>}
 {view==='Workspace'&&<><section className="stats" aria-label="Workspace summary">
 <article><span>Datasets</span><strong>{datasets.length.toString().padStart(2,'0')}</strong><small>Immutable imported sources</small></article>
 <article><span>Research records</span><strong>{datasets.reduce((s,d)=>s+d.row_count,0).toString().padStart(2,'0')}</strong><small>Ready for inspection</small></article>
 <article><span>Assessment runs</span><strong>{jobs.length.toString().padStart(2,'0')}</strong><small>{jobs.filter(j=>j.state==='succeeded').length} fully completed</small></article>
 <article><span>Needs attention</span><strong className="amber">{jobs.filter(j=>['incomplete','interrupted','failed'].includes(j.state)).length.toString().padStart(2,'0')}</strong><small>Review before interpreting</small></article></section>
 <div className="workspace-grid"><section className="card"><div className="section-heading"><h2>Start a research run</h2><span className="step">01 → 03</span></div><p>Choose a source, configure an assessment, then review its evidence.</p>
 <div className="workflow"><div><b>01</b><strong>Bring your data</strong><p>CSV, JSON or Parquet. Originals are preserved.</p></div><div><b>02</b><strong>Assess with provenance</strong><p>Record the input, prompt, schema, code and model.</p></div><div><b>03</b><strong>Validate and export</strong><p>Compare with human annotations and inspect exclusions.</p></div></div>
 <button onClick={()=>setView('Datasets')}>Open datasets →</button></section>
 <section className="card tinted"><p className="eyebrow">RESEARCH INTEGRITY</p><h2>Every result has context.</h2><p>A negative assessment, a missing observation and a failed request mean different things. This workspace keeps them separate.</p><div className="legend"><Pill value="succeeded"/><Pill value="missing"/><Pill value="failed"/><Pill value="inapplicable"/></div><button className="textbutton" onClick={()=>setView('Validation')}>Explore validation →</button></section></div></>}
 {(view==='Datasets'||view==='Workspace')&&<section className="card"><div className="section-heading"><div><h2>Datasets</h2><p>Inspect a bounded sample before starting a run.</p></div><label className="button secondary">Import dataset<input className="fileinput" type="file" accept=".json,.csv,.parquet" disabled={busy} aria-label="Import dataset" onChange={e=>{const file=e.target.files?.[0];if(file)void action(()=>importFile(file));e.target.value=''}}/></label></div>
 {!datasets.length?<div className="empty"><strong>Your workspace is ready.</strong><p>Import a dataset or load the six-record offline demonstration.</p></div>:<div className="tablewrap"><table><thead><tr><th>Dataset</th><th>Records</th><th>Source</th><th>Imported</th><th/></tr></thead><tbody>{datasets.map(d=><tr key={d.id} className={d.id===datasetId?'chosen':''}><td><strong>{d.name}</strong><small>{d.sha256.slice(0,12)}…</small></td><td>{d.row_count}</td><td><Pill value={d.kind}/></td><td>{new Date(d.created).toLocaleDateString()}</td><td><button className="textbutton" onClick={()=>{chooseDataset(d.id);setView('Datasets')}}>Inspect →</button></td></tr>)}</tbody></table></div>}</section>}
 {view==='Datasets'&&dataset&&<><section className="card"><div className="section-heading"><h2>Inspect: {dataset.name}</h2><span>{offset+1}–{Math.min(offset+25,dataset.row_count)} of {dataset.row_count}</span></div>
 {loading?<p role="status">Loading records…</p>:<div className="recordlist">{records.map(r=><article key={r.id}><button className="recordtitle" onClick={()=>setDetail(detail===r.id?null:r.id)} aria-expanded={detail===r.id}><code>{r.id}</code><strong>{r.title}</strong><span>{detail===r.id?'−':'+'}</span></button>{detail===r.id&&<div className="recorddetail"><h3>Article text</h3><pre>{r.text||'Missing article text'}</pre><h3>Repository input</h3><pre>{r.repo_url||'No repository URL'}{'\n'}{r.repo_content||'No supplied repository content'}</pre><h3>Human annotations</h3><pre>{JSON.stringify(r.human,null,2)}</pre></div>}</article>)}</div>}
 <div className="pagination"><button className="secondary" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-25))}>Previous</button><button className="secondary" disabled={offset+25>=dataset.row_count} onClick={()=>setOffset(offset+25)}>Next</button></div></section>
 <section className="card"><h2>Configure assessment</h2><div className="formgrid"><label>Research stage<select value={stage} onChange={e=>setStage(e.target.value as Stage)}><option value="article">Article assessment</option><option value="repository">Repository assessment</option></select></label><label>Execution<select value={mode} onChange={e=>setMode(e.target.value)}><option value="demo" disabled={dataset.kind!=='demo'}>Offline recorded demonstration</option><option value="live">Live OpenAI assessment</option></select></label></div>
 {mode==='live'&&<div className="liveconfig"><label>Model identifier<input value={model} placeholder="Enter a model available to your API account" onChange={e=>setModel(e.target.value)}/></label><p>Live runs are limited to 20 records. Each usable record can incur one API request. Set your key in Settings.</p><label className="check"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>I authorize this run to send selected content to OpenAI and incur API charges.</label>{stage==='repository'&&<label className="check"><input type="checkbox" checked={fetchRepos} onChange={e=>setFetchRepos(e.target.checked)}/>Retrieve public GitHub snapshots when repository content is missing.</label>}</div>}
 <button disabled={busy||(mode==='demo'&&dataset.kind!=='demo')||(mode==='live'&&(!consent||!model.trim()||dataset.row_count>20))} onClick={()=>void action(start)}>{busy?'Starting…':'Start '+(stage==='article'?'article':'repository')+' assessment →'}</button></section></>}
 {(view==='Assessments'||view==='Validation')&&<><section className="card compact"><label>Assessment run<select value={jobId} onChange={e=>{const j=jobs.find(x=>x.id===e.target.value);if(j){setJobId(j.id);chooseDataset(j.dataset_id)}}}><option value="">Select a run</option>{jobs.map(j=><option key={j.id} value={j.id}>{label(j.config.stage)} · {j.id.slice(0,8)} · {label(j.state)}</option>)}</select></label></section>
 {!job?<div className="card empty"><strong>No run selected</strong><p>Select a run above or start an assessment from Datasets.</p></div>:<><section className="card"><div className="section-heading"><div><h2>{label(job.config.stage)} assessment</h2><p><code>{job.id}</code> · {job.config.model}</p></div><Pill value={job.state}/></div><progress value={job.progress} max={job.total} aria-label="Completed records"/><div className="section-heading"><span>{job.progress} / {job.total} records processed</span><div className="actions">{active(job.state)&&<button className="secondary" disabled={busy} onClick={()=>void action(async()=>{await post(connection,'/jobs/'+job.id+'/cancel');await refresh()})}>Cancel run</button>}{resumable(job.state)&&<button className="secondary" disabled={busy} onClick={()=>void action(async()=>{await post(connection,'/jobs/'+job.id+'/resume');await refresh()})}>Resume compatible run</button>}<button className="secondary" onClick={()=>void action(async()=>setNotice(await exportRun(connection,job.id,'csv')))}>Export CSV</button><button onClick={()=>void action(async()=>setNotice(await exportRun(connection,job.id,'json')))}>Export with provenance</button></div></div>{job.error&&<p className="error">{job.error}</p>}
 <details><summary>Run provenance</summary><pre>{JSON.stringify(job.provenance,null,2)}</pre></details></section>
 {view==='Assessments'&&<section className="card"><div className="section-heading"><h2>Assessment review</h2><button className="textbutton" onClick={()=>setView('Validation')}>Compare with human annotations →</button></div>{!results.length?<p className="empty">Results appear as each record is saved.</p>:results.map(r=><details className="assessment" key={r.record_id}><summary><strong>{r.record_id}</strong><Pill value={r.status}/></summary>{r.error&&<p className="error">{r.error}</p>}{r.assessment?<table><thead><tr><th>Assessment field</th><th>Model result</th><th>Human annotation</th></tr></thead><tbody>{Object.entries(r.assessment).map(([k,v])=><tr key={k}><td>{label(k)}</td><td className={v===false?'negative':v===true?'positive':''}>{assessmentValue(k,v,r.assessment!)}</td><td>{records.find(x=>x.id===r.record_id)?.human[job.config.stage]?.[k]===undefined?'Not annotated':assessmentValue(k,records.find(x=>x.id===r.record_id)!.human[job.config.stage]![k],records.find(x=>x.id===r.record_id)!.human[job.config.stage])}</td></tr>)}</tbody></table>:<p>No assessment value. This record is {label(r.status).toLowerCase()}.</p>}<details><summary>Record evidence</summary><pre>{JSON.stringify(r.evidence,null,2)}</pre></details></details>)}</section>}
 {view==='Validation'&&<section className="card"><h2>Comparison with human annotations</h2><p>{evaluation?.note}</p>{!evaluation?.metrics.length?<div className="empty">No boolean human annotations are available for this stage.</div>:<div className="tablewrap"><table><thead><tr><th>Field</th><th>Paired n</th><th>Excluded</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1</th><th>TP / TN / FP / FN</th></tr></thead><tbody>{evaluation.metrics.map(m=><tr key={m.field}><td>{label(m.field)}</td><td>{m.n}</td><td>{m.excluded}</td><td>{percent(m.accuracy)}</td><td>{percent(m.precision)}</td><td>{percent(m.recall)}</td><td>{percent(m.f1)}</td><td>{m.tp} / {m.tn} / {m.fp} / {m.fn}</td></tr>)}</tbody></table></div>}<p className="hint">Metric definition: {evaluation?.version}. These descriptive metrics do not replace a prespecified validation analysis. Undefined denominators display “—”.</p></section>}</>}</>}
 {view==='Run history'&&<section className="card"><h2>Durable run history</h2><p>Completed records survive cancellation and application restarts. Changed inputs or methods require a new run.</p>{!jobs.length?<div className="empty">No assessment runs yet.</div>:<div className="tablewrap"><table><thead><tr><th>Run</th><th>Stage / model</th><th>Progress</th><th>Status</th><th/></tr></thead><tbody>{jobs.map(j=><tr key={j.id}><td><code>{j.id.slice(0,12)}</code><small>{new Date(j.created).toLocaleString()}</small></td><td>{label(j.config.stage)}<small>{j.config.model}</small></td><td>{j.progress}/{j.total}</td><td><Pill value={j.state}/></td><td><button className="textbutton" onClick={()=>chooseJob(j)}>Review →</button></td></tr>)}</tbody></table></div>}</section>}
 {view==='Settings'&&<section className="card settings"><h2>OpenAI credentials</h2><p>Save a key in the operating system’s credential store. It is never included in datasets, run records, exports, or frontend files.</p><form onSubmit={e=>{e.preventDefault();void action(async()=>{await post(connection,'/credentials',{key});setKey('');setNotice('Credential saved in the operating-system keychain.')})}}><label>API key<input type="password" value={key} onChange={e=>setKey(e.target.value)} autoComplete="off" required/></label><button disabled={busy}>Save in keychain</button></form><h2>Offline and online operations</h2><p>Importing data, inspecting records, running the recorded demonstration, evaluating results and exporting work offline. New model assessments require OpenAI access. Optional repository retrieval requires GitHub access.</p><h2>Local access</h2><p>The backend listens on loopback and requires a per-session token. The desktop app manages startup and shutdown automatically.</p></section>}
 <footer>TRIPODCode <span>Preserving the distinction between evidence and absence.</span></footer>
 </main></div></div>;
}
