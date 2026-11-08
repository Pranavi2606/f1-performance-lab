## V10 driver-performance additions

**NEW — Driver Debrief sidebar:** choose a reference driver and compare one or several race drivers, view five car traces and approximate cumulative delta, view track XY map with inferred braking-zone markers, export an engineering report as Markdown or PDF, and optionally view an experimental camera-derived wheel-rotation CSV (rights-cleared video required). See [V10 guide](research/V10_DRIVER_DEBRIEF_GUIDE.md). This is *not official steering data*, and oversteer cannot be diagnosed from these public channels.

# F1 Race Decision Intelligence — Performance Lab

A React + TypeScript + FastAPI research application for reproducible analysis of public Formula One data. Independent educational project; not affiliated with F1, FIA, FOM or any team.

## Six screens

1. **Race Results** — Jolpica calendar and classification, with 2022–2026 selectable; upstream publication determines what is actually returned.
2. **Stint Analysis** — OpenF1 lap/stint data, robust lap cleaning, per-stint linear lap-time trend, R², sample count and exclusion audit. Performance Discovery also compares age-only and context-adjusted OLS using available weather and race-control observations.
3. **Strategy Insights** — classification-derived grid-to-finish movement. This is descriptive and does not claim causal strategy attribution.
4. **Energy Management** — interactive power × time calculator, versioned FIA regulation context and an illustrative one-stop/two-stop scenario search. It does not reconstruct actual battery state or ERS deployment.
5. **Performance Discovery** — energy acceleration fingerprints (not ERS), context-aware tyre analysis, XY-curvature-derived corner-like exit repeatability, normalized-segment fallback and a Random Forest lap-time baseline with chronological holdout and median baseline comparison.
6. **Telemetry Lab** — OpenF1 speed, throttle and brake traces; distance estimated by integrating timestamped speed samples.

## Data coverage

- Jolpica provides historical and current-season calendar/classification endpoints where records have been published.
- OpenF1 historical coverage begins in 2023. Therefore 2022 is supported for classification but telemetry-derived analyses are unavailable.
- 2025/2026 event availability depends on completed sessions and upstream publication. A scheduled event is not proof that its race results or telemetry are available.
- OpenF1's public car data includes channels such as speed, throttle, brake, RPM and gear. It does not expose verified proprietary battery state-of-charge or a complete team ERS deployment command.
- 2026 energy parameters are event/session dependent. Read `research/RESEARCH_PROTOCOL.md`; the calculator is dimensional arithmetic only.

## Research documentation

- `research/RESEARCH_PROTOCOL.md` — research questions, hypotheses, methodology, rejection criteria, limitations, regulatory context and references.
- `research/SOURCE_REGISTER.md` — source provenance, authority and coverage caveats.

The research report is a protocol, not a fabricated results paper. Empirical findings must be added only after a real event dataset has been retrieved, quality-checked and analysed.

## Run on Windows

### Backend — PowerShell terminal 1

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend — PowerShell terminal 2

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. API health: http://localhost:8000/api/health. Interactive API docs: http://localhost:8000/docs.

Use Node.js 22 LTS or 24 LTS. If `npm -v` fails before installation, repair the Node/npm installation first; that is separate from this project's code.

## Tests

From the `backend` directory:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
```

## Known limitations

- Telemetry-derived analysis is unavailable for 2022 because OpenF1's historical coverage begins in 2023.
- The tyre context model compares age-only OLS, weather-adjusted OLS with stint fixed effects, and an exploratory single-breakpoint piecewise model selected by BIC. Safety-car/yellow/red-flag laps are excluded where race-control messages permit. Fuel load, traffic, tyre temperatures, setup and driver management remain unobserved; coefficients are associations, not causal tyre-wear rates. Piecewise model selection is in-sample and requires held-out-race validation.
- The lap-time ML baseline uses a chronological within-session holdout and a training-median baseline, but still does not establish cross-race or cross-season generalisation.
- Integrated distance is approximate and sensitive to timestamp gaps and downsampling.
- Public telemetry cannot establish actual battery state-of-charge or team energy deployment.
- API errors and missing data should be shown as unavailable; never substitute mock metrics in a live analysis view.

## Primary sources

- Jolpica API: https://github.com/jolpica/jolpica-f1
- Jolpica results endpoint docs: https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/results.md
- OpenF1 docs: https://openf1.org/docs/
- OpenF1 overview, coverage, terms and rate limits: https://openf1.org/
- FIA 2026 Technical Regulations, Section C, Issue 21 (19 Oct 2026): https://www.fia.com/system/files/documents/fia_2026_f1_regulations_-_section_c_technical_-_iss_21_-_2026-10-19.pdf
- FIA 2026 regulation refinements: https://api.fia.com/news/refinements-2026-fia-formula-1-regulations-agreed-all-stakeholders
- Formula1.com 2026 regulation refinements: https://www.formula1.com/en/latest/article/refinements-to-2026-f1-regulations-agreed-by-all-stakeholders.1xA0TRau0DvyId6R7oZjFv.1xA0TRau0DvyId6R7oZjFv
- FastF1 docs (supplementary only): https://docs.fastf1.dev/

See `research/SOURCE_REGISTER.md` for how each source is used and its caveats.

## Research endpoint added

`GET /api/research/{year}/{round}/{driver_number}` returns energy fingerprints, context-aware tyre model comparisons, XY-curvature-derived corner-like exit repeatability and a normalized-segment fallback. `GET /api/research/compare/{year}/{round_num}?driver_numbers=...` compares the same energy-proxy thresholds across 2–4 selected drivers. None of these outputs measures proprietary ERS deployment or official corner IDs.

Optional query parameters for the normalized fallback: `segment_start` and `segment_end` (fractions between 0 and 1; defaults 0.80 and 0.90).

Run backend tests with `cd backend && pytest -q`. The research implementation is exploratory and should be validated against live event data before drawing performance conclusions. Corner-like segments are detected algorithmically from XY location curvature and are not official turn IDs. Strategy scenario compound offsets and degradation defaults are illustrative assumptions, not measured tyre supplier data. OpenF1 telemetry coverage is not available for 2022; 2026 event coverage depends on sessions published by the API.


## V6 research validation
See `research/V6_VALIDATION_GUIDE.md` for synthetic calibration, leakage-safe filter/smoother modes, real OpenF1 race retrieval, and limits on evidence-based claims. `results/SYNTHETIC_CALIBRATION.json` is generated from synthetic data only. `results/REAL_EVENT_BRIEF_PENDING.md` explains how to generate a genuine race brief.

## V8 — research results directly in the UI

Open **Research Results** in the sidebar. Compare actual executed OpenF1 benchmark scores by race and stint with bar/line charts. The initial `results/cross_event_real.json` was supplied by the user from their successful three-race execution. After running a new benchmark, use **RELOAD SAVED RESULT**; alternatively import a JSON file with **IMPORT JSON**. The dashboard does not invent missing scores. See `research/V8_RESULTS_DASHBOARD.md` for methodology and validation status.

---

## V11 release candidate — read before running or publishing

See **[README_RELEASE_START_HERE.md](README_RELEASE_START_HERE.md)** for current setup and overview, **[research/V11_RELEASE_CANDIDATE.md](research/V11_RELEASE_CANDIDATE.md)** for validation gates, and **[steering_research/README.md](steering_research/README.md)** for experimental CNN/GRU/optical-flow training and inference. The optional deep-learning model has **no demonstrated real-world steering accuracy** yet.
