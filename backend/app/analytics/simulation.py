"""Transparent, reproducible strategy scenario models (not team-grade simulators)."""
import numpy as np


def simulate_strategy(race_laps:int, base_pace:float, degradation_per_lap:float,
                      pit_loss:float, stops:list[int], iterations:int=3000, seed:int=42):
    stops=sorted(set(int(s) for s in stops if 1 < int(s) < race_laps))
    rng=np.random.default_rng(seed); results=np.zeros(iterations,dtype=float)
    # Common random numbers: each iteration uses one noise vector for comparable runs.
    noise=rng.normal(0,0.12,size=(iterations,race_laps))
    for i in range(iterations):
        total=0.0; age=0; stop_idx=0
        for lap in range(1,race_laps+1):
            if stop_idx<len(stops) and lap==stops[stop_idx]:
                total+=pit_loss; age=0; stop_idx+=1
            total+=base_pace+degradation_per_lap*age+noise[i,lap-1]
            age+=1
        results[i]=total
    return {"mean":float(np.mean(results)),"median":float(np.median(results)),
            "p10":float(np.percentile(results,10)),"p90":float(np.percentile(results,90)),
            "best":float(np.min(results)),"worst":float(np.max(results)),
            "iterations":iterations,"stops":stops,"seed":seed,
            "model_note":"Deterministic-seed Monte Carlo with constant per-lap degradation and Gaussian lap-time noise. User-supplied assumptions; not calibrated to a team's simulator."}


def compare_strategy_scenarios(race_laps:int=57,base_pace:float=92.0,pit_loss:float=22.0,
                               soft_offset:float=-0.25,medium_offset:float=0.0,hard_offset:float=0.25,
                               soft_deg:float=0.075,medium_deg:float=0.045,hard_deg:float=0.025,
                               iterations:int=3000,seed:int=42):
    """Compare illustrative one- and two-stop compound strategies under stated assumptions."""
    compounds={"SOFT":(soft_offset,soft_deg),"MEDIUM":(medium_offset,medium_deg),"HARD":(hard_offset,hard_deg)}
    rng=np.random.default_rng(seed); noise=rng.normal(0,0.12,size=(iterations,race_laps))
    scenarios=[]
    # Enumerate one-stop and two-stop windows; enforce at least 8 laps per stint.
    for stops_count in (1,2):
        if stops_count==1:
            stop_sets=[(s,) for s in range(12,race_laps-7,2)]
        else:
            stop_sets=[(a,b) for a in range(10,race_laps-15,3) for b in range(a+8,race_laps-6,3)]
        for stops in stop_sets:
            bounds=(0,)+stops+(race_laps,)
            for choices in __import__('itertools').product(compounds, repeat=len(bounds)-1):
                if len(set(choices))<2: continue
                times=np.zeros(iterations,dtype=float)
                for stint_idx,compound in enumerate(choices):
                    start,end=bounds[stint_idx],bounds[stint_idx+1]
                    offset,deg=compounds[compound]
                    for j,lap_index in enumerate(range(start,end)):
                        tyre_age=j
                        times += (base_pace+offset+deg*tyre_age+noise[:,lap_index])
                times += pit_loss*len(stops)
                scenarios.append({"stops":list(stops),"compounds":list(choices),
                                   "mean_s":float(np.mean(times)),"p10_s":float(np.percentile(times,10)),
                                   "p90_s":float(np.percentile(times,90))})
    scenarios.sort(key=lambda x:x["mean_s"])
    return {"ready":bool(scenarios),"race_laps":race_laps,"iterations":iterations,"seed":seed,
            "best_scenarios":scenarios[:10],"assumptions":{"base_pace_s":base_pace,"pit_loss_s":pit_loss,
            "compound_parameters":{k:{"pace_offset_s":v[0],"degradation_s_per_lap":v[1]} for k,v in compounds.items()},
            "lap_time_noise_std_s":0.12},
            "model_note":"Illustrative scenario ranking only. Compound pace offsets and degradation rates are inputs/default assumptions, not live Pirelli or team data. Safety cars, traffic, weather, warm-up, tyre allocation, track evolution and undercut/overcut effects are not modelled."}
