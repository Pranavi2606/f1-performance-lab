"""Turn a previously executed OpenF1 benchmark JSON into an auditable engineering brief.

No network call, no invented observations, and no inference of tyre wear from slope alone.
"""
import argparse
import json
import math
from pathlib import Path


def _number(value, precision=4):
    if isinstance(value, (int, float)) and math.isfinite(value):
        return f"{value:+.{precision}f}"
    return "unavailable"


def _escape(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_brief(result, origin="user-supplied benchmark JSON"):
    if result.get("source") != "OpenF1":
        raise ValueError("Expected an explicitly OpenF1-labelled benchmark JSON")
    events = result.get("events", [])
    if not isinstance(events, list) or not events:
        raise ValueError("No event entries in benchmark")
    year = result.get("year", "unknown")
    driver = result.get("driver", "unknown")
    computed = [e for e in events if e.get("status") == "computed"]
    lines = [
        f"# Historical F1 engineering research brief — {year}, driver #{driver}", "",
        "> **Evidence category:** Report generated from an executed benchmark JSON; this report generator does not fetch OpenF1 data or independently verify that the upstream file came from OpenF1.", "",
        f"**Input provenance:** {_escape(origin)}. **Reported feed:** OpenF1. **Events computed:** {len(computed)}/{len(events)}.", "",
        "## Observed-model comparisons", "",
        "The slope is a fitted *lap-time association with tyre age* in seconds per lap, **not a causal measurement of tyre wear**. The 95% interval is model-dependent.", "",
        "| Event | Session key | Retained lap observations | Slope (s/lap) | 95% credible interval | Global-median inside CI? |",
        "|---|---:|---:|---:|---|---|",
    ]
    for e in events:
        if e.get("status") != "computed":
            lines.append(f"| {_escape(e.get('circuit','Unknown'))} | {_escape(e.get('session_key','—'))} | — | unavailable | — | — |")
            continue
        ci = e.get("ci95", [])
        interval = f"[{_number(ci[0])}, {_number(ci[1])}]" if len(ci) == 2 else "unavailable"
        included = {True: "yes", False: "no"}.get(e.get("ci_contains_global_median"), "unavailable")
        lines.append(f"| {_escape(e.get('circuit','Unknown'))} | {_escape(e.get('session_key','—'))} | {e.get('n_laps','—')} | {_number(e.get('slope'))} | {interval} | {included} |")
    lines += ["", "## Held-out lap-time prediction — within-stint chronology", "",
              "These are held-out **laps within each event**, not a model trained at one circuit and transferred to another. Compare MAE and RMSE against a training-median baseline.", "",
              "| Event | Model | Held-out laps | MAE (seconds) | Pooled RMSE (seconds) |", "|---|---|---:|---:|---:|"]
    any_benchmark = False
    for e in computed:
        bench = e.get("predictive_benchmark", {})
        if not bench or not bench.get("ready"):
            lines.append(f"| {_escape(e.get('circuit'))} | unavailable (older benchmark JSON or insufficient stints) | — | — | — |")
            continue
        by_model = {}
        for fold in bench.get("folds", []):
            n = int(fold.get("test_laps", 0))
            if n <= 0: continue
            for name, metrics in fold.get("models", {}).items():
                d = by_model.setdefault(name, [0,0.,0.])
                d[0] += n
                d[1] += n * float(metrics["mae_s"])
                d[2] += n * float(metrics["rmse_s"])**2
        if not by_model:
            lines.append(f"| {_escape(e.get('circuit'))} | no valid folds | — | — | — |")
        for model, (n, weighted_mae, weighted_sse) in sorted(by_model.items()):
            if n:
                any_benchmark = True
                lines.append(f"| {_escape(e.get('circuit'))} | {model} | {n} | {weighted_mae/n:.3f} | {math.sqrt(weighted_sse/n):.3f} |")
    lines += ["", "## Interpretation and confounding", "",
              "- A positive slope is associated with increasing lap times; a negative slope with decreasing lap times. Neither uniquely identifies physical tyre degradation.",
              "- **Fuel mass reduction**, pit stops and compound transitions, traffic, race-control periods, weather, track evolution and sampling biases can change apparent slopes.",
              "- A credible interval excluding the median of three circuit estimates is **not** evidence on its own of a regime shift or generalization failure.",
              "- With only three events, no out-of-event predictive generalization claim is supported.",
              "- Steering angle, tyre surface condition, detailed brake pressure, battery state/ERS command and proprietary CFD data are **unavailable** from the standard OpenF1 car feed.",
              "- The model's predictive-interval calibration on historical race laps is **not established** by the synthetic calibration audit.",
              "", "## Evidence and reproducibility", "",
              "- Source API documentation: https://openf1.org/ ; verify API provenance and terms before redistribution.",
              "- Run `python scripts/cross_event_benchmark.py --year 2024 --driver 1 --circuits Bahrain Monaco Belgium --output ../results/cross_event_real.json` from `backend/` on a network-enabled machine.",
              "- Generate this report with `python scripts/generate_engineering_brief.py --input ../results/cross_event_real.json --output ../results/ENGINEERING_BRIEF_2024.md`.",
              "- Keep the original JSON alongside this Markdown to support reproducibility; timestamps and raw-response hashes have not yet been recorded.",
              "", "## What we can safely say", "",
              f"The supplied benchmark records {len(computed)} successful circuit analyses using publicly described OpenF1 observations. " + ("Within-event held-out predictions are reported above; they do not test cross-circuit transfer." if any_benchmark else "**No out-of-sample prediction metrics appear in this input, so predictive accuracy cannot be claimed from it.**"),
              ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    input_path = Path(args.input)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_brief(payload, str(input_path)), encoding="utf-8")
    print(f"Wrote {output_path}")

if __name__ == "__main__":
    main()
