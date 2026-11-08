from app.analytics.degradation import analyze_stints
from app.analytics.debrief import extract_lap_trace, choose_lap
from app.api.analytics import driver_laps
from unittest.mock import patch


def test_stint_intercept_required_for_frontend_regression():
    laps=[{'lap_number':i,'lap_duration':90.0+0.2*i,'is_pit_out_lap':False} for i in range(1,11)]
    stints=[{'stint_number':1,'lap_start':1,'lap_end':10,'compound':'MEDIUM'}]
    result=analyze_stints(laps,stints)
    assert result['stints']
    s=result['stints'][0]
    assert isinstance(s['intercept'],float)
    assert abs((s['intercept']+s['degradationRate']*5)-91.0)<1e-5


def test_lap_listing_uses_real_stint_compound():
    laps=[{'lap_number':7,'lap_duration':92.5,'date_start':'2024-01-01T00:00:00Z'},
          {'lap_number':8,'lap_duration':93.5,'is_pit_out_lap':True,'date_start':'2024-01-01T00:01:32Z'}]
    stints=[{'lap_start':4,'lap_end':10,'compound':'HARD','stint_number':2}]
    with patch('app.api.analytics.jolpica.get_schedule',return_value=[{'round':1,'date':'2024-03-02'}]),\
         patch('app.api.analytics.openf1.resolve_race_session',return_value={'session_key':9472}),\
         patch('app.api.analytics.openf1.get_laps',return_value=laps),\
         patch('app.api.analytics.openf1.get_stints',return_value=stints):
        result=driver_laps(2024,1,1)
    assert result['laps']==[{'lap_number':7,'duration_s':92.5,'compound':'HARD','stint':2,'tyre_age_at_start':None}]
