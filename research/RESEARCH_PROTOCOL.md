# F1 Race Decision Intelligence — Research Protocol & Technical Note

**Version:** 1.1 (4 November 2026)  
**Status:** Research protocol and reproducible analysis specification. Empirical findings are intentionally not claimed until the selected event data have been fetched, quality-checked, and analysed.

## Abstract

This project is an open-data research platform for investigating three questions in Formula One performance analysis: (1) whether public telemetry contains repeatable signatures consistent with changes in straight-line energy deployment, (2) how tyre-age-associated lap-time trends vary after excluding abnormal laps and accounting for observable race context, and (3) whether corner-exit performance differences are repeatable across laps. The platform combines race classifications from Jolpica with historical session, lap, stint, weather, race-control and car telemetry data from OpenF1. The work deliberately distinguishes directly observed measurements from derived proxies and regulation-based calculations. Public telemetry does not provide verified team battery state-of-charge or a complete ERS deployment trace; consequently, the energy investigation is framed as a test of observable signatures, not a reconstruction of proprietary energy strategy.

## Scope and data provenance

### Season coverage

- **2022:** classification and schedule analysis via Jolpica. OpenF1 historical data coverage begins in 2023, so telemetry-based investigations are unavailable for 2022.
- **2023–2024:** historical session and telemetry analysis where endpoint coverage exists.
- **2025–2026:** recent-season analysis where the upstream API has published the relevant completed session and records. A calendar entry is not evidence that a session's data are complete.

The app must display empty/unavailable states for missing upstream data. It must not silently substitute synthetic samples.

### Primary data sources

1. **Jolpica F1 API** — schedule, race results/classification, qualifying, sprint and pit-stop endpoints. It is an open-source, community-maintained successor to the Ergast-compatible API. Treat it as an independent data service, not an FIA/FOM official feed.
2. **OpenF1 API** — meetings, sessions, drivers, laps, stints, pit stops, car data, location, weather and race-control messages. OpenF1 states that historical data are available from 2023 onward, and describes itself as independent and unaffiliated with Formula One/FIA. Free historical use is subject to its current rate limits and terms.
4. **FIA 2026 Technical Regulations, Section C, Issue 21 (19 October 2026), with FIA / Formula1.com stakeholder updates as secondary context** — primary regulatory source. Article C5.2.7 sets the 350 kW absolute ERS-K electrical DC ceiling. Article C5.2.10 sets an 8.5 MJ per-lap recharge framework, conditionally reducible to 7 MJ and further to no less than 4 MJ for qualifying under specified conditions, with up to 0.5 MJ additional energy subject to Article B7.2. Stakeholder summaries describe a 2–4 second superclip target; event-specific FIA documents and current regulation issue take precedence.
5. **FastF1 documentation** — optional supplementary Python interface to F1 timing data and telemetry. It is not the primary data source in the current app and should be introduced only with explicit source attribution, caching and licensing review.

## Research question 1 — Energy-deployment fingerprints in public telemetry

### Question
Can public speed, throttle, brake, gear, RPM and location/time-series signals identify repeatable straight-line speed or acceleration patterns that are *consistent with* changes in energy deployment, without claiming to observe the underlying battery or ERS command?

### Hypothesis (to be tested, not assumed)
Within comparable straight-line segments, some laps may exhibit repeatable changes in speed/acceleration profiles. Such patterns may be associated with energy-management behaviour, but can also be caused by lift-and-coast, traffic, DRS, wind, gearing, fuel load, tyre condition, track evolution or sensor/data quality.

### Method
1. Select a session and driver; retrieve car data and location where available.
2. Validate timestamps, monotonicity, duplicate records, impossible values and gaps. Retain a quality log.
3. Identify candidate straights using circuit/location geometry or a documented manually curated segment map. Do not infer straight segments from speed alone.
4. Align laps to distance using timestamp integration of speed; report accumulated distance as an estimate and reset/segment on large gaps.
5. Compute observable descriptors: speed, longitudinal speed derivative, throttle state, braking state, gear and RPM. Record whether DRS data are present.
6. Compare like-for-like segments within the same session and driver first. Extend to between-driver or between-event comparisons only with explicit normalisation and confounder checks.
7. Label any detector output **candidate telemetry signature**. It is not an ERS deployment measurement.

