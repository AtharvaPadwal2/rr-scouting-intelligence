
from pathlib import Path
from datetime import date
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "rr_official"
OUTPUT = ROOT / "frontend" / "public" / "data" / "uncapped-overview.json"

AS_OF = date(2026, 11, 10)

SOURCES = {
    "BATTER": DATA / "smat_batting_manual_review.csv",
    "BOWLER": DATA / "smat_bowling_manual_review.csv",
}

def read_optional(path):
    if path.exists():
        return pd.read_csv(
            path,
            dtype={"player_id": str},
            low_memory=False
        )
    return pd.DataFrame()

def clean_id(df):
    df = df.copy()
    if "player_id" in df.columns:
        df["player_id"] = df["player_id"].astype(str).str.strip()
    return df

queue = clean_id(read_optional(
    DATA / "uncapped_indian_verification_priority.csv"
))

dob_registry = clean_id(read_optional(
    DATA / "uncapped_indian_dob_registry.csv"
))

# One identity record per player.
if not dob_registry.empty:
    dob_registry = dob_registry.drop_duplicates("player_id")

def age_from_dob(value):
    if pd.isna(value) or not str(value).strip():
        return None

    try:
        born = date.fromisoformat(str(value).strip())
        if born > AS_OF:
            return None

        return (
            AS_OF.year - born.year
            - ((AS_OF.month, AS_OF.day) < (born.month, born.day))
        )
    except ValueError:
        return None

def build(role, path):
    df = clean_id(pd.read_csv(
        path,
        dtype={"player_id": str},
        low_memory=False
    ))

    df["role_group"] = role

    # Attach manually researched DOB records.
    if not dob_registry.empty:
        columns = [
            c for c in [
                "player_id",
                "date_of_birth",
                "dob_source_url"
            ] if c in dob_registry.columns
        ]

        if "date_of_birth" in columns:
            df = df.drop(
                columns=["date_of_birth", "dob_source_url"],
                errors="ignore"
            ).merge(
                dob_registry[columns],
                on="player_id",
                how="left",
                validate="many_to_one"
            )

    # Attach current verification queue data.
    if not queue.empty:
        review_fields = [
            "player_id",
            "role",
            "verification_status",
            "nationality_check",
            "uncapped_check",
            "ipl_contract_check",
            "auction_2026_status",
            "auction_evidence_url",
            "evidence_url",
            "verification_note",
        ]

        available = [
            c for c in review_fields if c in queue.columns
        ]

        if {"player_id", "role"}.issubset(available):
            review = queue[available].drop_duplicates(
                ["player_id", "role"]
            )

            df = df.drop(
                columns=[
                    c for c in available
                    if c not in ("player_id", "role")
                ],
                errors="ignore"
            ).merge(
                review,
                left_on=["player_id", "role_group"],
                right_on=["player_id", "role"],
                how="left",
                validate="many_to_one"
            )

    if "date_of_birth" not in df:
        df["date_of_birth"] = ""

    if "dob_source_url" not in df:
        df["dob_source_url"] = ""

    # A sourced birth date is required for age filtering.
    sourced = (
        df["dob_source_url"]
        .fillna("")
        .astype(str)
        .str.match(r"^https?://", case=False)
    )

    df["age"] = df["date_of_birth"].apply(age_from_dob)
    df.loc[~sourced, "age"] = None

    def get_name(row):
        for col in [
            "resolved_name",
            "candidate_name",
            "player_name",
            "registry_name"
        ]:
            value = row.get(col)
            if pd.notna(value) and str(value).strip():
                return str(value).strip()
        return "Unknown"

    df["display_name"] = df.apply(get_name, axis=1)

    for col in [
        "nationality_check",
        "uncapped_check",
        "ipl_contract_check",
        "verification_status"
    ]:
        if col not in df:
            df[col] = "REVIEW"
        df[col] = df[col].fillna("REVIEW")

    # Only explicit verification of all three conditions
    # qualifies a player for the confirmed shortlist.
    df["verified_eligible"] = (
        df["nationality_check"].astype(str).str.upper().eq("YES")
        & df["uncapped_check"].astype(str).str.upper().eq("YES")
        & df["ipl_contract_check"].astype(str).str.upper().isin(
            ["NO", "UNATTACHED"]
        )
        & df["evidence_url"].fillna("").astype(str)
            .str.match(r"^https?://", case=False)
        if "evidence_url" in df.columns
        else False
    )

    return df.sort_values(
        "scouting_score", ascending=False
    )

batters = build("BATTER", SOURCES["BATTER"])
bowlers = build("BOWLER", SOURCES["BOWLER"])

def records(df):
    return json.loads(df.to_json(orient="records"))

payload = {
    "metadata": {
        "title": "Uncapped Indian Scouting",
        "asOf": AS_OF.isoformat(),
        "agePolicy": "Verified DOB only",
        "dataCoverage": "Historical available SMAT records through 2024/25",
        "eligibilityWarning": (
            "Manual review candidates are not confirmed "
            "uncapped or currently unattached."
        ),
    },
    "batters": records(batters),
    "bowlers": records(bowlers),
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("\n=== UNCAPPED DASHBOARD EXPORT ===")
print("Batting reviews:", len(batters))
print("Bowling reviews:", len(bowlers))
print("Age verified:", int(
    batters["age"].notna().sum()
    + bowlers["age"].notna().sum()
))
print("Eligible batting records:", int(
    batters["verified_eligible"].sum()
))
print("Eligible bowling records:", int(
    bowlers["verified_eligible"].sum()
))
print("Exported:", OUTPUT)
