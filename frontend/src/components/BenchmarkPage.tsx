import SteeringResearchPanel from './SteeringResearchPanel';
import {useEffect, useMemo, useState} from 'react';
import {BarChart, Bar, CartesianGrid, Legend, LineChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine} from 'recharts';
import {Upload, RefreshCw} from 'lucide-react';

type ModelName = 'median' | 'ols' | 'piecewise_bic' | 'bayesian_mean';
type Score = {mae_s:number; rmse_s:number};
type Fold = {stint:string;train_laps:number;test_laps:number;models:Partial<Record<ModelName,Score>>};
type Event = {circuit:string;matched_circuit?:string;status:string;reason?:string;n_laps?:number;slope?:number;ci95?:[number,number];predictive_benchmark?:{ready:boolean;folds:Fold[]}};
type Report = {source:string;year:number;driver:number;events:Event[];limitations?:string};
const models:ModelName[]=['median','ols','piecewise_bic','bayesian_mean'];
const names:Record<ModelName,string>={median:'Median baseline',ols:'OLS',piecewise_bic:'Piecewise BIC',bayesian_mean:'Bayesian mean'};
const colors:Record<ModelName,string>={median:'#9ca3af',ols:'#60a5fa',piecewise_bic:'#f97373',bayesian_mean:'#34d399'};
const number=(x:number|undefined,digits=3)=> x==null||!Number.isFinite(x)?'—':x.toFixed(digits);

