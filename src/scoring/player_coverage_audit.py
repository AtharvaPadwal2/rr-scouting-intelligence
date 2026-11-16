
from pathlib import Path
from difflib import get_close_matches
import pandas as pd

BASE = Path("data/processed/rr_official")
OUTPUT = Path("outputs")
OUTPUT.mkdir(parents=True, exist_ok=True)

PLAYERS = [
    ("Daryl Mitchell", "Batting"),
    ("Yash Dhull", "Batting"),
    ("Karan Lal", "Batting"),
    ("Khilan Patel", "Batting"),
    ("Tushar Raheja", "Batting"),
    ("Aaryavir Sehwag", "Batting"),
    ("Anmolpreet Singh", "Batting"),
    ("Bevon Jacobs", "Batting"),
    ("Yajas Sharma", "Batting"),
    ("Aaron Hardie", "Batting"),
    ("Josh Tongue", "Bowling"),
    ("Tanush Kotian", "Bowling"),
    ("Simarjeet Singh", "Bowling"),
    ("Chetan Sakariya", "Bowling"),
    ("Ishant Bharadwaj", "Bowling"),
    ("Gerald Coetzee", "Bowling"),
    ("Shubham Kumar Gupta", "Bowling"),
    ("Shamar Springer", "Bowling"),
    ("Matthew Fisher", "Bowling"),
    ("Mohit Ulva", "Bowling"),
]

def normalize(name):
    return " ".join(str(name).lower().strip().split())

def load_csv(filename):
    return pd.read_csv(BASE / filename, low_memory=False)

registry = load_csv("players_clean.csv")

datasets = {
    "Batting": (
        load_csv("pressure_batting_adjusted.csv"),
        load_csv("pressure_batting_reliability.csv"),
    ),
    "Bowling": (
        load_csv("pressure_bowling_adjusted.csv"),
        load_csv("pressure_bowling_reliability.csv"),
    ),
}

registry["normalized_name"] = registry["player_name"].map(normalize)

rows = []

for name, role in PLAYERS:
    key = normalize(name)

    matches = registry[
        registry["normalized_name"] == key
    ]

    adjusted, reliability = datasets[role]

    if matches.empty:
        suggestions = get_close_matches(
            key,
            registry["normalized_name"].tolist(),
            n=3,
            cutoff=0.75,
        )

        rows.append({
            "player": name,
            "role": role,
            "status": "NOT_FOUND",
            "player_id": None,
            "matches": 0,
            "balls": 0,
            "suggestions": "; ".join(suggestions),
        })
        continue

    for _, player in matches.iterrows():
        pid = player["player_id"]

        performance = adjusted[
            adjusted["player_id"] == pid
        ]

        consistency = reliability[
            reliability["player_id"] == pid
        ]

        status = (
            "BOTH"
            if not performance.empty and not consistency.empty
            else "PARTIAL"
            if not performance.empty or not consistency.empty
            else "REGISTRY_ONLY"
        )

        rows.append({
            "player": name,
            "role": role,
            "status": status,
            "player_id": pid,
            "matches": (
                performance.iloc[0]["matches"]
                if not performance.empty else 0
            ),
            "balls": (
                performance.iloc[0]["balls"]
                if not performance.empty else 0
            ),
            "suggestions": "",
        })

result = pd.DataFrame(rows)

result.to_csv(
    OUTPUT / "player_coverage_audit.csv",
    index=False,
)

print("\n=== PLAYER COVERAGE AUDIT ===")
print(result.to_string(index=False))

print("\n=== COVERAGE SUMMARY ===")
print(result["status"].value_counts().to_string())

print("\nSaved to outputs/player_coverage_audit.csv")
