import type { Result } from "../types/f1";
export default function RaceResults({ results }: { results: Result[] }) {
  return <div className="panel table-panel">
    <div className="panel-title-row"><div><div className="eyebrow">CLASSIFICATION</div><h2>Race results</h2></div><span className="data-chip">{results.length} drivers</span></div>
    <div className="table-wrap"><table><thead><tr><th>POS</th><th>DRIVER</th><th>TEAM</th><th>GRID</th><th>LAPS</th><th>PTS</th><th>STATUS</th></tr></thead>
    <tbody>{results.map(r => <tr key={r.driverId}><td className="position">{r.position ?? "—"}</td><td><div className="driver-cell"><span className="driver-number">#{r.number ?? "?"}</span><span>{r.driver}</span></div></td><td className="muted">{r.constructor}</td><td>{r.grid ?? "—"}</td><td>{r.laps ?? "—"}</td><td className="points">{r.points.toFixed(1)}</td><td><span className={`status ${r.status === "Finished" || r.status.includes("Lap") ? "ok" : "warning"}`}>{r.status}</span></td></tr>)}</tbody>
    </table></div>
  </div>;
}