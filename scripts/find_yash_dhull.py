
from pathlib import Path
import re
import pandas as pd

ROOT = Path("data")
OUTPUT = Path("data/processed/yash_dhull_search_summary.csv")

# Common naming variants
ALIASES = re.compile(
    r"\b(?:"
    r"yash\s+(?:d\.?\s+)?dhull|"
    r"y\.?\s*dhull|"
    r"dhull\s*,?\s*yash|"
    r"dhull\s*,?\s*y\.?"
    r")\b",
    re.IGNORECASE,
)

NAME_HINTS = (
    "player", "name", "batter", "batsman",
    "striker", "bowler", "dismissed", "wicket"
)

results = []
files = sorted(ROOT.rglob("*.csv"))

print(f"Scanning {len(files)} CSV files...\n")

for path in files:
    total_matches = 0
    matched_columns = set()
    preview_rows = []

    try:
        for chunk in pd.read_csv(
            path,
            chunksize=20000,
            dtype=str,
            low_memory=False
        ):
            name_cols = [
                col for col in chunk.columns
                if any(h in col.lower() for h in NAME_HINTS)
                and not col.lower().endswith("_id")
            ]

            if not name_cols:
                continue

            matched = pd.Series(False, index=chunk.index)

            for col in name_cols:
                mask = chunk[col].fillna("").str.contains(
                    ALIASES, regex=True, na=False
                )

                if mask.any():
                    matched_columns.add(col)
                    matched = matched | mask

            rows = chunk.loc[matched]
            total_matches += len(rows)

            if len(preview_rows) < 3:
                preview_rows.extend(
                    rows.head(3 - len(preview_rows))
                    .to_dict("records")
                )

    except Exception as exc:
        print(f"[ERROR] {path}: {exc}")
        continue

    if total_matches == 0:
        continue

    print("=" * 72)
    print(f"FOUND: {path}")
    print(f"Matching rows: {total_matches}")
    print(f"Name columns: {', '.join(sorted(matched_columns))}")

    for row in preview_rows:
        useful = {
            key: value
            for key, value in row.items()
            if any(word in key.lower() for word in (
                "name", "player", "season", "team", "match",
                "runs", "balls", "strike", "average",
                "boundary", "four", "six", "pressure",
                "phase", "date", "competition"
            ))
            and not key.lower().endswith("_id")
        }

        print("Preview:", str(useful)[:700])

    results.append({
        "file": str(path),
        "matching_rows": total_matches,
        "matched_columns": ", ".join(
            sorted(matched_columns)
        ),
    })

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

pd.DataFrame(
    results,
    columns=["file", "matching_rows", "matched_columns"]
).to_csv(OUTPUT, index=False)

print("\n" + "=" * 72)
print("SEARCH COMPLETE")
print(f"CSV files scanned: {len(files)}")
print(f"Files containing player: {len(results)}")
print(f"Summary saved to: {OUTPUT}")

if not results:
    print(
        "No alias matches. Check whether other files "
        "use numeric player IDs without names."
    )
