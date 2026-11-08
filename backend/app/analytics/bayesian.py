"""Conjugate Bayesian within-stint age regression with explicit weak priors."""
import numpy as np


def bayesian_tyre_model(laps, stints, draws=4000, seed=42):
    """Fit y = stint intercept + beta*tyre_age + noise with Normal-Inverse-Gamma prior.
    A shared slope is an association, NOT causal physical tyre wear. Excludes pit-out laps;
    no race-control/weather correction here. For clean contextual filtering use existing analysis.
    """
    lookup = {}
    for s in stints:
        try:
            for n in range(int(s["lap_start"]), int(s["lap_end"])+1): lookup[n] = s
        except (KeyError, ValueError, TypeError): continue
    rows = []
    for lap in laps:
        try:
            n = int(lap["lap_number"]); duration = float(lap["lap_duration"])
            if n not in lookup or duration <= 0 or duration > 300 or lap.get("is_pit_out_lap"): continue
            s = lookup[n]
            rows.append((n-int(s["lap_start"]), duration, int(s.get("stint_number", 0))))
        except (KeyError, ValueError, TypeError): continue
    if len(rows) < 12 or len({r[0] for r in rows}) < 4:
        return {"ready": False, "observations": len(rows), "message": "Need at least 12 observed laps and four tyre ages; unavailable otherwise."}
    ids = sorted({r[2] for r in rows}); y = np.array([r[1] for r in rows]); age = np.array([r[0] for r in rows], dtype=float)
    # Intercept + slope + stint offsets, weak regularizing prior on coefficients.
    X = np.column_stack([np.ones(len(rows)), age] + [[float(r[2] == sid) for r in rows] for sid in ids[1:]])
    k = X.shape[1]
    m0 = np.array([float(np.median(y)), 0.] + [0.]*(k-2))
    prior_precision = np.diag([1/100**2, 1/0.5**2] + [1/10**2]*(k-2))
    a0, b0 = 2., 1.  # sigma^2 ~ InvGamma(2,1) seconds^2
    precision = prior_precision + X.T@X
    covariance = np.linalg.inv(precision)
    mn = covariance@(prior_precision@m0 + X.T@y)
    an = a0 + len(y)/2
    bn = max(1e-9, b0 + 0.5*(y@y + m0@prior_precision@m0 - mn@precision@mn))
    rng = np.random.default_rng(seed)
    sigma2 = 1/rng.gamma(an, scale=1/bn, size=draws)
    slopes = mn[1] + rng.standard_normal(draws)*np.sqrt(sigma2*covariance[1,1])
    return {"ready": True, "observations": len(rows), "stints": len(ids), "posterior_mean_s_per_lap": float(np.mean(slopes)),
            "credible_interval_95_s_per_lap": [float(v) for v in np.quantile(slopes, [.025,.975])],
            "probability_positive_slope": float(np.mean(slopes>0)), "seed": seed, "posterior_draws": draws,
            "prior": {"slope_mean_s_per_lap": 0., "slope_std_scale": 0.5,
                      "residual_variance_inverse_gamma_shape": a0, "residual_variance_inverse_gamma_scale": b0},
            "limitations": "Bayesian pooled linear association with stint offsets and weak stated priors. Not a dynamic state-space model. Does not correct for safety cars, fuel, weather or compound; not validated across races."}
