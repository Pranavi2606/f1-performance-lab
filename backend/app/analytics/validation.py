"""Auditable coverage and cross-event holdout evaluation. No synthetic observations."""
from datetime import datetime
from collections import Counter
import math
import numpy as np


def _timestamp(row):
    try:
        s = row.get("date") or row.get("date_start")
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError, AttributeError):
        return None


def audit_feed(rows, required=(), time_key="date", gap_seconds=None):
    if rows is None:
        return {"available": False, "rows": 0, "message": "Feed unavailable; no values imputed"}
    timestamps = []
    missing = Counter()
    for row in rows:
        for key in required:
            if row.get(key) is None:
                missing[key] += 1
        val = row.get(time_key)
        try:
            t = datetime.fromisoformat(val.replace("Z", "+00:00")).timestamp() if val else None
        except (TypeError, ValueError, AttributeError):
            t = None
        if t is not None: timestamps.append(t)
    ordered = sorted(timestamps)
    diffs = np.diff(ordered) if len(ordered) > 1 else np.array([])
    duplicate_count = len(timestamps) - len(set(timestamps))
    out = {"available": bool(rows), "rows": len(rows), "timestamped_rows": len(timestamps),
           "missing_fields": dict(missing), "duplicate_timestamps": duplicate_count,
           "out_of_order_timestamps": sum(x > y for x,y in zip(timestamps,timestamps[1:])),
           "median_sampling_interval_s": float(np.median(diffs)) if len(diffs) else None,
           "largest_gap_s": float(max(diffs)) if len(diffs) else None,
           "start_utc": datetime.fromtimestamp(ordered[0], __import__('datetime').timezone.utc).isoformat() if ordered else None,
           "end_utc": datetime.fromtimestamp(ordered[-1], __import__('datetime').timezone.utc).isoformat() if ordered else None}
    if gap_seconds is not None:
        out["gaps_above_threshold"] = int(np.sum(diffs > gap_seconds))
        out["gap_threshold_s"] = gap_seconds
    return out


def audit_session(laps, stints, car, location, weather, race_control):
    feeds = {"laps": audit_feed(laps, ("lap_number", "lap_duration"), "date_start"),
             "stints": audit_feed(stints, ("lap_start", "lap_end", "compound"), "date"),
             "car_data": audit_feed(car, ("speed", "throttle", "brake", "rpm", "n_gear"), gap_seconds=3),
             "location": audit_feed(location, ("x", "y"), gap_seconds=3),
             "weather": audit_feed(weather, ("track_temperature",), gap_seconds=900),
             "race_control": audit_feed(race_control, (), gap_seconds=None)}
    lap_numbers = [r.get("lap_number") for r in laps if r.get("lap_number") is not None]
    feeds["laps"]["duplicate_lap_numbers"] = len(lap_numbers) - len(set(lap_numbers))
    return {"feeds": feeds, "source": "OpenF1", "rule": "Missing feeds remain unavailable; gaps are not interpolated. Timestamp duplicates may be valid if multiple messages share a timestamp."}


def evaluate_held_out_events(events):
    """Leave-one-event-out simple age slope vs training median; requires >=3 observed events."""
    cleaned = []
    for e in events:
        pts = [(float(x["age"]), float(x["lap_time"])) for x in e.get("points", [])
               if x.get("age") is not None and x.get("lap_time") is not None
               and math.isfinite(float(x["age"])) and math.isfinite(float(x["lap_time"]))]
        if len(pts) >= 8: cleaned.append((str(e["event_id"]), pts))
    if len(cleaned) < 3:
        return {"ready": False, "events_usable": len(cleaned), "message": "At least three distinct events with eight valid laps each are required; no synthetic races."}
    results = []
    for event_id, test in cleaned:
        train = [x for other_id, rows in cleaned if other_id != event_id for x in rows]
        X = np.array([[1., a] for a, _ in train]); y = np.array([t for _, t in train])
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        actual = np.array([t for _, t in test]); ages = np.array([a for a, _ in test])
        pred = beta[0] + beta[1]*ages
        baseline = np.full(len(test), float(np.median(y)))
        results.append({"held_out_event": event_id, "train_laps": len(train), "test_laps": len(test),
                        "linear_mae_s": float(np.mean(abs(actual-pred))),
                        "median_baseline_mae_s": float(np.mean(abs(actual-baseline))),
                        "linear_rmse_s": float(np.sqrt(np.mean((actual-pred)**2)))})
    return {"ready": True, "events_usable": len(cleaned), "folds": results,
            "mean_linear_mae_s": float(np.mean([r["linear_mae_s"] for r in results])),
            "mean_baseline_mae_s": float(np.mean([r["median_baseline_mae_s"] for r in results])),
            "limitations": "Leave-one-event-out evaluation on supplied observed lap rows. Different circuits, drivers, fuel loads, compound and race conditions can invalidate cross-event transfer; this is a baseline, not calibrated tyre physics."}


def audit_telemetry_ranges(car_rows):
    """Conservative physical/encoding sanity checks, not homologation limits."""
    limits={'speed':(0,450),'throttle':(0,100),'brake':(0,100),'rpm':(0,25000),'n_gear':(0,9)}
    counts={key:0 for key in limits}; examples={key:[] for key in limits}
    for row in car_rows or []:
        for key,(lo,hi) in limits.items():
            v=row.get(key)
            if v is None:continue
            try:
                x=float(v)
                invalid=not math.isfinite(x) or x<lo or x>hi
            except (ValueError,TypeError):invalid=True
            if invalid:
                counts[key]+=1
                if len(examples[key])<3:examples[key].append({'date':row.get('date'),'value':v})
    return {'available':car_rows is not None,'sanity_range_violations':counts,
            'examples':{k:v for k,v in examples.items() if v},
            'limits':limits,'note':'Heuristic sanity bounds, not FIA technical limits. Brake may be binary in OpenF1.'}


def audit_lap_set_consistency(laps,stints,car_rows):
    from .advanced import observed_stint_points
    observed={int(l['lap_number']) for l in laps or [] if str(l.get('lap_number','')).isdigit()}
    covered=set()
    for s in stints or []:
        try:
            a,b=int(s['lap_start']),int(s['lap_end'])
            if b>=a and b-a<200:covered.update(range(a,b+1))
        except (KeyError,ValueError,TypeError):pass
    timestamps=[_timestamp(r) for r in car_rows or []]
    timestamps=[t for t in timestamps if t is not None]
    timed_laps=[]
    for lap in laps or []:
        try:
            start=_timestamp(lap); duration=float(lap['lap_duration'])
            if start is not None and 0<duration<300:timed_laps.append((int(lap['lap_number']),start,start+duration))
        except (KeyError,ValueError,TypeError):pass
    # Each timestamp is checked against observed lap windows; car data has no lap_number.
    import bisect
    sorted_times=sorted(timestamps)
    with_samples=[n for n,a,b in timed_laps if bisect.bisect_right(sorted_times,b)>bisect.bisect_left(sorted_times,a)]
    return {'observed_lap_count':len(observed),'stint_covered_lap_count':len(covered),
            'observed_laps_without_stint':sorted(observed-covered),
            'stint_laps_without_lap_record':sorted(covered-observed),
            'lap_windows_with_car_samples':len(with_samples),
            'timed_lap_windows':len(timed_laps),
            'car_data_available':car_rows is not None,
            'note':'Car samples mapped by observed timestamp windows only; coverage does not establish perfect cross-source synchronization.'}