### Falsification / rejection criteria
Reject or flag candidate segments with inadequate sampling, timestamp gaps, implausible derivatives, missing channels, pit-lane activity, yellow/safety-car periods, or non-comparable track conditions. If the data cannot distinguish competing explanations, report the result as inconclusive.

### What can be claimed
The platform can describe measured public telemetry channels and derived kinematic proxies. It cannot claim to know actual battery state-of-charge, MGU-K deployment command, or team energy strategy from these channels alone.

## Research question 2 — Tyre-age trend versus race-context effects

### Question
How much of the within-stint lap-time trend is associated with tyre age, and how sensitive is that estimate to excluding abnormal laps and observable race context?

### Baseline model
For each stint, fit an ordinary least-squares descriptive trend:

`lap_time_i = intercept + beta * tyre_age_i + error_i`

The slope `beta` is expressed in seconds per lap. Report sample count, R-squared, excluded laps and exclusion reasons. It is not a pure physical tyre degradation coefficient.

### Quality filters and confounders
Exclude or separately flag pit in/out laps, laps with missing/invalid duration, implausibly slow laps, safety-car/VSC or yellow-flag periods where identifiable, and outliers under a documented robust rule. Where available, attach weather and race-control context. Fuel load, traffic, driver management, track evolution and car damage remain potential unobserved confounders.

### Model comparison plan
The implementation compares an age-only OLS baseline with a context-adjusted OLS model using available track temperature, air temperature and rain indicator. It excludes pit-out laps and identifiable safety-car/yellow/red-flag laps based on race-control messages. The lap-time Random Forest uses a chronological within-session holdout and a training-median baseline. This remains exploratory; grouped cross-race and cross-season validation is required before claiming generalisation. Every comparison must report split strategy, sample size, MAE/RMSE and limitations.

### Interpretation
A positive slope indicates lap times increased with lap number in the retained sample. It does not, by itself, prove tyre wear caused the increase. Compare model residuals and sensitivity to filtering before making strategic interpretations.

## Research question 3 — Repeatability of corner-exit performance

### Question
Do observable corner-exit speed/acceleration patterns repeat across a driver's laps, and are differences robust to lap selection and session context?

### Method
1. Use timestamped location and car data where coverage permits; construct a consistent distance coordinate per lap.
2. Current implementation derives curve-like zones from XY trajectory curvature in OpenF1 location samples and uses a fixed distance window around each detected curve exit. These are algorithmic candidate segments, not official turn IDs; visual validation against a circuit map remains required. Avoid selecting windows based solely on the outcome being tested.
3. Align comparable laps by distance and calculate speed at exit, speed gain over a fixed downstream distance, and time to traverse the window.
4. Compare a driver's laps to their own session median first. Report median, spread, number of valid laps and excluded laps.
5. Compare drivers only after matching session, tyre/stint context and relevant flags as far as public data allow.
6. Test repeatability on held-out laps or a separate session where available.

### Limitations
OpenF1 location coordinates are approximate and do not encode lateral placement. Distance reconstructed by integrating speed is sensitive to missing samples and timing gaps. Public channels do not expose steering angle, suspension state, aerodynamic load or the full vehicle-control stack. Any conclusion must remain descriptive.

## 2026 energy-regulation reference note

The current FIA 2026 Technical Regulations, Section C, Issue 21 (19 October 2026), Article C5.2.7 sets an absolute ERS-K electrical DC power ceiling of 350 kW. Article C5.2.9 limits the difference between maximum and minimum energy-store state of charge to 4 MJ. Article C5.2.10 sets an 8.5 MJ per-lap recharge framework, conditionally reducible to 7 MJ where FIA determines harvest potential under braking and partial load is no more than 7 MJ; qualifying may be further reduced to no less than 4 MJ under specified conditions, with up to 0.5 MJ additional energy subject to Article B7.2. Stakeholder summaries describe a 2–4 second superclip target, but it is not a measured trace. Check the latest FIA issue and event-specific power-unit information before using parameters. The UI's calculator is dimensional arithmetic (`energy_MJ = power_kW × duration_s / 1000`) and must not imply that the entire recharge allowance is deployable energy.

## Reproducibility and audit requirements

For every analysis run, retain or display: selected season/event/session/driver; source endpoint; retrieval timestamp; number of raw and retained observations; filters and exclusion reasons; units; formula/model version; and limitations. Cache responses responsibly and respect upstream rate limits. If an endpoint fails, surface the failure and do not replace it with fabricated values.

## Current implementation status

