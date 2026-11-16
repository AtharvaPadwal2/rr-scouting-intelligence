
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/processed/rr_official"

files = {
    "BATTER": DIR / "smat_batting_manual_review.csv",
    "BOWLER": DIR / "smat_bowling_manual_review.csv"
}

# Names requiring identity resolution before eligibility decisions.
IDENTITY_REVIEW = {
    "A Badoni": "Possibly Ayush Badoni (LSG)",
    "VR Iyer": "Possibly Venkatesh Iyer (RCB)",
    "S Dube": "Possibly Shivam Dube (CSK)",
    "Mohsin Khan (2)": "Check against Mohsin Khan (LSG)",
}

results = []

for role, path in files.items():
    df = pd.read_csv(path, dtype={"player_id": str})

    # Existing script may provide resolved_name.
    name_col = (
        "resolved_name"
        if "resolved_name" in df.columns
        else "player_name"
    )

    required = {"player_id", "scouting_score", name_col}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"{path.name} missing columns: {missing}"
        )

    df = df.copy()
    df["role"] = role
    df["candidate_name"] = df[name_col].astype(str)

    df["identity_flag"] = (
        df["candidate_name"]
        .map(IDENTITY_REVIEW)
        .fillna("")
    )

    df["verification_status"] = "REVIEW"
    df["nationality_check"] = "REVIEW"
    df["uncapped_check"] = "REVIEW"
    df["ipl_contract_check"] = "REVIEW"
    df["evidence_url"] = ""
    df["verification_note"] = ""

    df = df.sort_values(
        "scouting_score", ascending=False
    )

    results.append(df[[
        "player_id",
        "candidate_name",
        "role",
        "scouting_score",
        "identity_flag",
        "verification_status",
        "nationality_check",
        "uncapped_check",
        "ipl_contract_check",
        "evidence_url",
        "verification_note"
    ]])

combined = pd.concat(
    results, ignore_index=True
)

# Retain separate batting and bowling rows for all-rounders.
combined = combined.sort_values(
    ["role", "scouting_score"],
    ascending=[True, False]
)

output = DIR / "uncapped_indian_verification_priority.csv"

# Preserve existing manual work.
if output.exists():
    old = pd.read_csv(
        output, dtype={"player_id": str}
    )

    editable = [
        "verification_status",
        "nationality_check",
        "uncapped_check",
        "ipl_contract_check",
        "evidence_url",
        "verification_note"
    ]

    old = old.drop_duplicates(
        ["player_id", "role"]
    )

    combined = combined.merge(
        old[["player_id", "role"] + editable],
        on=["player_id", "role"],
        how="left",
        suffixes=("", "_old")
    )

    for col in editable:
        previous = col + "_old"
        combined[col] = combined[previous].fillna(
            combined[col]
        )
        combined = combined.drop(columns=previous)

combined.to_csv(output, index=False)

print("\n=== VERIFICATION QUEUE ===")
print(
    combined.groupby("role").size().to_string()
)

print("\n=== IDENTITY WARNINGS ===")
warnings = combined[
    combined["identity_flag"].ne("")
]

print(
    warnings[[
        "candidate_name", "role", "identity_flag"
    ]].to_string(index=False)
)

print("\nSaved:", output)
print("All eligibility fields remain unverified.")
