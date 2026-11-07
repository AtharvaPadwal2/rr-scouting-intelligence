"""Local Streamlit entry point for RR Scouting Intelligence."""

from zipfile import BadZipFile

import pandas as pd
import streamlit as st

from scouting.analytics import render_analytics
from scouting.importer import read_scouting_file
from scouting.synthetic import generate_players


SCOUTING_FIELDS = {
    "player_id": "Player ID",
    "player_name": "Player name",
    "season": "Season",
    "age_at_season_end": "Age at season end",
    "role": "Playing role",
}

ANALYTICS_UPLOAD_KEY = "analytics_upload"


@st.cache_data
def load_demo():
    """Cache the generated demonstration dataset."""
    return generate_players()


def render_overview(data):
    st.subheader("Scouting overview")

    players, seasons, records = st.columns(3)
    players.metric("Fictional players", data["player_id"].nunique(), border=True)
    seasons.metric("Seasons", data["season"].nunique(), border=True)
    records.metric("Raw records", len(data), border=True)

    st.subheader("Players by role")
    roles = data[["player_id", "role"]].assign(
        role=data["role"].str.strip().str.title()
    )
    role_counts = roles.drop_duplicates()["role"].value_counts()
    st.bar_chart(role_counts, color="#EA1A85", horizontal=True)


def render_synthetic_dataset(data):
    st.subheader("Synthetic dataset")
    season = st.selectbox("Season", sorted(data["season"].unique(), reverse=True))

    st.caption(
        "Raw preview. The generator deliberately adds a duplicate, "
        "a missing value, an inconsistent role label and a negative run total."
    )

    duplicates, missing, invalid = st.columns(3)
    duplicates.metric("Duplicate rows", int(data.duplicated().sum()), border=True)
    missing.metric("Missing balls faced", int(data["balls_faced"].isna().sum()), border=True)
    invalid.metric("Negative run totals", int(data["runs"].lt(0).sum()), border=True)

    st.dataframe(data.loc[data["season"].eq(season)], hide_index=True)
    st.download_button(
        "Download all synthetic records",
        data.to_csv(index=False),
        file_name="synthetic_rr_players.csv",
        mime="text/csv",
        type="primary",
    )


def valid_whole_numbers(values, minimum):
    numbers = pd.to_numeric(values, errors="coerce")
    return (
        numbers.ge(minimum)
        & numbers.lt(2**63)
        & numbers.mod(1).eq(0)
    ).fillna(False)


def render_data_quality_report(imported_data, mapped_data):
    st.subheader("Data quality report")

    age = mapped_data["age_at_season_end"]
    role = mapped_data["role"].astype("string").dropna()
    normalized_role = role.str.strip().str.casefold()
    role_variants = role.groupby(normalized_role).nunique()

    checks = {
        "Exact duplicate rows": int(imported_data.duplicated().sum()),
        "Missing or invalid ages": int((~valid_whole_numbers(age, minimum=1)).sum()),
        "Roles with inconsistent casing or spacing": int(role_variants.gt(1).sum()),
    }

    if "balls_faced" in imported_data.columns:
        checks["Missing balls faced"] = int(imported_data["balls_faced"].isna().sum())

    if "runs" in imported_data.columns:
        runs = pd.to_numeric(imported_data["runs"], errors="coerce")
        checks["Negative run totals"] = int(runs.lt(0).sum())

    st.dataframe(
        pd.DataFrame(list(checks.items()), columns=["Check", "Count"]),
        hide_index=True,
    )


