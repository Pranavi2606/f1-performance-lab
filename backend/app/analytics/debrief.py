from __future__ import annotations
from datetime import datetime
from typing import Any
import math
import numpy as np


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def _f(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        return 100.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _valid_lap(lap: dict[str, Any]) -> bool:
    try:
        if lap.get('is_pit_out_lap') is True:
            return False
        d = _f(lap.get('lap_duration'), -1)
        return d > 0
    except Exception:
        return False


def choose_lap(laps: list[dict[str, Any]], lap_number: int | None = None) -> dict[str, Any]:
    valid = [lap for lap in laps if _valid_lap(lap)]
    if not valid:
        raise ValueError('No valid race laps available for comparison.')
    if lap_number is not None:
        chosen = next((lap for lap in valid if int(lap.get('lap_number', -1)) == lap_number), None)
        if not chosen:
            raise ValueError(f'Lap {lap_number} not found among valid laps.')
        return chosen
    return min(valid, key=lambda lap: _f(lap.get('lap_duration'), float('inf')))


def _interpolate_series(x: np.ndarray, y: np.ndarray, grid: np.ndarray) -> np.ndarray:
    if len(x) == 0:
        return np.zeros_like(grid)
    if len(x) == 1:
        return np.full_like(grid, float(y[0]), dtype=float)
    xs = np.array(x, dtype=float)
    ys = np.array(y, dtype=float)
    order = np.argsort(xs)
    xs, ys = xs[order], ys[order]
    uniq_idx = np.concatenate(([0], np.where(np.diff(xs) > 1e-9)[0] + 1))
    xs, ys = xs[uniq_idx], ys[uniq_idx]
    if len(xs) == 1:
        return np.full_like(grid, float(ys[0]), dtype=float)
    return np.interp(grid, xs, ys)


def extract_lap_trace(car_data: list[dict[str, Any]], laps: list[dict[str, Any]], lap_number: int | None = None) -> dict[str, Any]:
    lap = choose_lap(laps, lap_number)
    lap_no = int(lap.get('lap_number', 0))
    t0 = _time(lap['date_start'])
    duration = _f(lap.get('lap_duration'), 0.0)
    t1 = t0.timestamp() + duration
    rows = []
    for row in sorted((r for r in car_data if r.get('date')), key=lambda r: r['date']):
        try:
            ts = _time(row['date']).timestamp()
        except Exception:
            continue
        if t0.timestamp() <= ts <= t1 + 0.25:
            rows.append((ts, row))
    if len(rows) < 8:
        raise ValueError(f'Insufficient telemetry samples for lap {lap_no}.')
    distance = 0.0
    prev_t = None
    prev_speed_mps = None
    points = []
    for ts, row in rows:
        speed = _f(row.get('speed'))
        throttle = _f(row.get('throttle'))
        brake = _f(row.get('brake'))
        rpm = _f(row.get('rpm'))
        gear = _f(row.get('n_gear'))
        if prev_t is not None and prev_speed_mps is not None:
            dt = max(0.0, ts - prev_t)
            distance += max(0.0, (prev_speed_mps + speed / 3.6) * 0.5 * dt)
        prev_t = ts
        prev_speed_mps = speed / 3.6
        points.append({
            'elapsed_s': round(ts - t0.timestamp(), 3),
            'distance_m': round(distance, 3),
            'speed': round(speed, 3),
            'throttle': round(throttle, 3),
            'brake': round(brake, 3),
            'rpm': round(rpm, 3),
            'gear': int(round(gear)) if math.isfinite(gear) else 0,
        })
    total_dist = max(points[-1]['distance_m'], 1.0)
    for p in points:
        p['progress_pct'] = round(100.0 * p['distance_m'] / total_dist, 3)
    return {
        'lap_number': lap_no,
        'lap_time_s': round(duration, 3),
        'compound': lap.get('compound') or 'Unknown',
        'points': points,
        'total_distance_m': round(total_dist, 2),
    }


def normalize_trace(trace: dict[str, Any], grid_size: int = 241) -> dict[str, Any]:
    pts = trace['points']
    x = np.array([p['progress_pct'] for p in pts], dtype=float)
    grid = np.linspace(0.0, 100.0, grid_size)
    metrics = {}
    for key in ('elapsed_s', 'distance_m', 'speed', 'throttle', 'brake', 'rpm', 'gear'):
        y = np.array([p[key] for p in pts], dtype=float)
        values = _interpolate_series(x, y, grid)
        if key == 'gear':
            values = np.rint(values)
        metrics[key] = values
    rows = []
    for i, pct in enumerate(grid):
        rows.append({
            'progress_pct': round(float(pct), 2),
            'elapsed_s': round(float(metrics['elapsed_s'][i]), 3),
            'distance_m': round(float(metrics['distance_m'][i]), 2),
            'speed': round(float(metrics['speed'][i]), 3),
            'throttle': round(float(metrics['throttle'][i]), 3),
            'brake': round(float(metrics['brake'][i]), 3),
            'rpm': round(float(metrics['rpm'][i]), 1),
            'gear': int(metrics['gear'][i]),
        })
    return {
        **trace,
        'aligned_points': rows,
    }


def detect_corner_windows(aligned_points: list[dict[str, Any]]) -> list[dict[str, float]]:
    if not aligned_points:
        return []
    brake = np.array([p['brake'] for p in aligned_points], dtype=float)
    throttle = np.array([p['throttle'] for p in aligned_points], dtype=float)
    speed = np.array([p['speed'] for p in aligned_points], dtype=float)
    pct = np.array([p['progress_pct'] for p in aligned_points], dtype=float)
    active = brake > 5.0
    zones: list[dict[str, float]] = []
    i = 1
    while i < len(active):
        if not active[i] or active[i-1]:
            i += 1
            continue
        start = i
        j = i
        while j + 1 < len(active) and (active[j + 1] or throttle[j + 1] < 25.0):
            j += 1
            if j - start > 40:
                break
        end = min(j + 5, len(active) - 1)
        span = pct[end] - pct[start]
        if span < 1.0:
            i = j + 1
            continue
        k = start + int(np.argmin(speed[start:end + 1]))
        # throttle pickup after apex
        after = np.where(throttle[k:end + 1] >= 50.0)[0]
        pickup = int(k + after[0]) if len(after) else end
        zones.append({
            'start_idx': start,
            'apex_idx': k,
            'end_idx': end,
            'brake_on_pct': float(pct[start]),
            'apex_pct': float(pct[k]),
            'brake_release_pct': float(pct[min(j, len(pct)-1)]),
            'throttle_pickup_pct': float(pct[pickup]),
            'end_pct': float(pct[end]),
        })
        i = end + 1
    # fallback: use strongest local speed minima if no explicit brake zones
    if not zones and len(speed) > 10:
        minima = []
        for i in range(3, len(speed)-3):
            if speed[i] <= min(speed[i-3:i+4]):
                minima.append((speed[i], i))
        minima.sort(key=lambda x: x[0])
        for _, idx in minima[:4]:
            start = max(0, idx-6); end = min(len(speed)-1, idx+8)
            zones.append({
                'start_idx': start, 'apex_idx': idx, 'end_idx': end,
                'brake_on_pct': float(pct[start]), 'apex_pct': float(pct[idx]),
                'brake_release_pct': float(pct[idx]), 'throttle_pickup_pct': float(pct[min(end, idx+3)]),
                'end_pct': float(pct[end]),
            })
    # de-duplicate overlapping zones and limit count
    merged = []
    for z in sorted(zones, key=lambda z: z['start_idx']):
        if not merged or z['start_idx'] > merged[-1]['end_idx']:
            merged.append(z)
        elif (z['end_idx'] - z['start_idx']) > (merged[-1]['end_idx'] - merged[-1]['start_idx']):
            merged[-1] = z
    return merged[:6]


def zone_metrics(aligned_points: list[dict[str, Any]], zone: dict[str, float]) -> dict[str, float]:
    start, apex, end = int(zone['start_idx']), int(zone['apex_idx']), int(zone['end_idx'])
    pts = aligned_points
    seg = pts[start:end+1]
    speeds = [p['speed'] for p in seg]
    brakes = [p['brake'] for p in seg]
    throttles = [p['throttle'] for p in seg]
    elapsed = [p['elapsed_s'] for p in seg]
    start_t = pts[start]['elapsed_s']; end_t = pts[end]['elapsed_s']
    brake_on = next((p['progress_pct'] for p in seg if p['brake'] > 5), pts[start]['progress_pct'])
    brake_rel = next((p['progress_pct'] for p in reversed(seg) if p['brake'] > 5), pts[apex]['progress_pct'])
    pickup = next((p['progress_pct'] for p in seg[max(0, apex-start):] if p['throttle'] >= 50), pts[end]['progress_pct'])
    return {
        'entry_speed_kph': round(float(pts[start]['speed']), 2),
        'min_speed_kph': round(float(min(speeds)), 2),
        'exit_speed_kph': round(float(pts[end]['speed']), 2),
        'avg_throttle_pct': round(float(np.mean(throttles)), 2),
        'brake_active_pct': round(float(np.mean([b > 5 for b in brakes]) * 100.0), 1),
        'brake_on_pct': round(float(brake_on), 2),
        'brake_release_pct': round(float(brake_rel), 2),
        'throttle_pickup_pct': round(float(pickup), 2),
        'segment_time_s': round(float(end_t - start_t), 3),
    }


def summarize_corner(reference_name: str, compare_name: str, ref_metrics: dict[str, float], cmp_metrics: dict[str, float], delta_time_compare_minus_ref: float) -> str:
    """Report descriptive differences only; public channels cannot establish causal balance."""
    if abs(delta_time_compare_minus_ref) < 0.0005:
        headline = 'Similar approximate segment times'
    else:
        faster = reference_name if delta_time_compare_minus_ref > 0 else compare_name
        slower = compare_name if faster == reference_name else reference_name
        headline = f'{faster} gains {abs(delta_time_compare_minus_ref):.3f}s over {slower} in this aligned window'
    changes=[]
    min_diff=cmp_metrics['min_speed_kph']-ref_metrics['min_speed_kph']
    exit_diff=cmp_metrics['exit_speed_kph']-ref_metrics['exit_speed_kph']
    brake_diff=cmp_metrics['brake_release_pct']-ref_metrics['brake_release_pct']
    throttle_diff=cmp_metrics['throttle_pickup_pct']-ref_metrics['throttle_pickup_pct']
    if abs(min_diff)>=2:
        changes.append(f'{compare_name} minimum speed {min_diff:+.1f} km/h versus {reference_name}')
    if abs(exit_diff)>=3:
        changes.append(f'{compare_name} exit speed {exit_diff:+.1f} km/h versus {reference_name}')
    if abs(brake_diff)>=.5:
        changes.append(f'brake release relative progress {brake_diff:+.1f}% of lap')
    if abs(throttle_diff)>=.5:
        changes.append(f'throttle pickup relative progress {throttle_diff:+.1f}% of lap')
    if not changes:
        return headline + '. No large control-channel differences detected at this resolution; no causal explanation inferred.'
    return headline + '. Observed differences: ' + '; '.join(changes[:2]) + '. These do not prove the cause.'


def build_comparison(primary_trace: dict[str, Any], compare_trace: dict[str, Any], primary_name: str, compare_name: str, compare_driver_number: int | None = None) -> dict[str, Any]:
    ref = normalize_trace(primary_trace)
    cmp = normalize_trace(compare_trace)
    trace = []
    cpoints = cmp['aligned_points']
    rpoints = ref['aligned_points']
    n = min(len(rpoints), len(cpoints))
    for i in range(n):
        trace.append({
            'progress_pct': rpoints[i]['progress_pct'],
            'primary_speed': rpoints[i]['speed'],
            'compare_speed': cpoints[i]['speed'],
            'primary_throttle': rpoints[i]['throttle'],
            'compare_throttle': cpoints[i]['throttle'],
            'primary_brake': rpoints[i]['brake'],
            'compare_brake': cpoints[i]['brake'],
            'primary_rpm': rpoints[i]['rpm'],
            'compare_rpm': cpoints[i]['rpm'],
            'primary_gear': rpoints[i]['gear'],
            'compare_gear': cpoints[i]['gear'],
            'delta_time_s': round(cpoints[i]['elapsed_s'] - rpoints[i]['elapsed_s'], 4),
        })
    zones = detect_corner_windows(ref['aligned_points'])
    corners = []
    for idx, zone in enumerate(zones, start=1):
        ref_m = zone_metrics(ref['aligned_points'], zone)
        cmp_m = zone_metrics(cmp['aligned_points'], zone)
        start_idx = int(zone['start_idx']); end_idx = int(zone['end_idx'])
        delta = trace[end_idx]['delta_time_s'] - trace[start_idx]['delta_time_s']
        corners.append({
            'corner_like_segment': idx,
            'window_pct': [round(zone['brake_on_pct'], 2), round(zone['end_pct'], 2)],
            'primary': ref_m,
            'compare': cmp_m,
            'compare_minus_primary_time_s': round(float(delta), 4),
            'summary': summarize_corner(primary_name, compare_name, ref_m, cmp_m, float(delta)),
        })
    overall_delta = compare_trace['lap_time_s'] - primary_trace['lap_time_s']
    return {
        'compare_driver': compare_name,
        'compare_driver_number': compare_driver_number,
        'compare_lap_number': compare_trace['lap_number'],
        'compare_lap_time_s': compare_trace['lap_time_s'],
        'compare_compound': compare_trace['compound'],
        'lap_delta_s': round(overall_delta, 3),
        'trace': trace,
        'corner_comparisons': corners,
        'overall_summary': f"{primary_name} lap {primary_trace['lap_number']} vs {compare_name} lap {compare_trace['lap_number']}. Lap-time delta = {overall_delta:+.3f}s (compare minus primary). Negative means the comparison lap is faster.",
    }


def build_driver_debrief(primary_driver: dict[str, Any], primary_laps: list[dict[str, Any]], primary_car: list[dict[str, Any]],
                         comparison_payloads: list[dict[str, Any]], primary_lap_number: int | None = None) -> dict[str, Any]:
    primary_trace = extract_lap_trace(primary_car, primary_laps, primary_lap_number)
    primary_name = primary_driver.get('full_name') or str(primary_driver.get('driver_number'))
    comparisons = []
    for payload in comparison_payloads:
        compare_trace = extract_lap_trace(payload['car'], payload['laps'], payload.get('lap_number'))
        comparisons.append(build_comparison(primary_trace, compare_trace, primary_name, payload['driver'].get('full_name') or str(payload['driver'].get('driver_number')), int(payload['driver'].get('driver_number', 0))))
    return {
        'primary_driver': {
            'driver_number': int(primary_driver.get('driver_number', 0)),
            'full_name': primary_name,
            'team_name': primary_driver.get('team_name', ''),
            'lap_number': primary_trace['lap_number'],
            'lap_time_s': primary_trace['lap_time_s'],
            'compound': primary_trace['compound'],
        },
        'comparisons': comparisons,
        'steering_trace': {
            'status': 'unavailable',
            'reason': 'OpenF1 public car telemetry does not expose steering angle. Add an external computer-vision estimate if you want an experimental steering channel.'
        },
        'method': 'Per-lap telemetry aligned by normalized lap progress using fastest valid lap by default. Corner-like windows are derived from braking/throttle patterns on the primary lap and are intended for driver debrief, not official track-corner IDs.',
        'limitations': 'Brake is a public telemetry proxy, not full brake pressure. Steering, slip angle, tyre state and direct oversteer/understeer channels are unavailable in public OpenF1 data. Delta traces are approximate and aligned by normalized progress, not proprietary track-position synchronization.',
    }