- Race schedule/classification: Jolpica integration.
- OpenF1 session resolution, drivers, laps, stints, pits, car data, weather and race-control service wrappers.
- Stint trend: within-stint linear regression with robust lap cleaning and exclusion audit.
- Telemetry: speed/throttle/brake display; distance estimated by trapezoidal integration of speed samples.
- Strategy insights: classification-derived grid-to-finish movement.
- Energy calculator: transparent power × time calculation with 2026 regulation context.
- Performance model: Random Forest baseline with chronological within-session holdout, training-median baseline comparison and feature importance. It is not cross-race validation.
- Context-aware tyre model: age-only OLS, weather-adjusted OLS with stint fixed effects, and exploratory single-breakpoint piecewise regression selected by BIC; exclusions and limitations are returned.
- Corner-exit proxy: XY location curvature-based curve-like segment detection, same-order segment comparison, exit speed/throttle statistics; not official corner IDs and requires visual validation.
- Energy comparison: same candidate acceleration thresholds applied to two selected drivers; this is not ERS measurement.
- Strategy scenario search: deterministic-seed Monte Carlo ranking of illustrative one-stop and two-stop compound sequences under explicit assumed pace offsets and degradation rates.

This report is a protocol and implementation note. **It does not report empirical discoveries until a specific dataset has been fetched and analysed.**

## References and source register

- Jolpica F1, project and API documentation: https://github.com/jolpica/jolpica-f1
- Jolpica results endpoint documentation: https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/results.md
- OpenF1, API documentation: https://openf1.org/docs/
- OpenF1, project overview, historical coverage, rate limits and terms: https://openf1.org/
- FIA, 2026 Formula One Technical Regulations, Section C, Issue 21, 19 October 2026: https://www.fia.com/system/files/documents/fia_2026_f1_regulations_-_section_c_technical_-_iss_21_-_2026-10-19.pdf
- Formula1.com, “Refinements to 2026 F1 regulations agreed by all stakeholders”: https://www.formula1.com/en/latest/article/refinements-to-2026-f1-regulations-agreed-by-all-stakeholders.1xA0TRau0DvyId6R7oZjFv.1xA0TRau0DvyId6R7oZjFv
- FIA, “Refinements to the 2026 FIA Formula 1 regulations agreed by all stakeholders”: https://api.fia.com/news/refinements-2026-fia-formula-1-regulations-agreed-all-stakeholders
- FastF1 documentation (supplementary; not currently used as a primary app data feed): https://docs.fastf1.dev/

## Disclaimer
This is an independent educational and portfolio research project. It is not affiliated with Formula One, Formula One Management, the FIA or any F1 team. F1-related names and marks belong to their respective owners. Review upstream API terms and any data licensing requirements before commercial use or redistribution.

## Implemented exploratory telemetry endpoints (2026-11-04)

The backend exposes `GET /api/research/{year}/{round}/{driver_number}` and `GET /api/research/compare/{year}/{round_num}?driver_numbers=...`. The bundle returns the following analyses from OpenF1 public data:

1. **Energy fingerprint candidate windows:** samples are sorted by timestamp; a sample qualifies when speed is at least 180 km/h, throttle is at least 95%, brake is at most 5%, and speed-derived longitudinal acceleration exceeds 0.15 m/s². Contiguous runs of at least three samples are reported. These are high-throttle acceleration fingerprints only; they do not measure ERS deployment, MGU-K power, or state of charge.
2. **Context-aware tyre model:** compares age-only OLS, weather-adjusted OLS with stint fixed effects, and a one-breakpoint piecewise model. It reports BIC, R², MAE, RMSE, exclusions and caveats.
3. **Corner-exit repeatability (exploratory):** location XY samples are used to estimate path curvature, group candidate curve-like segments, integrate per-lap distance and compare mean speed/throttle in a fixed window around each detected segment exit. These are not official turn IDs and require circuit-map visual validation.
4. **Normalized lap-segment fallback:** if location data is unavailable or insufficient, telemetry is sampled in a configurable 80–90% elapsed-time window. This is not a named corner or physical corner-exit measurement.

Automated unit tests cover threshold detection, normalized time windows, contextual tyre regression, missing location handling and deterministic strategy outputs. The backend test suite currently contains 9 tests. Live OpenF1 event-by-event validation and frontend production build still need to be run in the target Windows environment; do not report empirical F1 findings or frontend build success until those checks are completed.