def render_import_dataset():
    st.subheader("Import dataset")
    st.caption("Preview a CSV or the first worksheet of an XLSX file.")

    # Publish data to Analytics only after the current upload and mapping pass.
    st.session_state.pop(ANALYTICS_UPLOAD_KEY, None)
    uploaded_file = st.file_uploader(
        "Choose a scouting file",
        type=["csv", "xlsx"],
    )
    if uploaded_file is None:
        return

    try:
        imported_data = read_scouting_file(
            uploaded_file.name,
            uploaded_file.getvalue(),
        )
    except (ValueError, OSError, BadZipFile) as error:
        st.error(f"Could not read the file. {error}")
        return

    rows, columns = st.columns(2)
    rows.metric("Rows", len(imported_data))
    columns.metric("Columns", len(imported_data.columns))
    st.caption("Showing up to 100 raw rows.")
    st.dataframe(imported_data.head(100), hide_index=True)

    if imported_data.empty:
        st.info("This file has no data rows to analyse.")
        return

    st.subheader("Map scouting columns")
    source_columns = list(imported_data.columns)
    options = [None, *source_columns]
    mapping = {}

    for field, label in SCOUTING_FIELDS.items():
        default_index = options.index(field) if field in source_columns else 0
        mapping[field] = st.selectbox(
            label,
            options,
            index=default_index,
            format_func=lambda column: "Select a column" if column is None else str(column),
            key=f"import_mapping_{field}",
        )

    selected_columns = [column for column in mapping.values() if column is not None]

    if len(selected_columns) != len(set(selected_columns)):
        st.error("Choose a different source column for each scouting field.")
        return

    if len(selected_columns) != len(SCOUTING_FIELDS):
        st.info("Select a source column for each field to see the mapped preview.")
        return

    mapped_data = imported_data.loc[:, selected_columns].copy()
    mapped_data.columns = list(SCOUTING_FIELDS)

    st.caption("Mapped preview · First 10 rows")
    st.dataframe(mapped_data.head(10), hide_index=True)

    render_data_quality_report(imported_data, mapped_data)

    st.subheader("Cleaned dataset preview")
    cleaned_data = imported_data.drop_duplicates().copy()

    role_column = mapping["role"]
    cleaned_data[role_column] = (
        cleaned_data[role_column].astype("string").str.strip().str.casefold()
    )

    age_column = mapping["age_at_season_end"]
    age = pd.to_numeric(cleaned_data[age_column], errors="coerce")
    cleaned_data[age_column] = age.where(
        valid_whole_numbers(age, minimum=1)
    ).astype("Int64")

    for batting_column in ("runs", "balls_faced"):
        if batting_column in cleaned_data.columns:
            values = pd.to_numeric(cleaned_data[batting_column], errors="coerce")
            cleaned_data[batting_column] = values.where(
                valid_whole_numbers(values, minimum=0)
            ).astype("Int64")

    if {"runs", "balls_faced"}.issubset(cleaned_data.columns):
        runs = cleaned_data["runs"]
        balls_faced = cleaned_data["balls_faced"]
        valid_strike_rate = runs.notna() & balls_faced.gt(0).fillna(False)

        st.metric("Rows usable for batting strike rate", int(valid_strike_rate.sum()))
        cleaned_data["calculated_batting_strike_rate"] = (
            runs.where(valid_strike_rate)
            .div(balls_faced.where(valid_strike_rate))
            .mul(100)
            .round(2)
        )

    st.metric("Rows after removing exact duplicates", len(cleaned_data))
    st.caption("Showing the first 10 cleaned rows.")
    st.dataframe(cleaned_data.head(10), hide_index=True)

    analytics_data = cleaned_data.assign(
        **{field: cleaned_data[source] for field, source in mapping.items()}
    )
    st.session_state[ANALYTICS_UPLOAD_KEY] = (uploaded_file.name, analytics_data)


def main():
    st.set_page_config(
        page_title="RR Scouting Intelligence",
        page_icon="🏏",
        layout="wide",
    )

    page = st.sidebar.radio(
        "Scouting workspace",
        ["Overview", "Synthetic Dataset", "Import Dataset", "Scouting Analytics"],
    )
    st.sidebar.caption("RR Scouting Intelligence · IPL 2027")

    st.title("RR Scouting Intelligence")
    st.caption("Rajasthan Royals auction scouting workspace")

    if page in ("Overview", "Synthetic Dataset"):
        st.warning(
            "Synthetic data only. All players, teams and performances "
            "shown here are fictional."
        )

    if page == "Overview":
        render_overview(load_demo())
    elif page == "Synthetic Dataset":
        render_synthetic_dataset(load_demo())
    elif page == "Import Dataset":
        render_import_dataset()
    elif page == "Scouting Analytics":
        analytics_upload = st.session_state.get(ANALYTICS_UPLOAD_KEY)
        if analytics_upload is None:
            st.info("Upload and map a file under Import Dataset first.")
        else:
            render_analytics(*analytics_upload)


if __name__ == "__main__":
    main()