function validate(input:unknown):Report {
 if(!input||typeof input!=='object')throw new Error('Expected a benchmark JSON object.');
 const x=input as Report;
 if(x.source!=='OpenF1'||!Array.isArray(x.events)||typeof x.year!=='number')throw new Error('Expected an OpenF1 cross_event_real.json report.');
 for(const e of x.events){
  if(typeof e.circuit!=='string'||typeof e.status!=='string')throw new Error('Invalid event details.');
  for(const f of e.predictive_benchmark?.folds??[]){
   if(!Number.isInteger(f.test_laps)||f.test_laps<=0||!f.models||typeof f.models!=='object')throw new Error('Invalid held-out fold.');
   for(const m of models){const score=f.models[m];if(score&&(!Number.isFinite(score.mae_s)||!Number.isFinite(score.rmse_s)||score.mae_s<0||score.rmse_s<0))throw new Error('Invalid error metrics.');}
  }
 }
 return x;
}
// Every model's pooled MAE is weighted by its OWN observed test-lap counts.
// RMSE pools squared errors: sqrt(sum(n * fold_rmse^2) / sum(n)).
function pooled(folds:Fold[], model:ModelName){
 const present=folds.filter(f=>f.models[model]);
 const n=present.reduce((a,f)=>a+f.test_laps,0);
 if(!n)return null;
 return {mae:present.reduce((a,f)=>a+f.test_laps*f.models[model]!.mae_s,0)/n,
         rmse:Math.sqrt(present.reduce((a,f)=>a+f.test_laps*f.models[model]!.rmse_s**2,0)/n),
         laps:n,folds:present.length};
}
export default function BenchmarkPage(){
 const [report,setReport]=useState<Report|null>(null),[source,setSource]=useState(''),[error,setError]=useState(''),[loading,setLoading]=useState(false);
 const [metric,setMetric]=useState<'mae'|'rmse'>('mae');
 async function load(){
  setLoading(true);setError('');
  try{const response=await fetch('/api/benchmark/latest');if(!response.ok){const result=await response.json().catch(()=>({}));throw new Error(result.detail||`HTTP ${response.status}`);}
   setReport(validate(await response.json()));setSource('Backend results/cross_event_real.json');
  }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setLoading(false)}
 }
 useEffect(()=>{void load()},[]);
 async function upload(file:File|undefined){if(!file)return;try{if(file.size>4_000_000)throw new Error('JSON file is too large (max 4 MB).');const x=validate(JSON.parse(await file.text()));setReport(x);setSource(`Uploaded: ${file.name}`);setError('');}catch(e){setError(e instanceof Error?e.message:String(e));}}
 const computed=report?.events.filter(e=>e.status==='computed')??[];
 const allFolds=computed.flatMap(e=>(e.predictive_benchmark?.folds??[]));
 const byRace=useMemo(()=>computed.map(e=>{
  const folds=e.predictive_benchmark?.folds??[];const values:Record<string,string|number|null>={circuit:e.circuit};
  for(const m of models){const score=pooled(folds,m);values[m]=score?(metric==='mae'?score.mae:score.rmse):null;}
  return values;
 }),[report,metric]);
 const byStint=useMemo(()=>computed.flatMap(e=>(e.predictive_benchmark?.folds??[]).map(f=>{
  const row:Record<string,string|number|null>={stint:`${e.circuit} S${f.stint}`,test_laps:f.test_laps};
  for(const m of models)row[m]=f.models[m]?.[`${metric}_s`]??null;
  return row;
 })),[report,metric]);
 const allPooled=models.map(m=>({model:m,...pooled(allFolds,m)}));
 const paired=models.filter(m=>m!=='median').map(m=>{
  const sameFolds=allFolds.filter(f=>f.models[m]&&f.models.median);
  const candidate=pooled(sameFolds,m);const baseline=pooled(sameFolds,'median');
  return {model:m,laps:candidate?.laps??0,baseline:baseline?.mae??null,modelMae:candidate?.mae??null,improvement:candidate&&baseline&&baseline.mae>0?100*(baseline.mae-candidate.mae)/baseline.mae:null};
 });
 const tested=allFolds.reduce((sum,f)=>sum+f.test_laps,0);
 const slopeData=computed.filter(e=>Number.isFinite(e.slope)).map(e=>({circuit:e.circuit,slope:e.slope,lo:e.ci95?.[0],hi:e.ci95?.[1]}));
 const hasResults=allFolds.length>0;
 return <section className="page benchmark-page">
  <div className="page-heading"><div><div className="kicker">REPRODUCIBLE REAL-DATA EVIDENCE</div><h2>Research Results</h2><p>Compare model errors on future laps within each stint. This page reads your executed OpenF1 benchmark; it never generates fictional scores.</p></div><div className="session-pill">OPENF1 · HISTORICAL</div></div>
  <div className="benchmark-toolbar"><button type="button" className="run-btn" onClick={()=>void load()} disabled={loading}><RefreshCw size={14}/> {loading?'LOADING':'RELOAD SAVED RESULT'}</button><label className="benchmark-upload"><Upload size={14}/> IMPORT JSON<input type="file" accept=".json,application/json" onChange={e=>void upload(e.target.files?.[0])}/></label><label className="benchmark-metric">METRIC <select value={metric} onChange={e=>setMetric(e.target.value as 'mae'|'rmse')}><option value="mae">MAE (s)</option><option value="rmse">RMSE (s)</option></select></label></div>
  {source&&<p className="benchmark-subtle">Data source: {source} · No live feed is required to view a saved result.</p>}
  {error&&<div className="error-box">{error} {report&&<span> Your currently loaded report remains visible.</span>}</div>}
  {!report&&<div className="card empty-state"><strong>No evaluated race result loaded</strong><span>Run the backend benchmark, then click Reload, or import cross_event_real.json using the button above.</span></div>}
  {report&&<>
   <div className="stat-grid"><div className="stat"><span>SEASON / DRIVER</span><strong>{report.year} · #{report.driver}</strong><small>Reported source: {report.source}</small></div><div className="stat"><span>RACES COMPUTED</span><strong>{computed.length} / {report.events.length}</strong><small>{report.events.length-computed.length} unavailable</small></div><div className="stat"><span>RACE LAP RECORDS</span><strong>{computed.reduce((s,e)=>s+(e.n_laps??0),0)}</strong><small>Not all used for testing</small></div><div className="stat"><span>HELD-OUT TEST LAPS</span><strong>{tested}</strong><small>{allFolds.length} within-stint folds</small></div></div>
   {!hasResults&&<div className="card">This JSON contains fitted slopes but no held-out test metrics. Run the v7+ benchmark again to populate comparison charts.</div>}
   {hasResults&&<>
   <div className="card benchmark-chart"><div className="card-head"><div><div className="kicker">COMPARISON 01</div><h3>Model error by Grand Prix</h3></div><div className="tiny-badge">TEST-LAP WEIGHTED {metric.toUpperCase()}</div></div><ResponsiveContainer width="100%" height={330}><BarChart data={byRace} margin={{top:8,right:16,bottom:14,left:2}}><CartesianGrid stroke="#202832" strokeDasharray="3 3"/><XAxis dataKey="circuit" tick={{fill:'#aab3bf',fontSize:11}}/><YAxis tick={{fill:'#aab3bf',fontSize:10}} unit=" s"/><Tooltip formatter={(v:any)=>[`${number(Number(v))} s`, '']} contentStyle={{background:'#0e141c',border:'1px solid #27313e',color:'#eef2f6'}}/><Legend/>{models.map(m=><Bar key={m} dataKey={m} name={names[m]} fill={colors[m]} maxBarSize={35}/>)}</BarChart></ResponsiveContainer><p className="benchmark-subtle">Race values pool each model's available folds by their held-out lap counts. A missing bar means the model was not computed, not zero error.</p></div>
   <div className="card benchmark-chart"><div className="card-head"><div><div className="kicker">COMPARISON 02</div><h3>Where model errors change by stint</h3></div><div className="tiny-badge">FUTURE-LAP {metric.toUpperCase()}</div></div><div style={{overflowX:'auto'}}><div style={{minWidth:Math.max(700,byStint.length*105)}}><ResponsiveContainer width="100%" height={340}><LineChart data={byStint} margin={{top:8,right:25,bottom:35,left:0}}><CartesianGrid stroke="#202832" strokeDasharray="3 3"/><XAxis dataKey="stint" angle={-24} textAnchor="end" interval={0} tick={{fill:'#aab3bf',fontSize:10}}/><YAxis tick={{fill:'#aab3bf',fontSize:10}} unit=" s"/><Tooltip contentStyle={{background:'#0e141c',border:'1px solid #27313e',color:'#eef2f6'}} formatter={(v:any)=>`${number(Number(v))} s`}/><Legend verticalAlign="top"/>{models.map(m=><Line key={m} type="linear" dataKey={m} name={names[m]} stroke={colors[m]} strokeWidth={2} connectNulls={false} dot={{r:4}}/>)}</LineChart></ResponsiveContainer></div></div><p className="benchmark-subtle">The connecting lines only aid reading across discrete stints; they do not represent a continuous time-series or interpolation.</p></div>
   <div className="card"><div className="card-head"><div><div className="kicker">AGGREGATED CHECK</div><h3>Overall held-out error</h3></div><div className="tiny-badge">NOT CROSS-EVENT TRANSFER</div></div><div className="table-scroll"><table className="pro-table"><thead><tr><th>Model</th><th>Test laps available</th><th>Folds</th><th>Pooled MAE</th><th>Pooled RMSE</th></tr></thead><tbody>{allPooled.map(x=><tr key={x.model}><td><strong>{names[x.model]}</strong></td><td>{x.laps??'Unavailable'}</td><td>{x.folds??'—'}</td><td>{number(x.mae)} s</td><td>{number(x.rmse)} s</td></tr>)}</tbody></table></div><h3 style={{marginTop:20}}>Fair comparison against the median baseline</h3><div className="table-scroll"><table className="pro-table"><thead><tr><th>Compared model</th><th>Shared test laps</th><th>Median MAE on shared folds</th><th>Model MAE</th><th>Change vs median</th></tr></thead><tbody>{paired.map(x=><tr key={x.model}><td>{names[x.model]}</td><td>{x.laps}</td><td>{number(x.baseline??undefined)} s</td><td>{number(x.modelMae??undefined)} s</td><td style={{color:x.improvement!=null&&x.improvement>0?"#34d399":"#f97373"}}>{x.improvement==null?"Unavailable":`${x.improvement>0?"+":""}${number(x.improvement,1)}% ${x.improvement>0?"lower error":"error reduction"}`}</td></tr>)}</tbody></table></div><p className="benchmark-subtle">Comparisons across models are only fair on identical evaluation folds. Piecewise BIC may be unavailable on short stints, so its pooled aggregate covers fewer laps. RMSE uses pooled squared errors, not the average of fold RMSEs.</p></div>
   </>}
   {slopeData.length>0&&<div className="card benchmark-chart"><div className="card-head"><div><div className="kicker">DESCRIPTIVE MODEL FIT</div><h3>Estimated lap-time slope by event</h3></div><div className="tiny-badge">SECONDS / LAP</div></div><ResponsiveContainer width="100%" height={265}><BarChart data={slopeData}><CartesianGrid stroke="#202832" strokeDasharray="3 3"/><XAxis dataKey="circuit" tick={{fill:'#aab3bf',fontSize:11}}/><YAxis tick={{fill:'#aab3bf',fontSize:10}}/><ReferenceLine y={0} stroke="#cbd5e1"/><Tooltip formatter={(v:any)=>`${number(Number(v),4)} s/lap`} contentStyle={{background:'#0e141c',border:'1px solid #27313e'}}/><Bar dataKey="slope" name="Fitted slope" fill="#60a5fa" maxBarSize={90}/></BarChart></ResponsiveContainer><div className="table-scroll"><table className="pro-table"><thead><tr><th>Event</th><th>Fitted slope</th><th>95% credible interval</th></tr></thead><tbody>{computed.map(e=><tr key={e.circuit}><td>{e.circuit}</td><td>{number(e.slope,4)} s/lap</td><td>{e.ci95?`${number(e.ci95[0],4)} to ${number(e.ci95[1],4)}`:'Unavailable'}</td></tr>)}</tbody></table></div><p className="benchmark-subtle">These are observational lap-time associations, not measured physical tyre wear. Credible intervals are displayed in the table, not represented by the bar lengths.</p></div>}
   {report.events.some(e=>e.status!=='computed')&&<div className="card"><h3>Unavailable events</h3><p>{report.events.filter(e=>e.status!=='computed').map(e=>`${e.circuit}: ${e.reason??'not reported'}`).join(' · ')}</p></div>}
   <div className="card"><div className="kicker">RESEARCH LIMITATIONS</div><p className="benchmark-subtle">{report.limitations??'No limitations statement supplied.'}</p><p className="benchmark-subtle">Confidence/credible intervals for fitted slopes must not be interpreted as calibrated predictive intervals for lap times. This page does not prove tyre degradation causality or cross-circuit generalization.</p></div>
  </>}
  <SteeringResearchPanel/>
 </section>;
}
