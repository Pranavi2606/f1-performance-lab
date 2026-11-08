import axios from "axios";
import type { DegradationResponse, Driver, OpenF1Session, Race, Result, SimulationResult, DriverTelemetry } from "../types/f1";

const api = axios.create({ baseURL: "/api", timeout: 30000 });

export interface RaceOverview {
  race: Race; results: Result[]; openf1Session: OpenF1Session; drivers: Driver[];
}
export async function getRaces(year: number) {
  return (await api.get<Race[]>(`/seasons/${year}/races`)).data;
}
export async function getRaceOverview(year: number, round: number) {
  return (await api.get<RaceOverview>(`/races/${year}/${round}/overview`)).data;
}
export async function getDegradation(year: number, round: number, driverNumber: number) {
  return (await api.get<DegradationResponse>(`/analytics/degradation/${year}/${round}/${driverNumber}`)).data;
}
export async function simulateStrategy(payload: {
  raceLaps:number;basePace:number;degradationPerLap:number;pitLoss:number;stops:number[];iterations:number;
}) {
  return (await api.post<SimulationResult>("/analytics/simulate", payload)).data;
}
export async function getTelemetry(year:number, round:number, driverNumber:number, lapNumber?:number) {
  return (await api.get<DriverTelemetry>(`/analytics/telemetry/${year}/${round}/${driverNumber}`, {params:{lap_number:lapNumber}})).data;
}

export async function getResearchBundle(year:number, round:number, driverNumber:number) {
  return (await api.get(`/research/${year}/${round}/${driverNumber}`)).data;
}

export async function getStrategyScenarios(raceLaps:number,basePace:number,pitLoss:number) {
  return (await api.get("/analytics/strategy-scenarios", {params:{race_laps:raceLaps,base_pace:basePace,pit_loss:pitLoss,iterations:1500}})).data;
}

export async function getEnergyComparison(year:number,round:number,driverNumbers:number[]) {
  return (await api.get(`/research/compare/${year}/${round}`, {params:{driver_numbers:driverNumbers}})).data;
}

/** Human-readable connectivity diagnostics; avoid silently treating HTTP failures as empty seasons. */
export function apiErrorMessage(error: unknown, context: string): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return `${context}: backend API is unreachable. Start FastAPI at http://127.0.0.1:8000 and verify /api/health. (${error.message})`;
    }
    const detail = error.response.data?.detail;
    return `${context}: HTTP ${error.response.status}${detail ? ` — ${String(detail)}` : ''}`;
  }
  return `${context}: ${error instanceof Error ? error.message : 'unknown error'}`;
}
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await api.get<{status: string}>("/health", {timeout: 5000});
    return response.data.status === "ok";
  } catch {
    return false;
  }
}

export async function getDriverDebrief(year:number, round:number, primaryDriverNumber:number, compareDriverNumbers:number[], primaryLapNumber?:number, compareLapNumber?:number) {
  // FastAPI expects repeated query keys, not Axios's default compare_driver_numbers[]=...
  const params = new URLSearchParams();
  for (const number of compareDriverNumbers) params.append('compare_driver_numbers', String(number));
  if (primaryLapNumber != null) params.set('primary_lap_number', String(primaryLapNumber));
  if (compareLapNumber != null) params.set('compare_lap_number', String(compareLapNumber));
  return (await api.get(`/analytics/debrief/${year}/${round}/${primaryDriverNumber}`, {params, timeout:120000})).data;
}

export async function getDriverTrack(year:number, round:number, driver:number, lap:number, bounds:number[][]){
  return (await api.get(`/analytics/debrief/track/${year}/${round}/${driver}`,{params:{lap_number:lap,zones:bounds.map(b=>b.join(',')).join(';')},timeout:120000})).data;
}
export async function exportDriverDebrief(report:any, format:'md'|'pdf'):Promise<Blob>{
  return (await api.post(`/analytics/debrief/export/${format}`, {report}, {responseType:'blob',timeout:60000})).data;
}

export async function getDriverLaps(year:number, round:number, driverNumber:number){
 return (await api.get(`/analytics/laps/${year}/${round}/${driverNumber}`)).data as {laps:Array<{lap_number:number;duration_s:number;compound:string;stint?:number}>};
}
