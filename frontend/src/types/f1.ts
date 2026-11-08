export interface Race {
  season: number; round: number; raceName: string; date: string; time?: string;
  circuitId: string; circuitName: string; locality: string; country: string;
}
export interface Result {
  position: number | null; number?: string; driverId: string; driver: string;
  constructor: string; grid: number | null; points: number; status: string; laps: number | null;
}
export interface OpenF1Session {
  session_key: number; session_type: string; session_name: string; date_start: string;
  date_end: string; meeting_key: number; circuit_short_name: string; country_name: string;
  location: string; year: number;
}
export interface Driver {
  driver_number: number; full_name: string; name_acronym: string; first_name: string;
  last_name: string; team_name: string; team_colour?: string;
}
export interface StintAnalysis {
  stintNumber: number; compound: string; lapStart: number; lapEnd: number;
  tyreAgeAtStart: number | null; degradationRate: number; intercept: number; rSquared: number;
  lapsAnalyzed: number; recommendation: "HIGH_DEG" | "MED_DEG" | "LOW_DEG";
  message: string; points: { lap: number; time: number }[];
}
export interface DegradationResponse {
  driverNumber: number; sessionKey: number; raceName: string;
  analysis: {
    cleanLapCount: number; excludedLapCount: number;
    excludedReasons: { lap: number; reason: string }[];
    stints: StintAnalysis[];
  };
}
export interface SimulationResult {
  mean: number; median: number; p10: number; p90: number;
  best: number; worst: number; iterations: number; stops: number[];
}
export interface DriverTelemetry {
  driver_number: number;
  full_name: string;
  team_name: string;
  laps: number;
  avg_speed: number;
  max_speed: number;
  avg_throttle: number;
  brake_events: number;
  selected_lap?: number; lap_time_s?: number; measurement_note?: string;
  points: { distance: number; speed: number; throttle: number; brake: number; rpm?:number; gear?:number }[];
}
