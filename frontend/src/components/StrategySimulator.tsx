import { useState } from "react";
import { BrainCircuit, Play, AlertCircle } from "lucide-react";
import { getStrategyScenarios } from "../services/api";

export default function StrategySimulator() {
  const [raceLaps,setRaceLaps]=useState(57),[basePace,setBasePace]=useState(92),[pitLoss,setPitLoss]=useState(22);
  const [result,setResult]=useState<any>(),[loading,setLoading]=useState(false),[error,setError]=useState("");
  async function run(){setLoading(true);setError("");try{setResult(await getStrategyScenarios(raceLaps,basePace,pitLoss));}catch(e:any){setError(e?.response?.data?.detail??"Could not run scenario comparison.");}finally{setLoading(false);}}
  return <div className="stack">
    <div className="panel"><div className="panel-title-row"><div><div className="eyebrow">DECISION SUPPORT · SCENARIO COMPARISON</div><h2>One-stop vs two-stop strategy search</h2><p className="muted">Ranks candidate pit windows and compound sequences under explicit assumptions.</p></div><BrainCircuit size={20}/></div>
      <div className="sim-grid">
        <label><span>Race laps</span><input type="number" min="20" max="100" value={raceLaps} onChange={e=>setRaceLaps(Number(e.target.value))}/></label>
        <label><span>Baseline pace (s)</span><input type="number" min="50" max="180" step=".1" value={basePace} onChange={e=>setBasePace(Number(e.target.value))}/></label>
        <label><span>Pit loss (s)</span><input type="number" min="0" max="60" step=".5" value={pitLoss} onChange={e=>setPitLoss(Number(e.target.value))}/></label>
      </div>
      <button className="primary-button" onClick={run} disabled={loading}><Play size={16}/>{loading?"Comparing scenarios…":"Compare strategy scenarios"}</button>
      {error&&<div className="error-box">{error}</div>}
    </div>
    {result&&<>
      <div className="panel"><div className="eyebrow">TOP MODELLED SCENARIOS</div><h3>Lowest expected total race time</h3>
        <div className="table-wrap"><table><thead><tr><th>Rank</th><th>Pit laps</th><th>Tyre sequence</th><th>Mean time</th><th>P10–P90</th></tr></thead><tbody>{result.best_scenarios.map((x:any,i:number)=><tr key={`${x.stops.join("-")}-${i}`}><td>{i+1}</td><td>{x.stops.join(", ")}</td><td>{x.compounds.join(" → ")}</td><td>{x.mean_s.toFixed(2)} s</td><td>{x.p10_s.toFixed(2)}–{x.p90_s.toFixed(2)} s</td></tr>)}</tbody></table></div>
        <p className="muted">{result.model_note}</p><div className="source-note">Assumptions: {JSON.stringify(result.assumptions)}. The ranking is illustrative, not a live race recommendation.</div>
      </div>
    </>}
    <div className="panel simulator-note"><AlertCircle size={16}/><span><strong>Model boundary:</strong> compound pace offsets and degradation rates are configurable assumptions, not live Pirelli or team data. Safety cars, traffic, weather, warm-up, track evolution and undercut/overcut effects are not yet modelled.</span></div>
  </div>;
}
