from app.analytics.debrief import extract_lap_trace, normalize_trace, detect_corner_windows, build_comparison


def sample_laps():
    return [
        {'lap_number': 1, 'date_start': '2024-03-02T10:00:00Z', 'lap_duration': 10.0, 'is_pit_out_lap': False},
        {'lap_number': 2, 'date_start': '2024-03-02T10:00:12Z', 'lap_duration': 9.6, 'is_pit_out_lap': False},
    ]


def make_car_row(sec, speed, throttle, brake, rpm=12000, gear=6):
    return {'date': f'2024-03-02T10:00:{sec:05.2f}Z'.replace('Z.','.'), 'speed': speed, 'throttle': throttle, 'brake': brake, 'rpm': rpm, 'n_gear': gear}


def sample_car_a():
    rows=[]
    seq=[(0,260,100,0,12500,8),(1,250,80,0,12200,8),(2,210,10,100,11800,7),(3,160,0,100,11000,5),(4,145,5,60,10500,4),(5,150,20,20,10800,4),(6,180,60,0,11200,5),(7,210,90,0,11800,6),(8,240,100,0,12300,7),(9,260,100,0,12500,8)]
    for t,s,th,b,r,g in seq:
        rows.append({'date': f'2024-03-02T10:00:0{t}Z', 'speed': s, 'throttle': th, 'brake': b, 'rpm': r, 'n_gear': g})
    for t,s,th,b,r,g in [(12,258,100,0,12400,8),(13,248,80,0,12100,8),(14,208,15,100,11700,7),(15,158,0,100,10900,5),(16,140,5,60,10300,4),(17,148,20,20,10700,4),(18,170,55,0,11100,5),(19,198,85,0,11600,6),(20,228,100,0,12100,7),(21,250,100,0,12400,8)]:
        rows.append({'date': f'2024-03-02T10:00:{t}Z', 'speed': s, 'throttle': th, 'brake': b, 'rpm': r, 'n_gear': g})
    return rows


def sample_car_b():
    rows=[]
    for t,s,th,b,r,g in [(0,255,100,0,12400,8),(1,245,75,0,12100,8),(2,200,5,100,11600,7),(3,150,0,100,10800,5),(4,132,0,70,10200,4),(5,136,10,35,10400,4),(6,160,35,0,10800,5),(7,192,72,0,11300,6),(8,220,100,0,11900,7),(9,245,100,0,12300,8)]:
        rows.append({'date': f'2024-03-02T10:00:0{t}Z', 'speed': s, 'throttle': th, 'brake': b, 'rpm': r, 'n_gear': g})
    return rows


def test_extract_and_normalize_trace():
    trace = extract_lap_trace(sample_car_a(), sample_laps(), lap_number=1)
    assert trace['lap_number'] == 1
    assert trace['lap_time_s'] == 10.0
    assert trace['total_distance_m'] > 0
    norm = normalize_trace(trace)
    assert len(norm['aligned_points']) == 241
    assert norm['aligned_points'][0]['progress_pct'] == 0.0
    assert norm['aligned_points'][-1]['progress_pct'] == 100.0


def test_corner_detection_and_comparison_summary():
    primary = extract_lap_trace(sample_car_a(), sample_laps(), lap_number=1)
    compare = extract_lap_trace(sample_car_b(), sample_laps(), lap_number=1)
    norm = normalize_trace(primary)
    zones = detect_corner_windows(norm['aligned_points'])
    assert zones, 'expected at least one braking/corner zone'
    result = build_comparison(primary, compare, 'Driver A', 'Driver B')
    assert result['trace']
    assert 'Lap-time delta' in result['overall_summary']
    assert result['corner_comparisons']
    assert 'gains' in result['corner_comparisons'][0]['summary']
