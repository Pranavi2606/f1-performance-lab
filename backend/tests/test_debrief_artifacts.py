from datetime import datetime,timedelta,timezone
from io import BytesIO
from app.analytics.debrief_artifacts import map_for_lap, render_markdown,render_pdf


def test_location_map_has_inferred_markers():
    start=datetime(2024,3,1,14,0,0,tzinfo=timezone.utc)
    lap={'date_start':start.isoformat(),'lap_duration':80.0,'lap_number':4}
    locations=[]
    for i in range(80):
        t=start+timedelta(seconds=i)
        locations.append({'date':t.isoformat(),'x':i,'y': i*i/100})
    result=map_for_lap(locations,lap,[[10,20],[50,60]])
    assert result['ready'] is True
    assert len(result['markers']) == 2
    assert all(marker['origin']=='inferred_braking_zone' for marker in result['markers'])
    assert all(0<=p['progress_pct']<=100 for p in result['points'])


def test_unavailable_if_location_missing():
    lap={'date_start':'2024-03-01T14:00:00+00:00','lap_duration':80.0,'lap_number':2}
    assert not map_for_lap([],lap)['ready']


def test_pdf_and_markdown_have_explicit_limitations():
    payload={'year':2024,'round':1,'race_name':'Bahrain Grand Prix','session_key':9472,
             'primary_driver':{'full_name':'Driver A','lap_number':5,'lap_time_s':89.0},
             'comparisons':[{'compare_driver':'Driver B','compare_lap_number':6,'compare_lap_time_s':89.5,
                             'lap_delta_s':0.5,'overall_summary':'A was faster.',
                             'corner_comparisons':[{'corner_like_segment':1,'compare_minus_primary_time_s':0.05,
                                                    'summary':'A was faster near braking point.'}]}],
             'limitations':'No measured steering or actual oversteer diagnostic.'}
    md=render_markdown(payload)
    assert 'Driver B' in md and 'NOT' not in md and 'not official FIA' in md
    pdf=render_pdf(payload)
    assert pdf.startswith(b'%PDF') and len(pdf)>1000
