"""Reproducible synthetic uncertainty audits; never label synthetic checks real-world validation."""
import math
import numpy as np
from scipy.stats import t as student_t


def generate_synthetic_stint(rng, scenario="stable", n=24):
    """Known ground truth; all parameters are synthetic, not F1 measured coefficients."""
    if scenario not in ("stable", "high_deg", "cliff"):
        raise ValueError("Unknown scenario")
    slope = {"stable": 0.015, "high_deg": 0.09, "cliff": 0.045}[scenario]
    age = np.arange(n, dtype=float)
    curve = np.maximum(age - 15, 0)**2 * 0.025 if scenario == "cliff" else 0
    y = 92.0 + slope*age + curve + rng.normal(0, 0.30, n)
    return age, y, slope


def _posterior(age, y):
    """Normal-Inverse-Gamma posterior for intercept+slope, proper weak prior."""
    X = np.column_stack((np.ones(len(age)), age))
    m0 = np.array([92., 0.]); precision0 = np.diag([1/100**2, 1/0.5**2])
    a0,b0 = 2.,1.
    precision = precision0 + X.T@X
    V = np.linalg.inv(precision)
    m = V@(precision0@m0 + X.T@y)
    an = a0 + len(y)/2
    bn = max(1e-12, b0 + 0.5*(y@y + m0@precision0@m0 - m@precision@m))
    scale = math.sqrt(bn/an * V[1,1])
    return float(m[1]), float(scale), float(2*an)


def calibration_report(synthetic_runs=500, seed=42, scenario="stable"):
    """Slope interval coverage and posterior-CDF ranks of known synthetic slopes.
    Ranks are a diagnostic, NOT a predictive PIT histogram; predictive PIT requires
    out-of-sample observed lap times and their predictive distributions.
    """
    if not 10 <= synthetic_runs <= 10000:
        raise ValueError("synthetic_runs must be between 10 and 10000")
    rng = np.random.default_rng(seed)
    covered=[]; widths=[]; ranks=[]
    for _ in range(synthetic_runs):
        x,y,truth=generate_synthetic_stint(rng,scenario)
        mean,scale,df=_posterior(x,y)
        lo,hi=student_t.ppf([.025,.975],df,loc=mean,scale=scale)
        covered.append(bool(lo<=truth<=hi));widths.append(float(hi-lo))
        ranks.append(float(student_t.cdf(truth,df,loc=mean,scale=scale)))
    rate=float(np.mean(covered)); se=math.sqrt(rate*(1-rate)/synthetic_runs)
    return {"source":"synthetic_only", "scenario":scenario,"runs":synthetic_runs,"seed":seed,
            "empirical_slope_coverage_95":rate,"coverage_mc_se":se,
            "mean_slope_interval_width_s_per_lap":float(np.mean(widths)),
            "posterior_slope_cdf_rank_histogram_10_bins":np.histogram(ranks,bins=np.linspace(0,1,11))[0].tolist(),
            "target":0.95,"interpretation":"Synthetic slope-interval coverage only; not real-race calibration. CDF ranks are not predictive PIT. Scenario mismatch (especially cliff) can reduce coverage."}
