import { useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, CheckCircle2, LoaderCircle } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getDegradation } from "../services/api";
import type { DegradationResponse, Driver } from "../types/f1";
import MetricCard from "./MetricCard";

export default function DegradationPanel({ year, round, drivers }: { year:number; round:number; drivers:Driver[] }) {
  const [driverNumber, setDriverNumber] = useState(drivers[0]?.driver_number ?? 1);
  const [stintNumber, setStintNumber] = useState(1);
  const [data, setData] = useState<DegradationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (drivers.length && !drivers.some(d => d.driver_number === driverNumber)) setDriverNumber(drivers[0].driver_number);
  }, [drivers, driverNumber]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError("");
    getDegradation(year, round, driverNumber).then(result => {
      if (!cancelled) { setData(result); setStintNumber(result.analysis.stints[0]?.stintNumber ?? 1); }
    }).catch(err => {
      if (!cancelled) { setData(null); setError(err?.response?.data?.detail ?? "Could not load degradation data."); }
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [year, round, driverNumber]);

  const stint = useMemo(() => data?.analysis.stints.find(s => s.stintNumber === stintNumber), [data, stintNumber]);
  const chartData = useMemo(() => {
    if (!stint) return [];
    const first = stint.points[0];
    const intercept = first ? first.time - stint.degradationRate * first.lap : 0;
    return stint.points.map(p => ({ lap:p.lap, lapTime:p.time, trend:stint.degradationRate*p.lap + intercept }));
  }, [stint]);

  return <div className="stack">
    <div className="panel"><div className="panel-title-row"><div><div className="eyebrow">TYRE MODEL</div><h2>Stint degradation</h2><p className="muted">Degradation is calculated within a tyre stint, not across pit stops.</p></div><Activity size={20}/></div>
      <div className="control-grid">
        <label><span>Driver</span><select value={driverNumber} onChange={e=>setDriverNumber(Number(e.target.value))}>{drivers.map(d=><option key={d.driver_number} value={d.driver_number}>{d.name_acronym} — {d.full_name}</option>)}</select></label>
        <label><span>Stint</span><select value={stintNumber} onChange={e=>setStintNumber(Number(e.target.value))} disabled={!data?.analysis.stints.length}>{data?.analysis.stints.map(s=><option key={s.stintNumber} value={s.stintNumber}>Stint {s.stintNumber} · {s.compound} · L{s.lapStart}–L{s.lapEnd}</option>)}</select></label>
      </div>
    </div>
    {loading && <div className="loading"><LoaderCircle className="spin" size={16}/> Fetching and cleaning public F1 data…</div>}
    {error && <div className="error-box">{error}</div>}
    {stint && !loading && <>
      <div className="metric-grid">
        <MetricCard label="DEGRADATION" value={`${stint.degradationRate >= 0 ? "+" : ""}${stint.degradationRate.toFixed(3)} s/lap`} sub={stint.compound}/>
        <MetricCard label="R²" value={stint.rSquared.toFixed(3)} sub="linear fit quality"/>
        <MetricCard label="CLEAN LAPS" value={String(stint.lapsAnalyzed)} sub={`${stint.lapStart}–${stint.lapEnd}`}/>
      </div>
      <div className="panel chart-panel"><div className="chart-header"><div><div className="eyebrow">PACE TRACE</div><h2>Lap time vs degradation trend</h2></div><div className={`recommendation ${stint.recommendation.toLowerCase()}`}>{stint.recommendation === "HIGH_DEG" ? <AlertTriangle size={15}/> : <CheckCircle2 size={15}/>} {stint.recommendation.replace("_"," ")}</div></div>
        <div className="chart"><ResponsiveContainer width="100%" height={340}><LineChart data={chartData}><CartesianGrid strokeDasharray="3 3" stroke="#252b36"/><XAxis dataKey="lap" stroke="#77808f"/><YAxis stroke="#77808f" domain={["auto","auto"]} tickFormatter={v=>`${Number(v).toFixed(1)}s`}/><Tooltip contentStyle={{background:"#10151e",border:"1px solid #2a3340",borderRadius:8}}/><Line type="monotone" dataKey="lapTime" stroke="#e8edf3" dot={false} strokeWidth={2} name="Lap time"/><Line type="linear" dataKey="trend" stroke="#ef4444" dot={false} strokeDasharray="6 5" strokeWidth={2} name="Trend"/></LineChart></ResponsiveContainer></div>
        <div className="insight">{stint.message}</div>
      </div>
      <div className="panel data-quality"><div className="eyebrow">DATA QUALITY</div><h2>Cleaning audit</h2><p className="muted">{data?.analysis.cleanLapCount} clean laps retained; {data?.analysis.excludedLapCount} excluded before modeling.</p>{data?.analysis.excludedReasons.slice(0,8).map((x,i)=><span className="reason" key={`${x.lap}-${x.reason}-${i}`}>L{x.lap}: {x.reason}</span>)}</div>
    </>}
  </div>;
}