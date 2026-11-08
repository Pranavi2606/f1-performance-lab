import {useEffect, useMemo, useState} from 'react';
import {Activity, Loader2, Route, AlertTriangle} from 'lucide-react';
import {LineChart, Line, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis} from 'recharts';
import {apiErrorMessage, getDriverDebrief, getDriverLaps} from '../services/api';
import {TrackMap, SteeringVideoExperiment, DebriefExport} from './DebriefExtras';

function metricChart(data:any[], title:string, primaryKey:string, compareKey:string, unit:string, primaryLabel:string, compareLabel:string, domain?:[number,number]){
  return <div className="card chart-card"><div className="card-head"><div><div className="kicker">TRACE OVERLAY</div><h3>{title}</h3></div></div><ResponsiveContainer width="100%" height={270}><LineChart data={data} margin={{top:8,right:20,bottom:10,left:0}}><CartesianGrid stroke="#202833" strokeDasharray="3 5"/><XAxis dataKey="progress_pct" stroke="#657181" tickFormatter={(v)=>`${Math.round(v)}%`}/><YAxis stroke="#657181" domain={domain ?? ['auto','auto']} unit={unit}/><Tooltip contentStyle={{background:'#0d131b',border:'1px solid #29313d'}} formatter={(v:any, n:any)=>[`${Number(v).toFixed(title==='Gear trace'?0: title==='RPM trace'?0:2)}${unit}`, n===primaryKey?primaryLabel:compareLabel]} labelFormatter={(v)=>`Lap progress ${Number(v).toFixed(1)}%`}/><Legend/>
  <Line type="linear" dataKey={primaryKey} stroke="#f3f5f7" dot={false} strokeWidth={2} name={primaryLabel}/>
  <Line type="linear" dataKey={compareKey} stroke="#e10600" dot={false} strokeWidth={2} name={compareLabel}/>
  </LineChart></ResponsiveContainer></div>
}

