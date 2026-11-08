import { Trophy, ArrowUpRight, ArrowDownRight } from "lucide-react";
export default function ResultsPage({overview}:any){
  const results=overview.results;
  return <div className="page">
    <div className="page-heading"><div><div className="kicker">01 / DATA INGESTION</div><h2>Race Results</h2><p>Official classification and race outcome data for the selected Grand Prix.</p></div><div className="session-pill"><span></span> {overview.openf1Session ? `OPENF1 SESSION ${overview.openf1Session.session_key}` : "CLASSIFICATION DATA"}</div></div>
    <div className="summary-strip">
      <div><span>WINNER</span><strong>{results[0]?.driver??"—"}</strong><small>{results[0]?.constructor??""}</small></div>
      <div><span>FASTEST FINISHERS</span><strong>{results.filter((r:any)=>r.position&&r.position<=3).length}</strong><small>podium positions</small></div>
      <div><span>CLASSIFIED</span><strong>{results.filter((r:any)=>r.position).length}/{results.length}</strong><small>official classification</small></div>
      <div><span>POINTS SCORED</span><strong>{results.reduce((a:any,r:any)=>a+r.points,0).toFixed(0)}</strong><small>total race points</small></div>
    </div>
    <div className="card">
      <div className="card-head"><div><div className="kicker">CLASSIFICATION</div><h3>Race finishing order</h3></div><span className="tiny-badge">JOLPICA</span></div>
      <div className="table-scroll"><table className="pro-table"><thead><tr><th>POS</th><th>DRIVER</th><th>CONSTRUCTOR</th><th>GRID</th><th>GAP / STATUS</th><th>PTS</th></tr></thead><tbody>{results.map((r:any,i:number)=><tr key={r.driverId}><td><span className={`pos-badge p${Math.min(i+1,4)}`}>{r.position??"—"}</span></td><td><strong>{r.driver}</strong><small className="driver-id">#{r.number}</small></td><td>{r.constructor}</td><td>{r.grid??"—"}</td><td><span className={r.status==="Finished"?"finish":"retire"}>{r.status==="Finished" ? (r.position===1?"WINNER":"CLASSIFIED") : r.status}</span></td><td><strong>{r.points.toFixed(1)}</strong></td></tr>)}</tbody></table></div>
    </div>
  </div>
}
