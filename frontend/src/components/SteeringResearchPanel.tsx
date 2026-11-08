import {useEffect,useState} from 'react';
import {BarChart, Bar, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis} from 'recharts';

type Metric={mae_deg:number;rmse_deg:number;n:number;p95_abs_error_deg?:number;bias_deg?:number};
type Eval={validation:Metric};
type SteeringReport={experiment:string;epochs:number;pretrained_imagenet_backbone:boolean;training_device:string;train_sequences:number;validation_sequences:number;test_sequences:number;models:Record<string,Eval>;selected_model:{mode:string;final_test:Metric};limitations?:string};
const labels:Record<string,string>={cnn:'CNN',cnn_gru:'CNN + GRU',cnn_gru_flow:'CNN + GRU + Optical Flow'};
function validate(v:unknown):SteeringReport{
 if(!v||typeof v!=='object')throw new Error('Expected a steering model report.');
 const x=v as SteeringReport;
 if(x.experiment!=='steering_cv_temporal_ablation'||!x.models||!x.selected_model||!x.selected_model.final_test)throw new Error('Not a steering_cv_temporal_ablation report.');
 for(const [,entry] of Object.entries(x.models))if(!Number.isFinite(entry.validation?.mae_deg)||!Number.isFinite(entry.validation?.rmse_deg))throw new Error('Invalid model metrics.');
 return x;
}
export default function SteeringResearchPanel(){
 const [report,setReport]=useState<SteeringReport|null>(null);
 const [source,setSource]=useState('');const [error,setError]=useState('');
 async function load(file?:File){if(!file)return;try{if(file.size>5_000_000)throw new Error('Report must be under 5 MB.');setReport(validate(JSON.parse(await file.text())));setSource(file.name);setError('');}catch(e){setError(e instanceof Error?e.message:String(e));}}
 useEffect(()=>{let active=true;fetch('/research/steering_ablation_gpu.json').then(r=>{if(!r.ok)throw new Error('No published research report');return r.json()}).then(v=>{if(active){setReport(validate(v));setSource('Published research report')}}).catch(()=>{});return()=>{active=false}},[]);
 const data=report?Object.entries(report.models).map(([key,value])=>({model:labels[key]??key,mae:value.validation.mae_deg,rmse:value.validation.rmse_deg,n:value.validation.n})):[];
 const selected=report?.selected_model;
 return <div className="card" style={{marginTop:22}}>
 <div className="card-head"><div><div className="kicker">COMPUTER VISION · EXPERIMENTAL</div><h3>Steering AI research</h3></div><span className="tiny-badge">ANNOTATED ONBOARD IMAGES</span></div>
 <p className="benchmark-subtle">Import your completed <code>steering_ablation_gpu.json</code>. This renders saved research metrics—no model retraining or video upload required. Angles are manually annotated visible steering-wheel rotations, not official telemetry.</p>
 <label className="benchmark-upload" style={{display:'inline-flex',marginBottom:14}}>IMPORT STEERING RESULTS JSON<input type="file" accept=".json,application/json" onChange={e=>void load(e.target.files?.[0])}/></label>
 {error&&<div className="error-box">{error}</div>}
 {!report&&<p className="benchmark-subtle">No steering experiment imported yet. Keep JSON and checkpoints in <code>results/</code>; choose the saved JSON above to display its metrics.</p>}
 {report&&<>
 <p className="benchmark-subtle">Source: {source} · {report.epochs} training epoch(s) · pretrained backbone: {report.pretrained_imagenet_backbone?'yes':'no'} · device: {report.training_device}</p>
 <div className="stat-grid"><div className="stat"><span>BEST VALIDATION MODEL</span><strong style={{fontSize:20}}>{labels[selected!.mode]??selected!.mode}</strong><small>Chosen using validation MAE</small></div><div className="stat"><span>HELD-OUT TEST MAE</span><strong>{selected!.final_test.mae_deg.toFixed(2)}°</strong><small>Preliminary; source groups not verified</small></div><div className="stat"><span>TEST RMSE</span><strong>{selected!.final_test.rmse_deg.toFixed(2)}°</strong><small>{selected!.final_test.n} test sequences</small></div><div className="stat"><span>TEST P95 ABS. ERROR</span><strong>{selected!.final_test.p95_abs_error_deg?.toFixed(2)??'—'}°</strong><small>90/95th tails matter for steering</small></div></div>
 <div style={{width:'100%',height:310,marginTop:20}}><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{top:12,right:22,bottom:16,left:14}}><CartesianGrid stroke="#202832" strokeDasharray="3 3"/><XAxis dataKey="model" tick={{fill:'#bdc7d5',fontSize:11}}/><YAxis unit="°" tick={{fill:'#bdc7d5'}}/><Tooltip contentStyle={{background:'#0e141c',border:'1px solid #27313e',color:'#fff'}} formatter={(n:any)=>`${Number(n).toFixed(2)}°`}/><Bar name="Validation MAE" dataKey="mae" fill="#f35555" maxBarSize={100}/></BarChart></ResponsiveContainer></div>
 <div className="table-scroll"><table className="pro-table"><thead><tr><th>Architecture</th><th>Validation samples</th><th>MAE</th><th>RMSE</th></tr></thead><tbody>{data.map(d=><tr key={d.model}><td>{d.model}</td><td>{d.n}</td><td>{d.mae.toFixed(2)}°</td><td>{d.rmse.toFixed(2)}°</td></tr>)}</tbody></table></div>
 <div style={{marginTop:15,padding:14,border:'1px solid #435063',borderRadius:10}}><strong>Research limitations</strong><p className="benchmark-subtle" style={{marginBottom:0}}>Exploratory results. Filename-derived recording groups have not been independently verified; overlapping source footage may cause leakage. {report.epochs===1?'Only one epoch was trained; convergence is unmeasured. ':''}{!report.pretrained_imagenet_backbone?'The encoder did not use pretrained weights. ':''}Errors are relative to human annotations, not instrumented steering-angle telemetry. {report.limitations??''}</p></div>
 </>}
 </div>;
}
