"""Build a reproducible, low-cost OpenF1 race-session coverage manifest.

This tool deliberately fetches metadata only, not bulk car/location telemetry.
Run it locally or in a scheduled ingestion job; never on every visitor request.

Usage:
  python backend/scripts/build_2026_coverage.py --years 2025 2026 --output data-cache/coverage.json
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://api.openf1.org/v1/sessions"
SOURCES = {"sessions": "https://openf1.org/docs/"}


def retrieve(year: int, retries: int = 3) -> list[dict]:
    url = API + "?" + urlencode({"year": year, "session_name": "Race"})
    for attempt in range(retries):
        try:
            with urlopen(Request(url, headers={"User-Agent": "F1-Performance-Lab-Research/1.0"}), timeout=30) as response:
                result = json.load(response)
            if not isinstance(result, list):
                raise ValueError("Unexpected sessions response")
            return result
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == retries - 1:
                raise
            retry_after = exc.headers.get("Retry-After")
            try:
                delay = min(60.0, max(1.0, float(retry_after))) if retry_after else 2 ** attempt
            except ValueError:
                delay = 2 ** attempt
            time.sleep(delay)
        except (URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Retries exhausted")


def make_manifest(years: list[int], offline: Path | None = None) -> dict:
    seasons: dict[str, list[dict]] = {}
    for year in years:
        if offline is not None:
            sessions = json.loads((offline / f"sessions_{year}.json").read_text(encoding="utf-8"))
        else:
            sessions = retrieve(year)
            time.sleep(2.1)  # Do not burst requests, even across years
        rows = []
        for session in sessions:
            if session.get("session_name") != "Race":
                continue
            rows.append({
                "session_key": session.get("session_key"),
                "meeting_key": session.get("meeting_key"),
                "session_name": session.get("session_name"),
                "meeting_name": session.get("meeting_name"),
                "location": session.get("location"),
                "country_name": session.get("country_name"),
                "date_start": session.get("date_start"),
                "date_end": session.get("date_end"),
                "coverage": {
                    "sessions": "observed",
                    "drivers": "not_checked",
                    "laps": "not_checked",
                    "stints": "not_checked",
                    "car_data": "not_checked",
                    "location": "not_checked",
                    "weather": "not_checked",
                    "race_control": "not_checked",
                },
            })
        seasons[str(year)] = sorted(rows, key=lambda x: x["date_start"] or "")
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": SOURCES,
        "method": "OpenF1 Race sessions only; telemetry not downloaded or verified",
        "seasons": seasons,
        "warnings": [
            "Race sessions are not equivalent to complete telemetry coverage.",
            "Use session_key to request data; never infer a session from round number alone.",
            "Do not publish raw third-party telemetry without checking its data terms.",
            "This file is a snapshot, not a live status or a guarantee of future availability."
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", type=int, default=[2025, 2026])
    parser.add_argument("--output", type=Path, default=Path("data-cache/coverage.json"))
    parser.add_argument("--offline", type=Path, help="Directory with sessions_YEAR.json fixtures; makes testing network-free")
    args = parser.parse_args()
    if any(y < 2023 or y > 2100 for y in args.years):
        parser.error("OpenF1 session coverage begins in 2023")
    report = make_manifest(sorted(set(args.years)), args.offline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, args.output)
    print(f"Wrote {args.output} ({sum(len(s) for s in report['seasons'].values())} race sessions)")


if __name__ == "__main__":
    main()
