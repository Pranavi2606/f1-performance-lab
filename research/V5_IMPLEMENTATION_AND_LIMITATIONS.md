# Research Upgrade v5 — implementation and limitations

## New code

- `backend/app/analytics/advanced.py`: observed per-stint point preparation, three-state local-quadratic Kalman filter and RTS smoother, discrete likelihood hyperparameter selection, and chronological within-stint median/OLS/piecewise-BIC/Bayesian-mean benchmark on the same observed points.
- `backend/app/analytics/validation.py`: added heuristic channel sanity ranges and lap/stint/car-sample timestamp-window coverage checks.
- `backend/app/analytics/composition.py`: auditable composition of coverage, model fits, benchmarking and optional timing scenarios. Proprietary inputs are explicitly `unavailable`.
- `backend/app/api/lab.py`: `POST /api/lab/composition` with supplied observations; `POST /api/lab/composition-live` with OpenF1 session key, driver number, optional telemetry and scenario. Live endpoint requires public network access and can fail/rate-limit.
- `backend/tests/test_v5.py`: synthetic deterministic tests, including no-fabrication checks.

## Correct technical interpretations

The 3-state filter uses pace level, slope and curvature; curvature must **not** be called a demonstrated tyre cliff. The smoother is retrospective and not suitable for out-of-sample scoring without a separate forward-filter forecasting implementation. Discrete process/measurement variance selection uses in-sample maximum likelihood. Approximate 95% state intervals are Gaussian model-based intervals, not empirically calibrated coverage claims.

The benchmark tests held-out final laps *within stints*, not leave-one-race-out. It compares median, OLS, piecewise BIC and Bayesian posterior mean on the same training/test split. Existing `/api/lab/historical-evaluation` provides a separate cross-event linear baseline. It does **not** establish cross-event Bayesian/state-space superiority. Bayesian credible-interval calibration is not implemented: measuring coverage against a noisy test-set slope is not sufficient to establish calibration.

The scenario harness can consume the Bayesian posterior **mean** as the tyre coefficient. It does not propagate Bayesian parameter draws or connect to an observed ERS state; race-time scenario bands include only user-selected independent Gaussian noise. Energy-to-lap-time physics and a full vehicle digital twin are **not implemented**.

`speed`, `rpm`, throttle, brake and gear range checks are conservative heuristic data sanity checks, not FIA regulation limits. Car data is associated with laps using observed timestamps; feed timestamp synchronization is not independently proven.

## Validation status

Tests are synthetic/unit checks, not live 2025/2026 event validation. Frontend production build is not guaranteed by backend tests. Public telemetry can be missing or rate-limited. Never present a synthetic test as a real race finding.

## Example API request

`POST /api/lab/composition-live`

```json
{"session_key": 9158, "driver_number": 1, "include_telemetry": false}
```

The session key is an illustrative API request parameter, **not a verified race session**. Discover actual session keys from OpenF1 first.
