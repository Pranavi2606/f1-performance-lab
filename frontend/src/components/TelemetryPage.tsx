import {useEffect,useState} from 'react';
import {Activity,Loader2} from 'lucide-react';
import {CartesianGrid,Line,LineChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
import {getDriverLaps,getTelemetry,apiErrorMessage} from '../services/api';

export default function TelemetryPage({year,round,drivers}:any){
 const [driver,setDriver]=useState<number>(drivers[0]?.driver_number??1);
 const [laps,setLaps]=useState<Array<{lap_number:number;duration_s:number;compound:string}>>([]);
 const [lap,setLap]=useState<number|undefined>(undefined);
 const [data,setData]=useState<any>();
 const [busy,setBusy]=useState(false); const [error,setError]=useState('');
 useEffect(()=>{if(drivers.length&&!drivers.some((d:any)=>d.driver_number===driver))setDriver(drivers[0].driver_number)},[drivers]);
 useEffect(()=>{let valid=true;setLaps([]);setData(null);setLap(undefined);if(year<2023)return;
  getDriverLaps(year,round,driver).then(r=>{if(valid){setLaps(r.laps);if(r.laps.length){const best=r.laps.reduce((a,b)=>a.duration_s<=b.duration_s?a:b);setLap(best.lap_number);}}}).catch(e=>{if(valid)setError(apiErrorMessage(e,'Lap list unavailable'))});
  return()=>{valid=false};},[year,round,driver]);
 useEffect(()=>{if(lap===undefined||year<2023)return;let valid=true;setBusy(true);setError('');
  getTelemetry(year,round,driver,lap).then(r=>{if(valid)setData(r)}).catch(e=>{if(valid){setData(null);setError(apiErrorMessage(e,'Telemetry unavailable'))}}).finally(()=>{if(valid)setBusy(false)});
  return()=>{valid=false};},[year,round,driver,lap]);
 const chart=data?.points??[];
 if(year<2023)return <div className="page"><h2>Telemetry</h2><p>OpenF1 car telemetry for this project starts with the 2023 season. Try a later race.</p></div>;
 return <div className="page"><div className="page-heading"><div><div className="kicker">06 / LAP TELEMETRY</div><h2>Single-driver lap telemetry</h2><p>One lap at a time. Compare drivers in Driver Debrief instead.</p></div></div>
 <div className="toolbar"><label>DRIVER<select value={driver} onChange={e=>setDriver(Number(e.target.value))}>{drivers.map((d:any)=><option value={d.driver_number} key={d.driver_number}>{d.name_acronym} · {d.full_name}</option>)}</select></label><label>LAP<select value={lap??''} onChange={e=>setLap(Number(e.target.value))}>{laps.map(l=><option value={l.lap_number} key={l.lap_number}>Lap {l.lap_number} · {l.duration_s.toFixed(3)} s · {l.compound}</option>)}</select></label></div>
 {error&&<div className="error-box">{error}</div>}
 {busy?<div className="loading"><Loader2 className="spin"/> Loading selected lap telemetry…</div>:data?<>
 <div className="stat-grid four"><div className="stat"><span>SELECTED LAP</span><strong>{data.selected_lap}</strong><small>{data.lap_time_s?.toFixed(3)} s</small></div><div className="stat"><span>AVG SPEED</span><strong>{data.avg_speed} km/h</strong></div><div className="stat"><span>MAX SPEED</span><strong>{data.max_speed} km/h</strong></div><div className="stat"><span>BRAKE EVENTS</span><strong>{data.brake_events}</strong></div></div>
 {([['Speed','speed','km/h'],['Throttle','throttle','%'],['Brake (binary)','brake','%'],['RPM','rpm','rpm'],['Gear','gear','']] as const).map(([title,key,unit])=><div className="card chart-card" key={key}><div className="card-head"><h3>{title} trace</h3></div><ResponsiveContainer width="100%" height={250}><LineChart data={chart}><CartesianGrid stroke="#202833" strokeDasharray="3 5"/><XAxis dataKey="distance" type="number" domain={['dataMin','dataMax']} tick={{fill:'#9ca3af',fontSize:11}} unit="m"/><YAxis tick={{fill:'#9ca3af',fontSize:11}} unit={unit}/><Tooltip contentStyle={{background:'#10161f',border:'1px solid #29313d'}}/><Line type="linear" dataKey={key} stroke="#e10600" strokeWidth={2} dot={false}/></LineChart></ResponsiveContainer></div>)}
 <p className="muted-note">{data.measurement_note} Distance is speed-integrated within the selected lap and is approximate.</p>
 </>:!error?<div className="empty-state card"><Activity size={26}/>Select a driver and lap to load available telemetry.</div>:null}</div>
}
