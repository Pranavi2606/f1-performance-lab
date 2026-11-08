import {useEffect,useState} from "react";
import {RefreshCw,Wifi} from "lucide-react";
import Sidebar from "./components/Sidebar";
import ResultsPage from "./components/ResultsPage";
import StintPage from "./components/StintPage";
import InsightsPage from "./components/InsightsPage";
import EnergyPage from "./components/EnergyPage";
import DiscoveryPage from "./components/DiscoveryPage";
import TelemetryPage from "./components/TelemetryPage";
import BenchmarkPage from "./components/BenchmarkPage";
import SteeringResearchPage from "./components/SteeringResearchPage";
import DebriefPage from "./components/DebriefPage";
import {apiErrorMessage,checkBackendHealth,getRaceOverview,getRaces} from "./services/api";
import type {Race} from "./types/f1";

export default function App(){
 const [backendOnline,setBackendOnline]=useState<boolean|null>(null);
 const [retry,setRetry]=useState(0);
 const [active,setActive]=useState("results"),[year,setYear]=useState(2024),[round,setRound]=useState(1),[races,setRaces]=useState<Race[]>([]),[overview,setOverview]=useState<any>(),[loading,setLoading]=useState(false),[error,setError]=useState("");
 useEffect(()=>{checkBackendHealth().then(setBackendOnline)},[retry]);
 useEffect(()=>{setRaces([]);setOverview(undefined);setLoading(true);setError("");getRaces(year).then(x=>{setRaces(x);if(x.length)setRound(x[0].round)}).catch(e=>setError(apiErrorMessage(e,"Unable to load season"))).finally(()=>setLoading(false))},[year,retry]);
 useEffect(()=>{if(!races.length || !races.some(r=>r.round===round))return;let active=true;setLoading(true);setError("");setOverview(undefined);getRaceOverview(year,round).then(x=>{if(active)setOverview(x)}).catch(e=>{if(active){setOverview(undefined);setError(apiErrorMessage(e,"Unable to load race"))}}).finally(()=>{if(active)setLoading(false)});return()=>{active=false}},[year,round,races.length]);
 const race=races.find(r=>r.round===round);
 return <div className="app"><Sidebar active={active} setActive={setActive} year={year} setYear={setYear} races={races} round={round} setRound={setRound}/>
 <main><header className="topbar"><div><div className="top-title"><span className="redline"></span><span>F1 PERFORMANCE LAB</span></div><div className="race-context">{race?.raceName??"Loading"} <b>·</b> {race?.circuitName??""} <b>·</b> {race?.date??""}</div></div><div className="top-status"><Wifi size={13}/> {backendOnline===true?"API CONNECTED":backendOnline===false?"API DISCONNECTED":"CHECKING API"} <span>v13.3</span></div></header>
 {error&&<div className="error-box">{error} <button type="button" onClick={()=>setRetry(r=>r+1)} style={{marginLeft:12,padding:"6px 12px",cursor:"pointer"}}>Retry connection</button><div style={{marginTop:8,fontSize:12}}>Check <a href="http://127.0.0.1:8000/api/health" target="_blank" rel="noreferrer">backend health endpoint</a>. Start backend with <code>python -m uvicorn app.main:app --reload --port 8000</code> in the backend folder.</div></div>}{loading&&<div className="loading"><RefreshCw className="spin"/> Syncing race data…</div>}
 {!loading&&overview&&active==="results"&&<ResultsPage overview={overview}/>}
 {!loading&&overview&&active==="stints"&&<StintPage year={year} round={round} drivers={overview.drivers}/>}
 {!loading&&overview&&active==="insights"&&<InsightsPage results={overview.results}/>}
 {active==="simulator"&&<EnergyPage/>}
 {!loading&&overview&&active==="ml"&&<DiscoveryPage year={year} round={round} drivers={overview.drivers}/>}
 {!loading&&overview&&active==="telemetry"&&<TelemetryPage year={year} round={round} drivers={overview.drivers}/>}
 {active==="benchmark"&&<BenchmarkPage/>}
 {active==="steering"&&<SteeringResearchPage/>}
 {!loading&&overview&&active==="debrief"&&<DebriefPage year={year} round={round} drivers={overview.drivers}/>}
 <footer>F1 PERFORMANCE LAB <span>·</span> public data research platform <span>·</span> Jolpica / OpenF1</footer>
 </main></div>
}
