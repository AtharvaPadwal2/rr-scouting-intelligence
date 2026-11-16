
from pathlib import Path
from datetime import date
import argparse
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "processed" / "rr_official"

QUEUE = DIR / "uncapped_indian_verification_priority.csv"
DOB_REGISTRY = DIR / "uncapped_indian_dob_registry.csv"

parser = argparse.ArgumentParser()
parser.add_argument("--min-age", type=int, default=18)
parser.add_argument("--max-age", type=int, default=25)
parser.add_argument(
    "--role",
    choices=["ALL", "BATTER", "BOWLER"],
    default="ALL"
)
parser.add_argument(
    "--as-of", default="2026-11-10"
)
args = parser.parse_args()

if args.min_age > args.max_age:
    parser.error("Minimum age cannot exceed maximum age.")

as_of = date.fromisoformat(args.as_of)

queue = pd.read_csv(
    QUEUE, dtype={"player_id": str}
)

# One birth-date record per unique player.
registry = (
    queue[["player_id", "candidate_name"]]
    .drop_duplicates("player_id")
    .copy()
)

registry["player_id"] = registry["player_id"].str.strip()

# Preserve existing DOB verification work.
if DOB_REGISTRY.exists():
    old = pd.read_csv(
        DOB_REGISTRY, dtype={"player_id": str}
    )

    old["player_id"] = old["player_id"].str.strip()

    fields = ["date_of_birth", "dob_source_url"]

    for col in fields:
        if col not in old.columns:
            old[col] = ""

    registry = registry.merge(
        old[["player_id"] + fields]
        .drop_duplicates("player_id"),
        on="player_id",
        how="left",
        validate="one_to_one"
    )
else:
    registry["date_of_birth"] = ""
    registry["dob_source_url"] = ""

registry = registry.fillna("")
registry.to_csv(DOB_REGISTRY, index=False)

# Attach verified birth dates.
df = queue.merge(
    registry[
        ["player_id", "date_of_birth", "dob_source_url"]
    ],
    on="player_id",
    how="left",
    validate="many_to_one"
)

dob = pd.to_datetime(
    df["date_of_birth"],
    format="%Y-%m-%d",
    errors="coerce"
)

# Require a source and a valid birth date.
source_verified = (
    df["dob_source_url"]
    .fillna("")
    .astype(str)
    .str.match(r"^https?://", case=False)
)

valid = (
    dob.notna()
    & source_verified
    & (dob <= pd.Timestamp(as_of))
)

# Calculate completed years of age.
def calculate_age(birth_date):
    if pd.isna(birth_date):
        return pd.NA

    born = birth_date.date()

    if born > as_of:
        return pd.NA

    return (
        as_of.year - born.year
        - (
            (as_of.month, as_of.day)
            < (born.month, born.day)
        )
    )

df["age"] = dob.apply(calculate_age).astype("Int64")
df.loc[~valid, "age"] = pd.NA

df["age_verification"] = "REVIEW"
df.loc[valid, "age_verification"] = "DOB_SOURCED"

# Filter by category.
if args.role != "ALL":
    df = df[df["role"].eq(args.role)].copy()

# Keep missing ages out of the age-filtered output.
filtered = df[
    df["age"].between(args.min_age, args.max_age)
].copy()

filtered = filtered.sort_values(
    ["role", "scouting_score"],
    ascending=[True, False]
)

# Important: DOB verification is not auction eligibility.
filtered["auction_eligibility"] = "UNVERIFIED"

output = DIR / (
    f"uncapped_age_{args.min_age}_"
    f"{args.max_age}_{args.role.lower()}.csv"
)

filtered.to_csv(output, index=False)

print("\n=== AGE FILTER ===")
print(f"Age range: {args.min_age}-{args.max_age}")
print(f"As of: {as_of}")
print(f"Role: {args.role}")
print("Candidates checked:", len(df))
print("With sourced DOB:", int(df["age"].notna().sum()))
print("Missing/unverified DOB:", int(df["age"].isna().sum()))
print("Matching age range:", len(filtered))

print("\n=== MATCHING PLAYERS ===")

if filtered.empty:
    print(
        "No age-verified matches yet. "
        "Fill DOB registry with sourced dates."
    )
else:
    print(
        filtered[
            [
                "candidate_name",
                "role",
                "age",
                "scouting_score",
                "verification_status"
            ]
        ].head(30).to_string(index=False)
    )

print("\nDOB registry:", DOB_REGISTRY)
print("Filtered output:", output)
print(
    "\nWARNING: Age verification alone does not "
    "confirm uncapped or unattached status."
)
