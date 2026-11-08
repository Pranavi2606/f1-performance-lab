"""Reproducible analyses using public telemetry.

All outputs are explicitly labelled as observed, derived or modelled. Public
telemetry does not expose proprietary ERS commands, battery state or tyre state.
"""
from __future__ import annotations
from datetime import datetime
from statistics import median
from typing import Any
import math
import numpy as np


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _number(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return 100.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * p
    lo, hi = int(pos), min(int(pos) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def energy_fingerprint(car_data: list[dict[str, Any]], *, min_speed_kph: float = 180.0,
                       throttle_pct: float = 95.0, max_brake: float = 5.0) -> dict[str, Any]:
    """Find sustained high-throttle, low-brake acceleration windows.

    Candidate straight-line acceleration fingerprints only; never infer ERS.
    """
    rows = sorted((r for r in car_data if r.get("date")), key=lambda r: r["date"])
    samples = []
    for row in rows:
        try:
            samples.append({"t": _time(row["date"]).timestamp(), "speed": _number(row, "speed"),
                            "throttle": _number(row, "throttle"), "brake": _number(row, "brake")})
        except (ValueError, TypeError):
            continue
    candidates: list[dict[str, float]] = []
    active: list[dict[str, float]] = []
    for i, sample in enumerate(samples):
        accelerating = False
        if i and sample["t"] > samples[i-1]["t"]:
            dt = sample["t"] - samples[i-1]["t"]
            accel = ((sample["speed"] - samples[i-1]["speed"]) / 3.6) / dt
            accelerating = accel > 0.15
        qualifies = (sample["speed"] >= min_speed_kph and sample["throttle"] >= throttle_pct
                     and sample["brake"] <= max_brake and accelerating)
        if qualifies:
            active.append(sample)
        elif active:
            if len(active) >= 3:
                candidates.append({"duration_s": active[-1]["t"] - active[0]["t"],
                                   "start_speed_kph": active[0]["speed"], "end_speed_kph": active[-1]["speed"],
                                   "mean_throttle_pct": sum(x["throttle"] for x in active)/len(active)})
            active = []
    if len(active) >= 3:
        candidates.append({"duration_s": active[-1]["t"] - active[0]["t"],
                           "start_speed_kph": active[0]["speed"], "end_speed_kph": active[-1]["speed"],
                           "mean_throttle_pct": sum(x["throttle"] for x in active)/len(active)})
    return {"method": "high-throttle, low-brake, positive longitudinal speed-change proxy",
            "sample_count": len(samples), "candidate_count": len(candidates),
            "total_candidate_seconds": round(sum(x["duration_s"] for x in candidates), 2),
            "candidates": [{k: round(v, 2) for k, v in c.items()} for c in candidates],
            "interpretation": "Candidate acceleration windows only. Public speed/throttle/brake data cannot identify ERS deployment, MGU-K power, or battery state of charge."}


def normalized_lap_segment(laps: list[dict[str, Any]], car_data: list[dict[str, Any]],
                            start_pct: float = 0.80, end_pct: float = 0.90) -> dict[str, Any]:
    """Legacy fallback: timestamp-aligned normalized elapsed-time window."""
    if not (0 <= start_pct < end_pct <= 1):
        raise ValueError("Segment percentages must satisfy 0 <= start < end <= 1")
    telemetry = sorted((r for r in car_data if r.get("date") and r.get("speed") is not None), key=lambda r: r["date"])
    output, excluded = [], 0
    for lap in laps:
        try:
            start = _time(lap["date_start"])
            duration = _number(lap, "lap_duration")
            if duration <= 0 and lap.get("date_end"):
                duration = (_time(lap["date_end"]) - start).total_seconds()
            if duration <= 0:
                excluded += 1; continue
            left, right = start.timestamp()+duration*start_pct, start.timestamp()+duration*end_pct
            speeds = [_number(r, "speed") for r in telemetry if left <= _time(r["date"]).timestamp() <= right]
            if len(speeds) < 3:
                excluded += 1; continue
            output.append({"lap_number": int(lap.get("lap_number", 0)), "mean_speed_kph": round(float(np.mean(speeds)), 2), "sample_count": len(speeds)})
        except (KeyError, TypeError, ValueError, OverflowError):
            excluded += 1
    values = [x["mean_speed_kph"] for x in output]
    if not values:
        return {"ready": False, "laps_used": 0, "laps_excluded": excluded,
                "message": "Insufficient timestamp-aligned telemetry in the selected normalized lap window."}
    q1, q3 = _percentile(values, .25), _percentile(values, .75)
    return {"ready": True, "window": {"start_pct": start_pct, "end_pct": end_pct},
            "window_label": f"{start_pct:.0%}–{end_pct:.0%} of elapsed lap time", "laps_used": len(values),
            "laps_excluded": excluded, "mean_speed_kph": round(float(np.mean(values)), 2),
            "median_speed_kph": round(median(values), 2), "speed_iqr_kph": round(q3-q1, 2),
            "lap_values": output,
            "interpretation": "Within-driver speed repeatability in a normalized elapsed-time segment. Not a named corner-exit metric."}


def _moving_average(values: np.ndarray, window: int = 5) -> np.ndarray:
    if len(values) < window:
        return values
    kernel = np.ones(window, dtype=float) / window
    return np.convolve(values, kernel, mode="same")


def corner_exit_repeatability(laps: list[dict[str, Any]], location: list[dict[str, Any]],
                              car_data: list[dict[str, Any]], *, min_corner_m: float = 25.0,
                              max_corner_m: float = 450.0) -> dict[str, Any]:
    """Detect curvature-defined corner-like zones from XY position and compare exits.

    These are algorithmically detected curve zones, not official FIA turn boundaries.
    Per-lap distance is integrated from location samples and used for alignment.
    """
    if not location:
        return {"ready": False, "message": "No location samples available; normalized elapsed-time analysis remains available."}
    car = sorted([r for r in car_data if r.get("date")], key=lambda r: r["date"])
    if not car:
        return {"ready": False, "message": "No timestamped car telemetry available."}
    car_times = np.array([_time(r["date"]).timestamp() for r in car])
    car_speeds = np.array([_number(r, "speed") for r in car])
    car_throttle = np.array([_number(r, "throttle") for r in car])
    car_brake = np.array([_number(r, "brake") for r in car])
    lap_curves: dict[int, list[dict[str, float]]] = {}
    for lap in laps:
        try:
            lap_no = int(lap["lap_number"]); start = _time(lap["date_start"]).timestamp()
            duration = _number(lap, "lap_duration")
            if duration <= 0: continue
            end = start + duration
            pts = [p for p in location if p.get("date") and start <= _time(p["date"]).timestamp() <= end and p.get("x") is not None and p.get("y") is not None]
            if len(pts) < 25: continue
            ts = np.array([_time(p["date"]).timestamp() for p in pts])
            xy = np.array([[_number(p,"x"), _number(p,"y")] for p in pts], dtype=float)
            delta = np.diff(xy, axis=0); ds = np.linalg.norm(delta, axis=1)
            headings = np.unwrap(np.arctan2(delta[:,1], delta[:,0]))
            dhead = np.diff(headings)
            segdist = np.maximum((ds[:-1]+ds[1:])*0.5, 0.5)
            curvature = np.abs(dhead) / segdist
            curvature = _moving_average(curvature, 5)
            dist = np.concatenate(([0.0], np.cumsum(ds)))
            # Adaptive threshold suppresses GPS noise while retaining sustained turns.
            threshold = max(float(np.percentile(curvature, 72)), 0.0008)
            active = curvature >= threshold
            zones, idx = [], 0
            while idx < len(active):
                if not active[idx]: idx += 1; continue
                j = idx
                while j+1 < len(active) and active[j+1]: j += 1
                d0, d1 = float(dist[idx]), float(dist[min(j+2, len(dist)-1)])
                length = d1-d0
                if min_corner_m <= length <= max_corner_m:
                    zones.append({"entry_m": d0, "exit_m": d1, "length_m": length})
                idx = j+1
            if zones:
                # Attach speed/throttle/brake to GPS samples via nearest timestamp.
                values = []
                for p, t, d in zip(pts, ts, dist):
                    k = int(np.searchsorted(car_times, t))
                    if k <= 0: k = 0
                    elif k >= len(car_times): k = len(car_times)-1
                    elif abs(car_times[k-1]-t) <= abs(car_times[k]-t): k -= 1
                    values.append((float(d), float(car_speeds[k]), float(car_throttle[k]), float(car_brake[k])))
                lap_curves[lap_no] = [{**z, "samples": values} for z in zones]
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    if len(lap_curves) < 2:
        return {"ready": False, "laps_with_location": len(lap_curves),
                "message": "Fewer than two laps had sufficient location samples for repeatability analysis."}
    # Use the lap with the most detected zones as reference, then compare same-order zones.
    reference_lap = max(lap_curves, key=lambda k: len(lap_curves[k]))
    ref_zones = lap_curves[reference_lap]
    comparisons = []
    for corner_idx, ref in enumerate(ref_zones, start=1):
        rows = []
        for lap_no, zones in lap_curves.items():
            if corner_idx-1 >= len(zones): continue
            z = zones[corner_idx-1]; samples = z["samples"]
            # Exit metric is average speed and throttle in final 30m of the detected curved zone.
            exit_samples = [s for s in samples if z["exit_m"]-30 <= s[0] <= z["exit_m"]+35]
            if len(exit_samples) < 2: continue
            rows.append({"lap_number": lap_no,
                         "exit_speed_kph": round(float(np.mean([s[1] for s in exit_samples])), 2),
                         "exit_throttle_pct": round(float(np.mean([s[2] for s in exit_samples])), 2),
                         "brake_active_pct": round(float(np.mean([s[3] > 5 for s in exit_samples])*100), 1)})
        if len(rows) >= 2:
            speeds = [r["exit_speed_kph"] for r in rows]
            comparisons.append({"corner_like_segment": corner_idx, "reference_lap": reference_lap,
                                "reference_entry_m": round(ref["entry_m"],1), "reference_exit_m": round(ref["exit_m"],1),
                                "laps_compared": len(rows), "mean_exit_speed_kph": round(float(np.mean(speeds)),2),
                                "exit_speed_iqr_kph": round(float(np.percentile(speeds,75)-np.percentile(speeds,25)),2),
                                "lap_values": rows})
    return {"ready": bool(comparisons), "method": "XY trajectory curvature threshold; per-lap integrated distance; exit window from -30m to +35m around detected curve end",
            "reference_lap": reference_lap, "laps_with_location": len(lap_curves),
            "segments": comparisons,
            "interpretation": "Curve-like segments are inferred from public XY location samples, not official corner IDs. Same-order segment matching is exploratory; inspect track map and sample quality before interpreting driver differences."}


def _nearest_weather(timestamp: float, weather: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    for row in weather:
        try: candidates.append((_time(row["date"]).timestamp(), row))
        except (KeyError, TypeError, ValueError): pass
    return min(candidates, key=lambda x: abs(x[0]-timestamp))[1] if candidates else {}


def contextual_tyre_analysis(laps: list[dict[str, Any]], stints: list[dict[str, Any]],
                              weather: list[dict[str, Any]] | None = None,
                              race_control: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Compare within-stint linear trend with a small context-adjusted OLS model.

    Covariates are included only when present. This is an association model, not a
    causal tyre-wear estimate; weather is nearest-sample and track status is inferred
    from race-control message text.
    """
    weather, race_control = weather or [], race_control or []
    controls = []
    for msg in race_control:
        text = str(msg.get("message", "")).upper()
        if any(term in text for term in ("SAFETY CAR", "VIRTUAL SAFETY CAR", "YELLOW", "RED FLAG")):
            try: controls.append((_time(msg["date"]).timestamp(), text))
            except (KeyError, TypeError, ValueError): pass
    output, excluded = [], []
    stint_by_lap = {}
    for stint in stints:
        for lap_no in range(int(stint.get("lap_start",0)), int(stint.get("lap_end",0))+1):
            stint_by_lap[lap_no] = stint
    raw = []
    for lap in laps:
        try:
            lap_no = int(lap["lap_number"]); duration = float(lap["lap_duration"])
            if duration <= 0: raise ValueError()
            if lap.get("is_pit_out_lap") is True: excluded.append({"lap":lap_no,"reason":"pit_out_lap"}); continue
            if lap_no not in stint_by_lap: excluded.append({"lap":lap_no,"reason":"no_stint_metadata"}); continue
            start = _time(lap["date_start"]).timestamp()
            end = start + duration
            weather_row = _nearest_weather(start, weather)
            active_flags = [flag for t,flag in controls if start <= t <= end]
            status = "green"
            if any("RED FLAG" in f for f in active_flags): status="red_flag"
            elif any("SAFETY CAR" in f for f in active_flags): status="safety_car"
            elif any("YELLOW" in f for f in active_flags): status="yellow"
            if status != "green": excluded.append({"lap":lap_no,"reason":status}); continue
            stint = stint_by_lap[lap_no]
            tyre_age = max(0, lap_no-int(stint.get("lap_start",lap_no)))
            raw.append({"lap":lap_no,"time":duration,"age":float(tyre_age),
                        "stint_id":int(stint.get("stint_number", 0)),
                        "track_temp":_number(weather_row,"track_temperature",float("nan")),
                        "air_temp":_number(weather_row,"air_temperature",float("nan")),
                        "rain":1.0 if _number(weather_row,"rainfall",0)>0 else 0.0,
                        "compound":str(stint.get("compound","UNKNOWN"))})
        except (KeyError, TypeError, ValueError, OverflowError):
            excluded.append({"lap":int(lap.get("lap_number",0)),"reason":"missing_or_invalid_fields"})
    # Exclude extreme lap-time outliers within the session, then fit by compound/stint age.
    if len(raw) >= 5:
        vals=np.array([r["time"] for r in raw]); med=float(np.median(vals)); mad=float(np.median(np.abs(vals-med)))
        limit=med+max(5.0,5*1.4826*mad)
        kept=[]
        for r in raw:
            if r["time"]>limit: excluded.append({"lap":r["lap"],"reason":"extreme_lap_time_outlier"})
            else: kept.append(r)
        raw=kept
    if len(raw)<6:
        return {"ready":False,"laps_used":len(raw),"laps_excluded":len(excluded),"excluded":excluded,
                "message":"At least six valid green-flag lap observations are required for contextual model comparison."}
    # Include stint fixed effects so tyre-age resets do not masquerade as one wear curve.
    y=np.array([r["time"] for r in raw],dtype=float)
    age=np.array([r["age"] for r in raw],dtype=float)
    stint_ids=sorted({r["stint_id"] for r in raw})
    fixed_effects=np.column_stack([[1.0 if r["stint_id"]==sid else 0.0 for r in raw]
                                   for sid in stint_ids[1:]]) if len(stint_ids)>1 else np.empty((len(raw),0))
    def fit_design(X):
        beta=np.linalg.lstsq(X,y,rcond=None)[0]
        pred=X@beta; residual=y-pred; rss=max(float(np.sum(residual**2)),1e-12)
        total=float(np.sum((y-y.mean())**2)); k=X.shape[1]; n=len(y)
        return beta,pred,{"r2":round(1-rss/total,4) if total else 0.0,
                          "mae_s":round(float(np.mean(np.abs(residual))),4),
                          "rmse_s":round(float(np.sqrt(np.mean(residual**2))),4),
                          "bic":round(float(n*np.log(rss/n)+k*np.log(n)),3)}
    base_X=np.column_stack([np.ones(len(raw)),age,fixed_effects])
    base_beta,base_pred,base_metrics=fit_design(base_X)
    context_features=[]
    for name,key in (("track_temperature_c","track_temp"),("air_temperature_c","air_temp"),("rain_indicator","rain")):
        values=np.array([r[key] for r in raw],dtype=float)
        if np.isfinite(values).all() and np.ptp(values)>0:
            context_features.append((name,values))
    context_X=np.column_stack([base_X]+[v for _,v in context_features])
    context_beta,context_pred,context_metrics=fit_design(context_X)
    # One-breakpoint hinge model is a lightweight piecewise-regression comparator.
    piecewise=None
    candidates=[v for v in sorted(set(age.tolist())) if np.sum(age<=v)>=3 and np.sum(age>v)>=3]
    if candidates:
        best=None
        for cp in candidates:
            X=np.column_stack([context_X,np.maximum(0.0,age-cp)])
            beta,pred,metrics_=fit_design(X)
            if best is None or metrics_["bic"]<best["metrics"]["bic"]:
                best={"cp":cp,"beta":beta,"metrics":metrics_}
        if best:
            beta=best["beta"]
            piecewise={"breakpoint_tyre_age_laps":float(best["cp"]),
                       "pre_break_slope_s_per_lap":round(float(beta[1]),5),
                       "post_break_slope_s_per_lap":round(float(beta[1]+beta[-1]),5),
                       **best["metrics"]}
    weather_coeffs={}
    if context_features:
        weather_coeffs={name:round(float(coef),5) for (name,_),coef in zip(context_features,context_beta[-len(context_features):])}
    return {"ready":True,"laps_used":len(raw),"laps_excluded":len(excluded),"excluded":excluded,
            "baseline_age_only":{"age_slope_s_per_lap":round(float(base_beta[1]),5),**base_metrics},
            "context_adjusted":{"age_slope_s_per_lap":round(float(context_beta[1]),5),
                                 "weather_coefficients":weather_coeffs,**context_metrics},
            "piecewise_model":piecewise,
            "model_comparison":{"baseline_bic":base_metrics["bic"],"context_bic":context_metrics["bic"],
                                 "piecewise_bic":piecewise["bic"] if piecewise else None,
                                 "selection_rule":"Lower BIC preferred among fitted descriptive models; in-sample model selection is exploratory, not a validation score."},
            "features_used":["tyre_age_laps","stint_fixed_effects"]+[name for name,_ in context_features],
            "compounds":sorted({r["compound"] for r in raw}),"stints":stint_ids,
            "limitations":"Observational within-session model. Stint fixed effects account for baseline differences between stints but not all compound, fuel, traffic or setup effects. Nearest weather samples and race-control message text are imperfect proxies; fuel load, traffic, tyre temperatures, setup and driver management are not fully observed. Coefficients are associations, not causal tyre-wear rates. Piecewise breakpoint selection is exploratory and must be tested on held-out races."}
