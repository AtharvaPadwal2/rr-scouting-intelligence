from pathlib import Path
import json
import math
import pandas as pd

ROOT = Path.cwd()
OUT = ROOT / "outputs"

SOURCE = OUT / "final_royal_edge_pri.json"
TARGET = OUT / "final_royal_edge_pri_v2.json"
CSV = OUT / "final_royal_edge_pri_v2.csv"

if not SOURCE.exists():
    raise SystemExit("Original PRI JSON not found.")

data = json.loads(SOURCE.read_text(encoding="utf-8"))

def clamp(x):
    return max(0.0, min(1.0, float(x)))

def model_reliability(player):
    required = [
        "positiveMatchPct",
        "pressureBalls",
        "pressureMatches",
        "top10StabilityPct",
    ]

    for field in required:
        value = player.get(field)
        if value is None:
            raise ValueError(
                f"{player['name']}: missing {field}"
            )
        if not math.isfinite(float(value)):
            raise ValueError(
                f"{player['name']}: invalid {field}"
            )

    consistency = clamp(
        player["positiveMatchPct"] / 100
    )

    ball_confidence = clamp(
        player["pressureBalls"]
        / (player["pressureBalls"] + 120)
    )

    match_breadth = clamp(
        player["pressureMatches"] / 30
    )

    rank_stability = clamp(
        player["top10StabilityPct"] / 100
    )

    score = 5 * (
        0.40 * consistency
        + 0.25 * ball_confidence
        + 0.20 * match_breadth
        + 0.15 * rank_stability
    )

    return score, {
        "consistency": round(consistency, 4),
        "ballConfidence": round(ball_confidence, 4),
        "matchBreadth": round(match_breadth, 4),
        "rankStability": round(rank_stability, 4),
    }

for role in ["batting", "bowling"]:
    players = data[role]

    if len(players) != 10:
        raise ValueError(
            f"{role}: expected 10 players"
        )

    for player in players:
        name = player["name"]

        model_p = player.get("modelPressure")
        if model_p is None:
            raise ValueError(
                f"{name}: no model pressure evidence"
            )

        human_p = float(player["humanPressure"])
        human_r = float(player["humanReliability"])
        w = float(player["modelWeight"])

        if not 0 <= w <= 1:
            raise ValueError(
                f"{name}: invalid model weight"
            )

        model_r, dimensions = model_reliability(player)

        # Pressure: existing hybrid method
        final_p = (
            w * float(model_p)
            + (1 - w) * human_p
        )

        # Reliability: NEW hybrid method
        final_r = (
            w * model_r
            + (1 - w) * human_r
        )

        pri = final_p + final_r

        player["modelReliability"] = round(model_r, 3)
        player["reliabilityDimensions"] = dimensions
        player["pressureScore"] = round(final_p, 3)
        player["reliabilityScore"] = round(final_r, 3)
        player["overallScore"] = round(pri, 3)

        player["assessmentMethod"] = (
            "HYBRID_PRESSURE_AND_RELIABILITY"
        )

    players.sort(
        key=lambda p: (
            -p["overallScore"],
            -p["pressureBalls"],
            p["name"],
        )
    )

    for i, player in enumerate(players, 1):
        player["rank"] = i

data["model"] = "ROYAL EDGE HYBRID PRI v2"
data["version"] = "2.0-statistical-reliability"
data["scoresValidated"] = False

data["methodology"] = {
    "pressureFormula":
        "w*modelPressure + (1-w)*humanPressure",
    "reliabilityFormula":
        "w*modelReliability + (1-w)*humanReliability",
    "modelReliabilityFormula":
        "5*(0.40*C + 0.25*B + 0.20*M + 0.15*S)",
    "C": "positiveMatchPct/100",
    "B": "pressureBalls/(pressureBalls+120)",
    "M": "min(pressureMatches/30,1)",
    "S": "top10StabilityPct/100",
    "finalFormula":
        "pressureScore + reliabilityScore",
    "modelNormalization":
        "Role-specific percentile of provisional "
        "adjusted structural-pressure impact",
    "modelWeight":
        "30% for 1-249 pressure balls; "
        "50% for 250-599; 70% for 600+",
    "limitations": [
        "Pressure classification remains provisional",
        "Bowling extras accounting requires validation",
        "Human assessments are subjective",
        "Top-10 stability refers to the full model pool",
        "Phase-specific PDF weights are not "
        "independently recomputed here",
        "PRI ranks apply to the selected 10 per role",
    ],
}

all_players = data["batting"] + data["bowling"]

assert len(all_players) == 20
assert len({p["name"] for p in all_players}) == 20
assert all(
    0 <= p["pressureScore"] <= 5
    and 0 <= p["reliabilityScore"] <= 5
    and 0 <= p["overallScore"] <= 10
    for p in all_players
)

# Save separately; original PRI v1 remains intact.
TARGET.write_text(
    json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    ),
    encoding="utf-8"
)

pd.DataFrame(all_players).drop(
    columns=["reliabilityDimensions"],
    errors="ignore"
).to_csv(CSV, index=False)

for role in ["batting", "bowling"]:
    print(f"\n=== ROYAL EDGE PRI v2: {role.upper()} ===")

    table = pd.DataFrame([
        {
            "Rank": p["rank"],
            "Player": p["name"],
            "Model P": p["modelPressure"],
            "Model R": p["modelReliability"],
            "Human P": p["humanPressure"],
            "Human R": p["humanReliability"],
            "Final P": p["pressureScore"],
            "Final R": p["reliabilityScore"],
            "PRI": p["overallScore"],
        }
        for p in data[role]
    ])

    print(table.round(2).to_string(index=False))

print("\nSUCCESS: PRI v2 calculated for 20 players.")
print("JSON:", TARGET)
print("CSV:", CSV)
print("Original PRI v1 preserved.")
