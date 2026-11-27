# 2026 research roadmap — audited foundation

Status: **planning and metadata ingestion only**. This is not an executed 2026 race-performance study.

## Existing modules (reuse; do not duplicate)
- `frontend/src/components/EnergyPage.tsx`: FIA regulation arithmetic and `StrategySimulator`. Add a new **observational comparison layer** beneath the calculator, never re-label the current calculation as inferred deployment.
- `frontend/src/components/SteeringResearchPage.tsx`: saved experiment visualizations. The original dataset had confirmed exact-image train/validation leakage; the saved MAE values are historical exploratory evidence, not validated performance.
- `frontend/src/components/DiscoveryPage.tsx`: research bundle, contextual tyre, car/location/energy proxies. Large OpenF1 requests currently occur during user interactions.
- `backend/app/services/openf1.py`: process-local `lru_cache` only; not shared across Vercel instances.
- `backend/app/services/http.py`: worker-local 0.6 s pacing, bounded retry on 429. Not sufficient for a globally shared 30/minute provider quota.
- `backend/scripts/build_2026_coverage.py`: metadata-only offline-testable 2025/2026 race-session manifest (new).

## Protection & accessibility
- Public browser code and browser-delivered results cannot be made uncopyable.
- Keep dataset provenance, results summaries, independently reproducible baselines and method limitations public.
- Keep *original annotations, licensed footage, unpublished model weights, internal experimental notebooks and derived research assets* private until provenance, sharing rights and publication strategy are reviewed.
- Consider a private repository for research-in-progress, authored source licenses, citation instructions, an original website brand/favicon, commit history and dated preprints/DOIs. A copyright footer does **not** prevent scraping. Avoid exposing research secrets in Vite `VITE_*` values.
- Separate public reference calculations from private, resource-heavy experiments. Don't promise exclusive algorithms in browser JavaScript.

## Multi-user architecture (not yet implemented)
1. Public API serves indexed **precomputed, per-session JSON / Parquet-derived summary files**; cache immutable completed sessions on CDN/object storage.
2. Historical ingestion runs as a separate scheduled/queued worker, not on each website visit. Store session-key manifests, per-feed fetch timestamps, source/version/checksums, and licensing terms.
3. Use a **shared** per-provider rate limiter and shared request de-duplication (e.g., Redis + distributed lock / queue). The 3/s and 30/min free limits apply to *aggregate upstream requests*, not each visitor.
4. Apply application-level per-IP/user rate limits; cap expensive endpoints, payload size, max concurrency and per-request timeouts. Cache errors briefly; use exponential backoff for 429/5xx with respect for `Retry-After`; avoid retry storms.
5. Queue expensive comparison/research analyses with bounded workers; return job IDs and polling status. Keep quick deterministic calculators independent of OpenF1.
6. Use monitoring: p50/p95 latency, 4xx/5xx, provider 401/429, cache hit ratio, job queue length and concurrency. Allow a graceful **dataset unavailable** state rather than fabricated results.

## Research questions / segmentation
**Main hypothesis:** After regulating for session, circuit, tyre/traffic/weather and qualifying-versus-race conditions, public performance indicators show detectable regime shifts across 2026.

**Regimes (pre-registered, not assumed causation):**
- Opening races before Miami regulation changes (2026 energy parameters revised for Miami, distinguish source issue date from effective session).
- Post-Miami until the summer break.
- Post-summer-break.
- Explore data-driven change points only as secondary analysis; do not tune boundaries after seeing hold-out results.

**Per event:** driver, constructor, meeting_key, session_key, track, date, session conditions, official classification, valid laps, pit stints, relative pace, sector/mini-sector, public speed/throttle/brake/gear/RPM, flags and data quality.

**Case studies:** São Paulo and Las Vegas 2026, with independent 2025/2026 held-out races. Report raw classification first, then model outputs; do not infer battery SoC/ERS maps.

**Validation:** session-key matching, missing-data audit, track normalization, uncertainty, robust baselines, leave-one-event-out, sensitivity to traffic/yellow flags, data-release version lock, corrections log.

## Steering follow-up study
1. Review raw footage identity/licensing and candidate recording groups; quarantine suspected duplicates, overlapping crops and simulated footage.
2. Build source-disjoint split and publish only legally redistributable samples or aggregate metadata.
3. Compare constant-angle baseline vs CNN / CNN+GRU / CNN+GRU+flow, multiple seeds with identical budgets.
4. Evaluate MAE, RMSE, percentile error, signed bias, per-source confidence intervals and failure gallery; disclose units and label protocol.
5. Only update the Steering UI with new scores after a complete rerun and evidence provenance.

## Next gate
Run `python backend/scripts/build_2026_coverage.py --years 2025 2026 --output data-cache/coverage.json` **in a network-connected development environment**. The first output shows verified race session metadata only. Verify race dates/classifications from FIA/Jolpica before requesting any high-frequency feed. Do not commit a large raw telemetry corpus to this public repository.
