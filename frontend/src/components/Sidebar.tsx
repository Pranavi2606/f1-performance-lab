import { BarChart3, BrainCircuit, Gauge, GitBranch, Radio, Trophy, Settings2, ChartNoAxesCombined, SplitSquareVertical, ScanEye } from "lucide-react";

const pages = [
  ["results","Race Results",Trophy],["stints","Stint Analysis",Gauge],
  ["insights","Strategy Insights",BarChart3],["simulator","Energy Management",GitBranch],
  ["ml","Performance Discovery",BrainCircuit],["telemetry","Telemetry",Radio],
  ["benchmark","Research Results",ChartNoAxesCombined],["steering","Steering AI Research",ScanEye],["debrief","Driver Debrief",SplitSquareVertical]
] as const;

export default function Sidebar({active,setActive,year,setYear,races,round,setRound}:any) {
  return <aside className="sidebar">
    <div className="brand"><div className="brand-mark"><span>F1</span></div><div><div className="brand-title">PERFORMANCE LAB</div><div className="brand-sub">RACE DECISION SYSTEM</div></div></div>
    <div className="session-box">
      <div className="section-label">RACE CONTROL</div>
      <label>SEASON<select value={year} onChange={e=>setYear(Number(e.target.value))}>{[2026,2025,2024,2023,2022].map(y=><option key={y}>{y}</option>)}</select></label>
      <label>GRAND PRIX<select value={races.length ? round : ""} disabled={!races.length} onChange={e=>setRound(Number(e.target.value))}>{!races.length&&<option value="">No races loaded — check API</option>}{races.map((r:any)=><option key={r.round} value={r.round}>{String(r.round).padStart(2,"0")} · {r.raceName.replace(" Grand Prix","")}</option>)}</select></label>
    </div>
    <nav className="nav">{pages.map(([key,label,Icon])=><button key={key} onClick={()=>setActive(key)} className={`nav-item ${active===key?"active":""}`}><Icon size={17}/><span>{label}</span><span className="nav-arrow">›</span></button>)}</nav>
    <div className="sidebar-bottom"><div className="live-dot"></div><div><strong>PUBLIC DATA MODE</strong><small>API status shown above</small></div></div>
    <div className="side-meta"><Settings2 size={13}/> PUBLIC DATA MODE</div>
  </aside>
}
