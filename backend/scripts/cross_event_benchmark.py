"""Fetch real OpenF1 races, report descriptive slope heterogeneity (NOT transfer performance)."""
import argparse, json, sys, unicodedata
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.openf1 import get_race_sessions,get_laps,get_stints
from app.analytics.advanced import observed_stint_points, compare_stint_models
from app.analytics.bayesian import bayesian_tyre_model


# User-facing Grand Prix names differ from the OpenF1 circuit/location fields.
# Keep aliases explicit; never guess a race session from a partial substring alone.
CIRCUIT_ALIASES = {
    'bahrain': {'bahrain', 'sakhir'},
    'belgium': {'belgium', 'spa', 'spa-francorchamps'},
    'monaco': {'monaco', 'monte carlo'},
    'saudi arabia': {'saudi arabia', 'jeddah'},
    'australia': {'australia', 'melbourne'},
    'japan': {'japan', 'suzuka'},
    'china': {'china', 'shanghai'},
    'emilia romagna': {'emilia romagna', 'imola'},
    'canada': {'canada', 'montreal'},
    'spain': {'spain', 'barcelona', 'catalunya'},
    'austria': {'austria', 'spielberg'},
    'great britain': {'great britain', 'silverstone'},
    'united kingdom': {'great britain', 'silverstone'},
    'hungary': {'hungary', 'hungaroring', 'budapest'},
    'netherlands': {'netherlands', 'zandvoort'},
    'italy': {'italy', 'monza'},
    'azerbaijan': {'azerbaijan', 'baku'},
    'singapore': {'singapore', 'marina bay'},
    'united states': {'united states', 'austin'},
    'usa': {'united states', 'austin'},
    'mexico': {'mexico', 'mexico city'},
    'brazil': {'brazil', 'interlagos', 'sao paulo'},
    'las vegas': {'las vegas'},
    'qatar': {'qatar', 'lusail'},
    'abu dhabi': {'abu dhabi', 'yas marina', 'yas island', 'yas marina circuit'},
}


def _norm(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    return ' '.join(''.join(c for c in text if not unicodedata.combining(c)).lower().replace('-', ' ').split())


def match_race_sessions(sessions, circuit):
    query = _norm(circuit)
    names = {_norm(name) for name in CIRCUIT_ALIASES.get(query, {query})}
    names.add(query)
    found = []
    for session in sessions:
        candidates = {_norm(session.get(field)) for field in ('circuit_short_name', 'meeting_name', 'location', 'country_name', 'country_code')}
        if names & candidates:
            found.append(session)
    return found


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--year',type=int,default=2024)
    parser.add_argument('--driver',type=int,default=1)
    parser.add_argument('--circuits',nargs='+',default=['Bahrain','Monaco','Belgium'])
    parser.add_argument('--output',default='results/cross_event_real.json')
    args=parser.parse_args()
    sessions=get_race_sessions(args.year)
    events=[]
    for circuit in args.circuits:
        matching=match_race_sessions(sessions,circuit)
        if not matching:
            events.append({'circuit':circuit,'status':'unavailable','reason':'No matching race session'});continue
        key=matching[0]['session_key']
        matched_name=matching[0].get('circuit_short_name') or matching[0].get('location')
        try:
            laps=get_laps(key,args.driver);stints=get_stints(key,args.driver)
            points=observed_stint_points(laps,stints)
            result=bayesian_tyre_model(laps,stints)
            if not result.get('ready'): events.append({'circuit':circuit,'session_key':key,'matched_circuit':matched_name,'status':'unavailable','reason':result.get('message')});continue
            events.append({'circuit':circuit,'session_key':key,'matched_circuit':matched_name,'status':'computed','n_laps':len(points), 'predictive_benchmark':compare_stint_models(points), 'slope':result['posterior_mean_s_per_lap'],'ci95':result['credible_interval_95_s_per_lap']})
        except Exception as exc:events.append({'circuit':circuit,'session_key':key,'matched_circuit':matched_name,'status':'unavailable','reason':str(exc)})
    valid=[e for e in events if e['status']=='computed']
    median=float(np.median([e['slope'] for e in valid])) if valid else None
    for e in valid:e['ci_contains_global_median']=(e['ci95'][0]<=median<=e['ci95'][1])
    out={'source':'OpenF1','year':args.year,'driver':args.driver,'events':events,'median_observed_slope':median,'limitations':'Fitted slopes are descriptive heterogeneity, NOT cross-event transfer accuracy. The predictive_benchmark uses within-stint chronological held-out laps, not held-out circuits. Different compounds, weather, fuel loads and circuits confound slope comparisons. No regime-shift claim from CI non-overlap alone.'}
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

if __name__=='__main__':main()
