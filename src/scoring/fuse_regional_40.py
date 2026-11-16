"""Blend regional aggregate form into the existing HITL PRI for eligible players.

A single aggregate form proxy is applied to both PRI axes. This DOES NOT mean
pressure and reliability were separately estimated for these players.
Run AFTER hitl_fusion.py and remaining_seven_model.py; repeatable/idempotent.
"""
from __future__ import annotations

import csv
import json
import math
from datetime import datetime
from pathlib import Path
from shutil import copy2

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
JSON_PATH = ROOT / "frontend" / "public" / "data" / "scouting_scores.json"
SCORE_PATH = OUT / "remaining_seven_model.csv"
RESULT_PATH = OUT / "hitl_regional_40_final.csv"
MODEL_WEIGHT = 0.40


def valid_number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def main():
    if not JSON_PATH.is_file() or not SCORE_PATH.is_file():
        raise SystemExit("Missing dashboard JSON or remaining_seven_model.csv. Run the prior scripts first.")

    with JSON_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    players = data.get("players")
    if not isinstance(players, list):
        raise SystemExit("Invalid dashboard JSON: players list missing.")

    with SCORE_PATH.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    model = {r["player"].strip(): r for r in rows if r.get("player")}

    # Keep a backup outside the live frontend directory; repeated runs are safe.
    backup = OUT / "scouting_scores_before_regional_fusion.json"
    if not backup.exists():
        copy2(JSON_PATH, backup)

    updated = []
    for p in players:
        name = p.get("name", "")
        entry = model.get(name)
        if not entry:
            continue
        form = valid_number(entry.get("aggregate_form_score"))
        h_pressure = valid_number(p.get("humanPressure"))
        h_reliability = valid_number(p.get("humanReliability"))
        if form is None or h_pressure is None or h_reliability is None:
            continue  # Aaryavir: missing balls faced; do not invent the score.
        if not (0 <= form <= 5 and 0 <= h_pressure <= 5 and 0 <= h_reliability <= 5):
            raise SystemExit(f"Score out of range: {name}")
        # Never overwrite a full-delivery statistical profile.
        if p.get("assessmentMethod") not in {"ANALYST_ONLY", "AGGREGATE_FORM_HITL_40"} and (valid_number(p.get("modelMatches")) or 0) > 0:
            continue
        if name not in {"Tushar Raheja", "Yajas Sharma", "Aaryavir Sehwag", "Khilan Patel", "Mohit Ulva", "Shubham Kumar Gupta", "Ishant Bharadwaj"}:
            continue

        pressure = round(MODEL_WEIGHT * form + (1 - MODEL_WEIGHT) * h_pressure, 2)
        reliability = round(MODEL_WEIGHT * form + (1 - MODEL_WEIGHT) * h_reliability, 2)
        pri = round(pressure + reliability, 2)
        p.update({
            "modelWeight": MODEL_WEIGHT,
            "humanWeight": 1 - MODEL_WEIGHT,
            "pressureScore": pressure,
            "reliabilityScore": reliability,
            "overallScore": pri,
            "assessmentMethod": "AGGREGATE_FORM_HITL_40",
            "aggregateFormScore": form,
            "aggregateModelType": "AGGREGATE_FORM_PROXY",
            "aggregateProxyAppliedToBothAxes": True,
            "aggregateMethodNote": "40% aggregate form proxy + 60% analyst on each PRI axis; proxy is NOT independently estimated pressure or reliability.",
            # Don't fill modelPressure/modelReliability with an invented independent estimate.
            "modelPressure": None,
            "modelReliability": None,
        })
        updated.append(name)

    # Full ranking recomputation, stable alphabetical tie break.
    players.sort(key=lambda p: (-float(p.get("overallScore", 0)), str(p.get("name", ""))))
    for i, p in enumerate(players, 1):
        p["rank"] = i
    data["version"] = "0.6-HITL-Regional40"
    data["regionalFusionMethod"] = "0.4 * (2 * aggregate_form_score) + 0.6 * (human_pressure + human_reliability); for eligible regional-only profiles. The same aggregate proxy is used on both axes, not a separate reliability estimate."

    # Write atomically to avoid partially written JSON served by Next.js.
    tmp = JSON_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)
    tmp.replace(JSON_PATH)

    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["rank", "name", "pressureScore", "reliabilityScore", "overallScore", "modelWeight", "humanWeight", "assessmentMethod", "aggregateFormScore"]
    with RESULT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(players)

    print("\n=== UPDATED 40% REGIONAL MODEL + 60% ANALYST ===")
    print(f"Regional players fused: {len(updated)}")
    for p in players:
        if p["name"] in updated:
            print(f"#{p['rank']:02d} {p['name']:<23} form={p['aggregateFormScore']:.2f}  pressure={p['pressureScore']:.2f}  reliability={p['reliabilityScore']:.2f}  PRI={p['overallScore']:.2f}  model=40%")
    print("\nNot fused: Aaryavir Sehwag (no numerical aggregate form score)")
    print(f"Updated: {JSON_PATH}")
    print(f"Ranking CSV: {RESULT_PATH}")
    print(f"Initial backup: {backup}")
    print("NOTE: Regional scores are aggregate FORM proxies, not direct pressure/reliability measurements.")


if __name__ == "__main__":
    main()
