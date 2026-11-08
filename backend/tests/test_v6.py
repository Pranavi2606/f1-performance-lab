import numpy as np
import pytest
from app.analytics.advanced import _kalman, state_space_stints
from app.analytics.evaluation import calibration_report

def test_forward_filter_future_invariance():
    y=np.array([90.,90.2,90.1,90.3,90.5,90.8,91.])
    changed=y.copy();changed[-2:]+=30
    _,a,_=_kalman(y,0.001,0.2,mode='filter')
    _,b,_=_kalman(changed,0.001,0.2,mode='filter')
    assert np.allclose(a[:-2],b[:-2])
    _,sa,_=_kalman(y,0.001,0.2,mode='smooth')
    _,sb,_=_kalman(changed,0.001,0.2,mode='smooth')
    assert not np.allclose(sa[:-2],sb[:-2])

def test_filter_rejects_test_stint_tuning():
    points=[{'stint':'1','age':i,'lap_time':90+i*.1} for i in range(10)]
    with pytest.raises(ValueError,match='pre-specified'):
        state_space_stints(points,mode='filter')
    assert state_space_stints(points,mode='filter',process_variance=.001,measurement_variance=.2)['ready']

def test_calibration_reproducible():
    a=calibration_report(100,42,'stable'); b=calibration_report(100,42,'stable')
    assert a==b
    assert sum(a['posterior_slope_cdf_rank_histogram_10_bins'])==100
    assert a['source']=='synthetic_only'

def test_bad_mode():
    with pytest.raises(ValueError): _kalman(np.array([1.,2.]),.1,.2,mode='forecast')
