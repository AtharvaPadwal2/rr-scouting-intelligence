import altair as alt
import pandas as pd
import streamlit as st


RR_PINK = "#EA1A85"
RR_BLUE = "#1A3789"
ROLE_COLORS = [RR_PINK, RR_BLUE, "#8B5CF6", "#0F766E", "#C2410C", "#64748B"]

METRICS = {
    "Batting strike rate": "calculated_batting_strike_rate",
    "Bowling economy": "calculated_bowling_economy",
    "Runs": "runs",
    "Wickets": "wickets",
}


def render_analytics(upload_name, imported_data):
    st.subheader("Scouting Analytics")
    st.caption(
        f"{upload_name} · Each record represents a player-season in the demo dataset."
    )
    data = imported_data.copy()

    bowling_columns = {"runs_conceded", "legal_balls_bowled"}
    if bowling_columns.issubset(data.columns):
        conceded = pd.to_numeric(data["runs_conceded"], errors="coerce")
        balls = pd.to_numeric(data["legal_balls_bowled"], errors="coerce")
        valid = conceded.ge(0) & balls.gt(0)
        data["calculated_bowling_economy"] = (
            conceded.where(valid).mul(6).div(balls.where(valid)).round(2)
        )

    metrics = {}
    for label, column in METRICS.items():
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")
            metrics[label] = column

    if not metrics:
        st.info("This upload has no supported batting or bowling metric columns.")
        return

    data["season"] = data["season"].astype("string").fillna("Unknown")
    data["role"] = data["role"].astype("string").fillna("Unknown").str.capitalize()

    season_box, role_box, metric_box, order_box = st.columns(4)
    seasons = sorted(data["season"].unique(), reverse=True)
    selected_seasons = season_box.multiselect("Season · empty means all", seasons)
    selected_roles = role_box.multiselect(
        "Role · empty means all", sorted(data["role"].unique())
    )
    metric = metric_box.selectbox("Rank by", list(metrics))
    order = order_box.radio(
        "Order", ["High to low", "Low to high"],
        index=int(metric == "Bowling economy"),
        key=f"analytics_order_{metrics[metric]}",
        horizontal=True,
    )

    if selected_seasons:
        data = data.loc[data["season"].isin(selected_seasons)]
    if selected_roles:
        data = data.loc[data["role"].isin(selected_roles)]

    data = data.assign(value=data[metrics[metric]])
    ranked = data.dropna(subset=["value"]).sort_values(
        "value", ascending=order == "Low to high", kind="stable"
    )

    players, records, usable = st.columns(3)
    players.metric("Unique players", data["player_id"].nunique())
    records.metric("Filtered records", len(data))
    usable.metric("Records with selected metric", len(ranked))

    if data.empty:
        st.info("No records match these filters.")
        return

    role_counts = data.groupby("role", as_index=False).size()
    donut = alt.Chart(role_counts).mark_arc(innerRadius=55).encode(
        theta="size:Q",
        color=alt.Color("role:N", title="Role", scale=alt.Scale(range=ROLE_COLORS)),
        tooltip=[
            alt.Tooltip("role:N", title="Role"),
            alt.Tooltip("size:Q", title="Player-season records"),
        ],
    )

    left, right = st.columns([1, 2])
    left.subheader("Role distribution")
    left.altair_chart(donut.properties(height=300), width="stretch")

    right.subheader("First 12 ranked records")
    if ranked.empty:
        right.info(f"No usable values for {metric} in these filters.")
        return

    top = ranked.head(12).copy()
    top["entry"] = (
        top["player_name"].astype("string").fillna("Unnamed player")
        + " · " + top["season"]
    )

    bars = alt.Chart(top).mark_bar(color=RR_PINK, cornerRadiusEnd=4).encode(
        x=alt.X("value:Q", title=metric),
        y=alt.Y(
            "entry:N",
            title=None,
            sort=alt.SortField("value", order="ascending" if order == "Low to high" else "descending"),
        ),
        tooltip=[
            alt.Tooltip("entry:N", title="Player and season"),
            alt.Tooltip("role:N", title="Role"),
            alt.Tooltip("value:Q", title=metric, format=".2f"),
        ],
    )
    right.altair_chart(bars.properties(height=300), width="stretch")

    trend = ranked.groupby("season", as_index=False)["value"].median()
    st.subheader(f"Season trend · Median {metric.lower()}")
    line = alt.Chart(trend).mark_line(color=RR_BLUE, point=True).encode(
        x=alt.X("season:O", title="Season"),
        y=alt.Y("value:Q", title=f"Median {metric.lower()}"),
        tooltip=["season:O", alt.Tooltip("value:Q", title="Median", format=".2f")],
    )
    st.altair_chart(line.properties(height=240), width="stretch")

    batting = "calculated_batting_strike_rate"
    bowling = "calculated_bowling_economy"
    if {batting, bowling}.issubset(data.columns):
        two_way = data.dropna(subset=[batting, bowling])
        if not two_way.empty:
            st.subheader("Batting strike rate vs bowling economy")
            scatter = alt.Chart(two_way).mark_circle(size=75, opacity=0.7).encode(
                x=alt.X(f"{batting}:Q", title="Batting strike rate", scale=alt.Scale(zero=False)),
                y=alt.Y(f"{bowling}:Q", title="Bowling economy", scale=alt.Scale(zero=False)),
                color=alt.Color(
                    "role:N", title="Role",
                    scale=alt.Scale(domain=sorted(data["role"].unique()), range=ROLE_COLORS),
                ),
                tooltip=[
                    "player_name:N", "season:O", "role:N",
                    alt.Tooltip(f"{batting}:Q", title="Strike rate", format=".2f"),
                    alt.Tooltip(f"{bowling}:Q", title="Economy", format=".2f"),
                ],
            )
            st.altair_chart(scatter.properties(height=330).interactive(), width="stretch")

    st.subheader("Filtered records")
    st.caption("Click a table header to sort the table. Use Rank by and Order to update the chart.")
    st.dataframe(
        ranked[["player_name", "season", "role", "value"]].rename(columns={"value": metric}),
        hide_index=True,
        width="stretch",
    )