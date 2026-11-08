import importlib.util
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"generate_engineering_brief.py"
spec=importlib.util.spec_from_file_location("engineering_brief", SCRIPT)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_missing_prediction_metrics_never_fabricated():
    data={"source":"OpenF1","year":2024,"driver":1,"events":[{"circuit":"Monaco","status":"computed","session_key":9523,"n_laps":75,"slope":-0.1,"ci95":[-0.14,-0.06]}]}
    report=module.render_brief(data)
    assert "No out-of-sample prediction metrics" in report
    assert "-0.1000" in report
    assert "unavailable (older benchmark JSON" in report


def test_pooled_error_aggregation():
    data={"source":"OpenF1","events":[{"circuit":"Bahrain","status":"computed","predictive_benchmark":{"ready":True,"folds":[{"test_laps":2,"models":{"ols":{"mae_s":1,"rmse_s":2}}},{"test_laps":6,"models":{"ols":{"mae_s":3,"rmse_s":4}}}]}}]}
    report=module.render_brief(data)
    assert "| Bahrain | ols | 8 | 2.500 | 3.606 |" in report


def test_reject_unattributed_data():
    try:
        module.render_brief({"source":"synthetic","events":[{}]})
    except ValueError:
        pass
    else:
        raise AssertionError("Must reject non-OpenF1-labelled inputs")
