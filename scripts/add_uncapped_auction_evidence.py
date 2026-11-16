
from pathlib import Path
import pandas as pd

DIR = Path("data/processed/rr_official")
path = DIR / "uncapped_indian_verification_priority.csv"

df = pd.read_csv(path, dtype={"player_id": str})

# Historical 2026 auction evidence, NOT a live contract check.
evidence = {
    "Anmolpreet Singh": "Anmolpreet Singh",
    "Atharva Taide": "Atharva Taide",
    "YV Dhull": "Yash Dhull",
    "Tanush Kotian": "Tanush Kotian",
    "Mayank Dagar": "Mayank Dagar",
    "CV Milind": "Chama Milind",
}

source = (
    "https://www.wisden.com/series/ipl-2026/"
    "cricket-news/ipl-2026-auction-complete-list-of-players-unsold"
)

# Preserve the existing verification data.
if "auction_2026_status" not in df.columns:
    df["auction_2026_status"] = "NOT_CHECKED"

if "auction_evidence_url" not in df.columns:
    df["auction_evidence_url"] = ""

if "identity_verification" not in df.columns:
    df["identity_verification"] = "REVIEW"

df["candidate_name"] = df["candidate_name"].astype(str).str.strip()

for dataset_name, auction_name in evidence.items():
    mask = df["candidate_name"].eq(dataset_name)

    df.loc[mask, "auction_2026_status"] = (
        "UNCAPPED_UNSOLD_2026"
    )
    df.loc[mask, "auction_evidence_url"] = source

    if dataset_name != auction_name:
        df.loc[mask, "identity_verification"] = (
            f"VERIFY_ALIAS: {auction_name}"
        )

# Never infer current contract status from old auction data.
df.to_csv(path, index=False)

print("\n=== AUCTION EVIDENCE ADDED ===")
print(
    df[df["auction_2026_status"].eq("UNCAPPED_UNSOLD_2026")][
        [
            "candidate_name",
            "role",
            "scouting_score",
            "auction_2026_status",
            "identity_verification",
        ]
    ].to_string(index=False)
)

print("\nCurrent contract status remains unverified.")
print("Saved:", path)
