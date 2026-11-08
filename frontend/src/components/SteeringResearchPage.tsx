import { useEffect, useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Download, Upload, RefreshCw } from 'lucide-react';

type Metrics = { status: string; n: number; mae_deg: number; rmse_deg: number; p95_abs_error_deg: number; bias_deg: number };
type EpochPoint = { epoch: number; train_smooth_l1: number; validation_mae_deg?: number; validation_rmse_deg?: number };
type Model = { validation: Metrics; by_validation_video?: Record<string, Metrics>; training_history?: EpochPoint[]; best_epoch?: number };
type Report = {
 experiment: string; status: string; seed: number; epochs?: number; epochs_requested?: number; pretrained_imagenet_backbone: boolean;
 training_device: string; label_origin: string; reference: string; split: string; group_mapping?: string | null;
 train_sequences: number; validation_sequences: number; test_sequences?: number; reserved_test_sequences?: number; median_angle_baseline?: { validation?: Metrics }; 
 train_video_ids: string[]; validation_video_ids: string[]; test_video_ids?: string[]; reserved_test_video_ids?: string[]; validation_only?: boolean;
 models: Record<string,Model>; selected_model: {mode: string; validation_mae_deg: number; final_test?: Partial<Metrics> & {status?: string}; by_final_test_video?: Record<string,Metrics>; selection_policy: string};
 limitations: string;
};
const labels: Record<string,string> = { cnn: 'CNN', cnn_gru: 'CNN + GRU', cnn_gru_flow: 'CNN + GRU + Flow' };
const format = (n:number, d=2) => Number.isFinite(n) ? n.toFixed(d) : '—';
function check(input:unknown): Report {
 if (!input || typeof input!=='object') throw new Error('Expected an evaluation JSON object.');
 const r=input as Report;
 if(r.experiment!=='steering_cv_temporal_ablation'||!['evaluated','exploratory_validation_only','evaluated_source_independence_unverified'].includes(r.status)||!r.models||!r.selected_model) throw new Error('Not a supported steering experiment report.');
 const modes=Object.keys(r.models).filter(m=>m in labels);
 if(modes.length===0 || !modes.includes(r.selected_model.mode)) throw new Error('No valid selected model found.');
 for(const m of modes) {
  const v=r.models[m]?.validation;
  if(!v||!Number.isFinite(v.mae_deg)||!Number.isFinite(v.rmse_deg)||v.n<=0||v.mae_deg<0) throw new Error(`Invalid ${m} validation metrics.`);
 }
 if(r.selected_model.final_test?.status==='computed' && (!Number.isFinite(r.selected_model.final_test.mae_deg)||!r.selected_model.final_test.n||r.selected_model.final_test.n<=0)) throw new Error('Invalid final test metrics.');
 return r;
}
export default function SteeringResearchPage(){
 const [report,setReport]=useState<Report|null>(null);
 const [error,setError]=useState('');
 const [source,setSource]=useState('');
 const [metric,setMetric]=useState<'mae_deg'|'rmse_deg'>('mae_deg');
 const [loading,setLoading]=useState(false);
 async function reload(){setLoading(true);setError('');try{const response=await fetch('/steering_ablation_gpu.json',{cache:'no-store'});if(!response.ok)throw new Error('Saved experiment JSON not found.');setReport(check(await response.json()));setSource('Bundled evaluation snapshot · results/steering_ablation_gpu.json');}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setLoading(false);}}
 useEffect(()=>{void reload()},[]);
 async function upload(file:File|undefined){if(!file)return;try{if(file.size>3_000_000)throw new Error('File exceeds 3 MB.');const value=check(JSON.parse(await file.text()));setReport(value);setSource(`Local import: ${file.name}`);setError('');}catch(e){setError(e instanceof Error?e.message:String(e));}}
 const rows=useMemo(()=>report?Object.entries(report.models).filter(([key])=>key in labels).map(([key,m])=>({name:labels[key],key,mae_deg:m.validation.mae_deg,rmse_deg:m.validation.rmse_deg,n:m.validation.n})):[],[report]);
 const byRecording=useMemo(()=>report?Object.entries(report.selected_model.by_final_test_video||{}).map(([name,v])=>({name,mae_deg:v.mae_deg,rmse_deg:v.rmse_deg,n:v.n})).sort((a,b)=>b.mae_deg-a.mae_deg):[],[report]);
 const cnn=report?.models.cnn?.validation.mae_deg;
 const selectedMode=report?.selected_model.mode??'';
 const selectedLabel=labels[selectedMode]??selectedMode;
 const selectedMAE=report?.models[selectedMode]?.validation.mae_deg??NaN;
 const reduction=cnn!==undefined&&Number.isFinite(selectedMAE)&&cnn>0?100*(cnn-selectedMAE)/cnn:NaN;
 const test=report?.selected_model.final_test;
 const hasTest=test?.status==='computed' && Number.isFinite(test.mae_deg);
 const convergence=report?.models[selectedMode]?.training_history||[];
 const measuredConvergence=convergence.some(p=>Number.isFinite(p.validation_mae_deg));
 const epochCount=report?.epochs_requested??report?.epochs??0;
 const download=()=>{if(!report)return;const a=document.createElement('a');const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));a.href=url;a.download='steering_research_evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
 return <section className="page steering-research-page">
  <div className="page-heading"><div><div className="kicker">STEERING RESEARCH · SAVED EXPERIMENTS</div><h2>Steering AI Research</h2><p>Measured steering-wheel rotation prediction errors from manually annotated F1 onboard images. These charts read a saved evaluation file; <strong>no retraining is needed</strong>.</p></div><div className="session-pill">PRELIMINARY · NOT OFFICIAL TELEMETRY</div></div>
  <div className="benchmark-toolbar"><button className="run-btn" disabled={loading} onClick={()=>void reload()}><RefreshCw size={15}/>{loading?'Loading…':'Reload saved experiment'}</button><label className="benchmark-upload"><Upload size={15}/> Import newer results JSON<input type="file" accept=".json,application/json" onChange={e=>void upload(e.target.files?.[0])}/></label><button className="benchmark-upload" onClick={download} disabled={!report}><Download size={15}/> Download evidence JSON</button><label className="benchmark-metric">Chart metric <select value={metric} onChange={e=>setMetric(e.target.value as 'mae_deg'|'rmse_deg')}><option value="mae_deg">MAE (degrees)</option><option value="rmse_deg">RMSE (degrees)</option></select></label></div>
  {source&&<p className="benchmark-subtle">Source: {source} · A saved report, not an active training run.</p>}
  {error&&<div className="error-box">{error}</div>}
  {!report&&<div className="card">No saved steering evaluation loaded. Import the JSON produced by your completed training run.</div>}
  {report&&<>
   <div className="steering-warning"><strong>Exploratory, not deployment-ready.</strong> {report.group_mapping?'This run used source-group proposals; review status and independent footage provenance must be checked.':'Recording IDs come from filenames and may represent overlapping footage.'} Annotations describe apparent steering-wheel rotation, not measured steering-system angle. The backbone {report.pretrained_imagenet_backbone?'used ImageNet weights':'was not pretrained'}, and this experiment ran for {epochCount} requested epoch{epochCount===1?'':'s'}. {report.validation_only?'The final test was deliberately NOT run.':''}</div>
   <div className="stat-grid steering-stats"><div className="stat"><span>BEST VALIDATION MAE</span><strong>{format(selectedMAE)}°</strong><small>{selectedLabel}</small></div><div className="stat"><span>SELECTED MODEL TEST MAE</span><strong>{hasTest?`${format(test?.mae_deg??NaN)}°`:'Not evaluated'}</strong><small>{hasTest?`${test?.n} test sequences`:'Provisional · validation only'}</small></div><div className="stat"><span>VALIDATION ERROR REDUCTION</span><strong>{Number.isFinite(reduction)?`${format(reduction,1)}%`:'—'}</strong><small>{Number.isFinite(reduction)?'Selected vs CNN; exploratory':'CNN baseline not in this run'}</small></div><div className="stat"><span>TEST ERROR P95</span><strong>{hasTest?`${format(test?.p95_abs_error_deg??NaN)}°`:'—'}</strong><small>{hasTest?'Large errors remain':'Test reserved'}</small></div></div>
   <div className="card steering-panel"><div className="card-head"><div><div className="kicker">ARCHITECTURE ABLATION</div><h3>Validation error by architecture</h3></div><div className="tiny-badge">LOWER IS BETTER · {metric==='mae_deg'?'MAE':'RMSE'}</div></div><ResponsiveContainer width="100%" height={320}><BarChart data={rows} margin={{top:12,right:20,bottom:6,left:4}}><CartesianGrid stroke="#253344" strokeDasharray="3 3"/><XAxis dataKey="name" tick={{fill:'#b9c6d6',fontSize:12}}/><YAxis tick={{fill:'#9daabc',fontSize:12}} unit="°"/><Tooltip formatter={(value:any)=>`${format(Number(value))}°`} contentStyle={{background:'#101824',color:'#e5edf6',border:'1px solid #354355'}}/><Bar dataKey={metric} name={metric==='mae_deg'?'Validation MAE':'Validation RMSE'} fill="#e10600" maxBarSize={100}/></BarChart></ResponsiveContainer><p className="steering-note">Evaluated on {report.validation_sequences} validation sequences. This single-run comparison does not establish which component caused the improvement or that the model generalizes to unseen source footage.</p></div>
   <div className="card steering-panel"><div className="card-head"><div><div className="kicker">EXPERIMENT EVIDENCE</div><h3>Model comparison and evaluation protocol</h3></div></div><div className="table-scroll"><table className="pro-table"><thead><tr><th>Architecture</th><th>Val. sequences</th><th>MAE</th><th>RMSE</th><th>95th-percentile error</th></tr></thead><tbody>{Object.entries(report.models).filter(([k])=>k in labels).map(([k,m])=><tr key={k}><td><strong>{labels[k]}</strong></td><td>{m.validation.n}</td><td>{format(m.validation.mae_deg)}°</td><td>{format(m.validation.rmse_deg)}°</td><td>{format(m.validation.p95_abs_error_deg)}°</td></tr>)}</tbody></table></div><p className="steering-note">Train / validation / reserved test: {report.train_sequences} / {report.validation_sequences} / {report.test_sequences??report.reserved_test_sequences??'—'} candidate sequences. Seed {report.seed}; device {report.training_device}; ImageNet pretrained: {report.pretrained_imagenet_backbone?'yes':'no'}. Reported split: {report.split}. <strong>Check source-recording evidence before claiming independence.</strong></p><div className="steering-test-summary"><strong>{hasTest?'Selected model on held-out test':'Held-out test deliberately reserved'}</strong><span>{hasTest?`MAE ${format(test?.mae_deg??NaN)}° · RMSE ${format(test?.rmse_deg??NaN)}° · signed bias ${format(test?.bias_deg??NaN)}° · n = ${test?.n}`:'No final-test scores were generated because the source-group mapping is provisional.'}</span></div>{report.median_angle_baseline?.validation?.mae_deg!==undefined&&<p className="steering-note">Training-median constant-angle baseline: validation MAE {format(report.median_angle_baseline.validation.mae_deg)}°. Compare learned models against this baseline, not only each other.</p>}</div>
   {convergence.length>0&&<div className="card steering-panel"><div className="card-head"><div><div className="kicker">PER-EPOCH CONVERGENCE · {selectedLabel}</div><h3>Training loss and validation accuracy</h3></div><div className="tiny-badge">{convergence.length} EPOCH{convergence.length===1?'':'S'} MEASURED</div></div>
    <div className="steering-convergence-grid">
     <div><h4>Training SmoothL1 loss</h4><ResponsiveContainer width="100%" height={250}><LineChart data={convergence} margin={{top:12,right:16,bottom:8,left:0}}><CartesianGrid stroke="#253344" strokeDasharray="3 3"/><XAxis dataKey="epoch" tick={{fill:'#b9c6d6'}}/><YAxis tick={{fill:'#b9c6d6'}}/><Tooltip contentStyle={{background:'#101824',color:'#e5edf6',border:'1px solid #354355'}}/><Line dataKey="train_smooth_l1" stroke="#e77f78" strokeWidth={2.5} dot={false} name="Train SmoothL1"/></LineChart></ResponsiveContainer></div>
     <div><h4>Validation MAE (degrees)</h4>{measuredConvergence?<ResponsiveContainer width="100%" height={250}><LineChart data={convergence} margin={{top:12,right:16,bottom:8,left:0}}><CartesianGrid stroke="#253344" strokeDasharray="3 3"/><XAxis dataKey="epoch" tick={{fill:'#b9c6d6'}}/><YAxis tick={{fill:'#b9c6d6'}} unit="°"/><Tooltip formatter={(value:any)=>`${format(Number(value))}°`} contentStyle={{background:'#101824',color:'#e5edf6',border:'1px solid #354355'}}/><Line dataKey="validation_mae_deg" stroke="#6ab6ff" strokeWidth={2.5} dot={false} name="Val MAE"/></LineChart></ResponsiveContainer>:<p className="steering-note">This earlier run did not measure validation error at every epoch.</p>}</div>
    </div><p className="steering-note">Epoch curves show optimisation behavior on these provisional groups, not certified real-world generalization. {report.models[selectedMode]?.best_epoch?`Best validation checkpoint: epoch ${report.models[selectedMode]?.best_epoch}.`:''}</p>
   </div>}
   {hasTest&&<div className="card steering-panel"><div className="card-head"><div><div className="kicker">GENERALIZATION DIAGNOSTICS</div><h3>Selected model error across held-out recording groups</h3></div></div><div className="steering-scroll-chart"><ResponsiveContainer width="100%" height={Math.max(370,byRecording.length*35)}><BarChart data={byRecording} layout="vertical" margin={{top:10,right:24,bottom:4,left:30}}><CartesianGrid stroke="#243245" strokeDasharray="3 3"/><XAxis type="number" tick={{fill:'#aebbd0',fontSize:12}} unit="°"/><YAxis type="category" dataKey="name" width={205} tick={{fill:'#b6c3d4',fontSize:11}}/><Tooltip formatter={(value:any)=>`${format(Number(value))}°`} contentStyle={{background:'#101824',color:'#e5edf6',border:'1px solid #354355'}}/><Bar dataKey="mae_deg" fill="#ef7972" name="MAE" maxBarSize={21}/></BarChart></ResponsiveContainer></div><p className="steering-note">High variation across recordings. Some groups contain few sequences; per-group metrics should not be treated as equally precise.</p></div>}
   <div className="card steering-panel"><div className="kicker">MEASUREMENT & REPRODUCIBILITY NOTES</div><h3>What the experiment does—and does not—establish</h3><p>Reference: {report.reference}</p><p>Selection policy: {report.selected_model.selection_policy}</p><p>{report.limitations}</p><p>Errors are relative to manual image annotations. A lower MAE here does not establish reliable inference for real onboard video, vehicle balance, or official wheel-angle telemetry. Keep the original JSON and checkpoints as immutable experiment artifacts.</p></div>
  </>}
 </section>;
}
