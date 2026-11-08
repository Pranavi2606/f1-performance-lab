import numpy as np
from app.analytics.advanced import observed_stint_points,state_space_stints,compare_stint_models
from app.analytics.validation import audit_telemetry_ranges,audit_lap_set_consistency
from app.analytics.composition import compose_public_data_report


def fixture():
    laps=[{'lap_number':i,'lap_duration':90+.08*(i-1)+.01*np.sin(i),
           'date_start':f'2026-01-01T00:{i:02d}:00+00:00'} for i in range(1,21)]
    stints=[{'lap_start':1,'lap_end':20,'stint_number':1,'compound':'MEDIUM'}]
    return laps,stints


def test_state_space_and_benchmark():
    laps,stints=fixture();pts=observed_stint_points(laps,stints)
    smoother=state_space_stints(pts)
    assert smoother['ready'] and len(smoother['stints'][0]['latent_slope_s_per_lap'])==20
    benchmark=compare_stint_models(pts)
    assert benchmark['ready']
    assert benchmark['folds'][0]['models']['ols']['mae_s']<.1


def test_quality_and_lap_consistency():
    laps,stints=fixture()
    audit=audit_telemetry_ranges([{'speed':900,'throttle':-2,'brake':1,'rpm':10000,'n_gear':3}])
    assert audit['sanity_range_violations']['speed']==1
    assert audit['sanity_range_violations']['throttle']==1
    consistency=audit_lap_set_consistency(laps,stints,[])
    assert consistency['observed_laps_without_stint']==[]
    assert consistency['lap_windows_with_car_samples']==0


def test_no_fabrication_and_composition():
    laps,stints=fixture()
    report=compose_public_data_report(laps,stints,scenario={'race_laps':20,'base_lap_s':90,
        'pit_loss_s':20,'stops':[10],'use_bayesian_tyre_slope':True})
    assert report['scenario']['ready']
    assert report['scenario']['tyre_slope_provenance']=='bayesian_posterior_mean_estimate'
    assert report['proprietary_inputs']['ers_commands']['status']=='unavailable'
    assert report['physics_vehicle_twin']['status']=='unavailable'
    assert compose_public_data_report([],[],scenario={'use_bayesian_tyre_slope':True})['scenario']['status']=='unavailable'


def test_missing_age_rejected_not_interpolated():
    points=[{'stint':'1','age':i,'lap_time':90+.1*i} for i in [0,1,2,3,4,6,7,8]]
    result=state_space_stints(points)
    assert not result['ready']
    assert 'Missing tyre-age steps' in result['stints'][0]['reason']