export default function DebriefPage({year,round,drivers}:any){
  const primaryDefault = drivers[0]?.driver_number ?? 1;
  const [primary,setPrimary]=useState(primaryDefault);
  const [selectedCompare,setSelectedCompare]=useState<number[]>(drivers.slice(1,3).map((d:any)=>d.driver_number));
  const [detailDriver,setDetailDriver]=useState<number|undefined>(drivers[1]?.driver_number);
  const [data,setData]=useState<any>(null);
  const [primaryLaps,setPrimaryLaps]=useState<Array<{lap_number:number;duration_s:number;compound:string}>>([]);
  const [compareLaps,setCompareLaps]=useState<Array<{lap_number:number;duration_s:number;compound:string}>>([]);
  const [primaryLap,setPrimaryLap]=useState<number|undefined>();
  const [compareLap,setCompareLap]=useState<number|undefined>();
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');

  useEffect(()=>{ if(drivers.length && !drivers.some((d:any)=>d.driver_number===primary)) setPrimary(drivers[0].driver_number); },[drivers]);
  useEffect(()=>{
    const available = drivers.filter((d:any)=>d.driver_number!==primary).map((d:any)=>d.driver_number);
    const next = selectedCompare.filter(x=>available.includes(x));
    const fallback = next.length ? next : available.slice(0, Math.min(2, available.length));
    setSelectedCompare(fallback);
    setDetailDriver(prev => prev && fallback.includes(prev) ? prev : fallback[0]);
  },[drivers,primary]);
  useEffect(()=>{
    if(!selectedCompare.length) return;
    setBusy(true); setError('');
    getDriverDebrief(year, round, primary, selectedCompare, primaryLap, selectedCompare.length===1?compareLap:undefined).then((x:any)=>setData(x)).catch((e:any)=>{setData(null);setError(apiErrorMessage(e,'Unable to load driver debrief'))}).finally(()=>setBusy(false));
  },[year,round,primary,selectedCompare.join(','),primaryLap,compareLap]);

  useEffect(()=>{setPrimaryLap(undefined);getDriverLaps(year,round,primary).then(x=>setPrimaryLaps(x.laps)).catch(()=>setPrimaryLaps([]))},[year,round,primary]);
  useEffect(()=>{setCompareLap(undefined); const driver=selectedCompare[0]; if(!driver)return;getDriverLaps(year,round,driver).then(x=>setCompareLaps(x.laps)).catch(()=>setCompareLaps([]))},[year,round,selectedCompare.join(',')]);
  const comparisons = data?.comparisons ?? [];
  const detail = comparisons.find((x:any)=> detailDriver ? x.compare_driver_number===detailDriver : true) ?? comparisons[0];
  const primaryName = data?.primary_driver?.full_name ?? 'Primary';
  

  const summaryRows = useMemo(()=>comparisons.map((c:any)=>({
    compare_driver: c.compare_driver,
    lap_delta_s: c.lap_delta_s,
    compare_lap_number: c.compare_lap_number,
    compare_lap_time_s: c.compare_lap_time_s,
    strongest_corner: c.corner_comparisons?.slice().sort((a:any,b:any)=>Math.abs(b.compare_minus_primary_time_s)-Math.abs(a.compare_minus_primary_time_s))[0]
  })),[comparisons]);

  function toggleCompare(n:number){
    setSelectedCompare(prev=> prev.includes(n) ? prev.filter(x=>x!==n) : [...prev,n]);
  }

  return <div className="page debrief-page"><div className="page-heading debrief-hero"><div><div className="kicker">08 / VEHICLE PERFORMANCE</div><h2>Driver Performance Debrief</h2><p>Compare real OpenF1 lap traces and discover the braking zones where lap-time differences emerge. Choose a reference driver, then compare one or several drivers.</p></div><div className="model-chip"><span className="pulse"></span> OPENF1 · PUBLIC TELEMETRY</div></div>
  <section className="card debrief-controls" aria-label="Driver comparison configuration">
    <div className="debrief-section-heading"><div><div className="kicker">STEP 01 · SELECT DRIVERS & LAPS</div><h3>Build a comparison</h3></div><span className="debrief-helper">Default: fastest valid race lap for each driver</span></div>
    <div className="debrief-control-grid"><label>Reference driver<select value={primary} onChange={e=>setPrimary(+e.target.value)}>{drivers.map((d:any)=><option key={d.driver_number} value={d.driver_number}>{d.name_acronym} · {d.full_name}</option>)}</select></label>
    <label>Reference lap<select value={primaryLap??''} onChange={e=>setPrimaryLap(e.target.value?Number(e.target.value):undefined)}><option value="">Fastest valid</option>{primaryLaps.map(l=><option key={l.lap_number} value={l.lap_number}>Lap {l.lap_number} · {l.duration_s.toFixed(3)} s · {l.compound}</option>)}</select></label>
    <label>Inspect comparison<select value={detailDriver ?? ''} onChange={e=>setDetailDriver(Number(e.target.value))}>{comparisons.map((x:any)=><option key={x.compare_driver_number} value={x.compare_driver_number}>{x.compare_driver}</option>)}</select></label>
    {selectedCompare.length===1&&<label>Comparison lap<select value={compareLap??''} onChange={e=>setCompareLap(e.target.value?Number(e.target.value):undefined)}><option value="">Fastest valid</option>{compareLaps.map(l=><option key={l.lap_number} value={l.lap_number}>Lap {l.lap_number} · {l.duration_s.toFixed(3)} s · {l.compound}</option>)}</select></label>}
    </div>
    <div className="debrief-driver-picker"><div className="debrief-picker-title"><strong>Compare against</strong><span>Select one for detailed 1:1, or multiple for the leaderboard.</span><span>{selectedCompare.length} selected</span></div><div className="debrief-driver-grid">{drivers.filter((d:any)=>d.driver_number!==primary).map((d:any)=><label className={`debrief-driver-choice ${selectedCompare.includes(d.driver_number)?'selected':''}`} key={d.driver_number}><input type="checkbox" checked={selectedCompare.includes(d.driver_number)} onChange={()=>toggleCompare(d.driver_number)}/><span>{d.name_acronym}</span><span>{d.full_name}</span></label>)}</div></div>
  </section>
  <div className="card" style={{marginBottom:16}}><div className="kicker">CHANNEL AVAILABILITY</div><p>Available: speed, throttle, brake, gear, RPM and approximate delta-time traces. <strong>Unavailable:</strong> official steering angle, slip angle, tyre state and direct oversteer/understeer measurements.</p>{data?.steering_trace && <p className="muted-note"><AlertTriangle size={14} style={{verticalAlign:'text-bottom',marginRight:6}}/>{data.steering_trace.reason}</p>}</div>
  {busy ? <div className="loading"><Loader2 className="spin"/> Loading debrief comparison…</div> : error ? <div className="error-box">{error}</div> : !data ? <div className="empty-state card"><Activity size={30}/><strong>No driver debrief data</strong><span>Select at least one comparison driver to load the analysis.</span></div> : <>
    <div className="stat-grid four"><div className="stat"><span>PRIMARY LAP</span><strong>{data.primary_driver.lap_number}</strong><small>{primaryName} · {data.primary_driver.lap_time_s.toFixed(3)}s</small></div><div className="stat"><span>COMPARISONS</span><strong>{comparisons.length}</strong><small>One-to-many summary enabled</small></div><div className="stat"><span>DETAIL LAP</span><strong>{detail?.compare_lap_number ?? '—'}</strong><small>{detail?.compare_driver ?? 'No detail selection'}</small></div><div className="stat"><span>STEERING TRACE</span><strong>Unavailable</strong><small>CV estimate can be added later</small></div></div>
    <div className="card debrief-leaderboard"><div className="card-head"><div><div className="kicker">STEP 02 · MULTI-DRIVER OVERVIEW</div><h3>Lap comparison leaderboard</h3></div><span className="tiny-badge">COMPARE MINUS REFERENCE</span></div><div className="debrief-leaderboard-list">{summaryRows.map((row:any)=><div className="debrief-leaderboard-row" key={row.compare_driver}><div><strong>{row.compare_driver}</strong><span>Lap {row.compare_lap_number} · {row.compare_lap_time_s.toFixed(3)} s</span></div><div className={row.lap_delta_s<0?'debrief-faster':'debrief-slower'}>{row.lap_delta_s>0?'+':''}{row.lap_delta_s.toFixed(3)} s</div><div className="debrief-helper">{row.strongest_corner?`Largest detected window: Zone ${row.strongest_corner.corner_like_segment}, ${Math.abs(row.strongest_corner.compare_minus_primary_time_s).toFixed(3)} s`:'No corner-like windows available'}</div></div>)}</div><p className="debrief-helper">Negative delta = comparison lap faster. Different laps and conditions may not be directly comparable.</p></div>
    {detail && <>
      <div className="card"><div className="card-head"><div><div className="kicker">DETAILED DEBRIEF</div><h3>{primaryName} vs {detail.compare_driver}</h3></div><span className="tiny-badge">{detail.overall_summary}</span></div><p className="muted-note">Different lap numbers, compound selections and race conditions may make direct driver attribution unreliable. Primary lap {data.primary_driver.lap_number} ({data.primary_driver.lap_time_s.toFixed(3)}s) vs comparison lap {detail.compare_lap_number} ({detail.compare_lap_time_s.toFixed(3)}s). Negative delta-time values on the chart mean the comparison lap is ahead of the primary lap.</p></div>
      <TrackMap year={year} round={round} driver={primary} lap={data.primary_driver.lap_number} cornerComparisons={detail.corner_comparisons}/>
      {metricChart(detail.trace,'Speed trace','primary_speed','compare_speed',' km/h',primaryName,detail.compare_driver)}
      {metricChart(detail.trace,'Throttle trace','primary_throttle','compare_throttle',' %',primaryName,detail.compare_driver,[0,100])}
      {metricChart(detail.trace,'Brake trace','primary_brake','compare_brake',' %',primaryName,detail.compare_driver,[0,100])}
      {metricChart(detail.trace,'RPM trace','primary_rpm','compare_rpm',' rpm',primaryName,detail.compare_driver)}
      {metricChart(detail.trace,'Gear trace','primary_gear','compare_gear','',primaryName,detail.compare_driver)}
      <div className="card chart-card"><div className="card-head"><div><div className="kicker">TIME DELTA</div><h3>Cumulative delta trace</h3></div><Route size={17}/></div><ResponsiveContainer width="100%" height={260}><LineChart data={detail.trace}><CartesianGrid stroke="#202833" strokeDasharray="3 5"/><XAxis dataKey="progress_pct" stroke="#657181" tickFormatter={(v)=>`${Math.round(v)}%`}/><YAxis stroke="#657181" unit=" s"/><Tooltip contentStyle={{background:'#0d131b',border:'1px solid #29313d'}} formatter={(v:any)=>`${Number(v).toFixed(3)} s`} labelFormatter={(v)=>`Lap progress ${Number(v).toFixed(1)}%`}/><Line type="linear" dataKey="delta_time_s" stroke="#93c5fd" dot={false} strokeWidth={2} name="Compare minus primary"/></LineChart></ResponsiveContainer><p className="muted-note">Positive values mean the comparison lap is losing time relative to the primary lap at that part of the lap.</p></div>
      <section className="card debrief-corner-section"><div className="card-head"><div><div className="kicker">STEP 04 · BRAKING-ZONE DEBRIEF</div><h3>Where the time difference changes</h3></div><span className="tiny-badge">INFERRED WINDOWS · NOT OFFICIAL CORNERS</span></div>
      <div className="debrief-corner-grid">{detail.corner_comparisons.map((c:any)=><article className="debrief-corner-card" key={c.corner_like_segment}><div className="debrief-corner-top"><div><strong>Zone {c.corner_like_segment}</strong><span>{c.window_pct[0].toFixed(1)}–{c.window_pct[1].toFixed(1)}% lap progress</span></div><div className={c.compare_minus_primary_time_s<0?'debrief-faster':'debrief-slower'}>{c.compare_minus_primary_time_s>0?'+':''}{c.compare_minus_primary_time_s.toFixed(3)} s</div></div><div className="debrief-corner-metrics"><div><span>Min speed · reference</span><strong>{c.primary.min_speed_kph.toFixed(1)} <small>km/h</small></strong></div><div><span>Min speed · comparison</span><strong>{c.compare.min_speed_kph.toFixed(1)} <small>km/h</small></strong></div><div><span>Exit speed · reference</span><strong>{c.primary.exit_speed_kph.toFixed(1)} <small>km/h</small></strong></div><div><span>Exit speed · comparison</span><strong>{c.compare.exit_speed_kph.toFixed(1)} <small>km/h</small></strong></div></div><details className="debrief-details"><summary>Brake and throttle timing</summary><div>Brake-on: {c.primary.brake_on_pct.toFixed(1)}% vs {c.compare.brake_on_pct.toFixed(1)}% · Brake release: {c.primary.brake_release_pct.toFixed(1)}% vs {c.compare.brake_release_pct.toFixed(1)}% · Throttle pickup: {c.primary.throttle_pickup_pct.toFixed(1)}% vs {c.compare.throttle_pickup_pct.toFixed(1)}%</div></details><p>{c.summary}</p></article>)}</div><p className="debrief-helper">Time deltas use normalized lap-progress alignment. Differences describe observations, not proof of driving technique, balance or oversteer.</p></section>
    </>}
    <SteeringVideoExperiment/>
    <DebriefExport report={data}/>
    <div className="card"><div className="kicker">LIMITATIONS</div><p className="muted-note">{data.limitations}</p></div>
  </>}
  </div>;
}
