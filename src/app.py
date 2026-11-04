"""
app.py - the Streamlit dashboard (one scrolling page).

Run from the project folder:   streamlit run src/app.py

Page layout (top to bottom):
    1. Welcome
    2. Behaviour insights   (features live in behavior_insights.py)
    3. Space for teammates' sections

Every section is a function that is handed the data it needs, so it is easy to add more.
    df       = the person's days inside the sidebar period
    all_data = all of the person's days
"""

import plotly.express as px
import pandas as pd
import streamlit as st

import behavior_insights as bi
from load_data import LABELS, PERSON_ID, USER_NAME, load_user_metrics, show

from wellness_tracker import wellness_tracker, GOALS, COLOURS, RINGS
from drill_down_function import build_daily_goal_drilldown
from derived_features import derived_features_section, walking_features_section

st.set_page_config(page_title="Fitbit Dashboard", layout="wide")


@st.cache_data
def get_user_data(user_id):
    """Load once and cache, so changing a filter only re-runs the charts (fast)."""
    return load_user_metrics(user_id)


def fmt_date(date):
    return pd.Timestamp(date).strftime("%a %d %b %Y")


# Each chart needs its own key: two "No data" charts can look identical, and Streamlit
# would complain about duplicate IDs.


# ----------------------------------------------------------------------------
# 1. Welcome
# ----------------------------------------------------------------------------
def welcome_section(df, start, end, last_day):
    st.title(f"Welcome back, {USER_NAME}!")
    st.write(f"Here is your activity for **{fmt_date(start)}** to **{fmt_date(end)}**.")
    cols = st.columns(4)
    cols[0].metric("Days with data", int(df["steps"].notna().sum()))
    for col, metric in zip(cols[1:], bi.CORE_METRICS):
        col.metric(
            f"Avg {LABELS[metric].lower()} / day", show(df[metric].mean(), metric)
        )
    st.caption(
        f"Data runs to {fmt_date(last_day)}. Use the sidebar to change the period."
    )


# ----------------------------------------------------------------------------
# 2. Behaviour insights - one small function per feature
# ----------------------------------------------------------------------------
def weekday_weekend_section(df):
    st.subheader("Weekdays vs weekends")
    st.caption("Average per day. Days with no data are left out.")
    insight = bi.weekday_weekend_insight(df)
    if insight:
        st.info(insight, icon=":material/lightbulb:")
    st.plotly_chart(
        bi.weekday_weekend_chart(df), width="stretch", key="weekday_weekend_chart"
    )


def best_worst_section(df):
    st.subheader("Best and worst day")
    best_worst = bi.best_worst_days(df)
    for col, row in zip(st.columns(len(best_worst)), best_worst.itertuples()):
        col.markdown(f"**{LABELS[row.metric]}**")
        if pd.isna(row.best_value):
            col.write("No data")
        else:
            col.markdown(
                f":green[Best] {show(row.best_value, row.metric)}  \n{row.best_date:%a %d %b}"
            )
            col.markdown(
                f":red[Worst] {show(row.worst_value, row.metric)}  \n{row.worst_date:%a %d %b}"
            )
    metric = st.selectbox(
        "Show daily values for",
        bi.ALL_METRICS,
        format_func=LABELS.get,
        key="best_worst_metric",
    )
    st.plotly_chart(
        bi.best_worst_chart(df, metric), width="stretch", key="best_worst_chart"
    )


def activity_levels_section(df):
    st.subheader("Time at each activity level")
    st.caption(
        "Averages for the period, then each day as one bar split by the share of the day at each level."
    )
    totals = bi.activity_level_totals(df)
    if totals.empty:
        st.write("No data")
    else:
        for col, row in zip(st.columns(4), totals.itertuples()):
            col.metric(
                row.level,
                f"{row.avg_minutes:,.0f} min/day",
                f"{row.share_pct:.0f}% of tracked time",
                delta_color="off",
            )
    st.plotly_chart(
        bi.activity_levels_chart(df), width="stretch", key="activity_levels_chart"
    )


def unusual_days_section(df, all_data):
    st.subheader("Unusual days vs your usual level")
    st.caption(
        "Compared with your average over all your data. The three most unusual days in this period:"
    )
    insights = bi.unusual_day_insights(df, baseline=all_data)
    if not insights:
        st.write("No unusual days in this period.")
    for item in insights:
        icon = (
            ":material/trending_up:"
            if item["direction"] == "Increase"
            else ":material/trending_down:"
        )
        st.info(item["text"], icon=icon)

    st.caption(
        f"Explore a metric. The shaded band is your usual range; "
        f"big dots are days more than {bi.Z_THRESHOLD} standard deviations away."
    )
    metric = st.selectbox(
        "Metric", bi.ALL_METRICS, format_func=LABELS.get, key="change_metric"
    )
    st.plotly_chart(
        bi.significant_change_chart(df, metric, baseline=all_data),
        width="stretch",
        key="significant_change_chart",
    )


def compare_periods_section(all_data, start, end):
    st.subheader("Compare two periods")
    st.caption(
        "Did you improve or decline? Higher is treated as better. "
        "The periods start as the two halves of the selected period."
    )
    first_day, last_day = all_data["Date"].min().date(), all_data["Date"].max().date()
    half = (end - start).days // 2
    col_a, col_b = st.columns(2)
    period_a = col_a.date_input(
        "Period A",
        value=(start, start + pd.Timedelta(days=half)),
        min_value=first_day,
        max_value=last_day,
    )
    period_b = col_b.date_input(
        "Period B",
        value=(start + pd.Timedelta(days=half + 1), end),
        min_value=first_day,
        max_value=last_day,
    )
    if len(period_a) != 2 or len(period_b) != 2:
        st.info("Pick a start and end date for both periods.")
        return

    summary = bi.compare_periods(all_data, period_a, period_b)
    for col, row in zip(st.columns(len(summary)), summary.itertuples()):
        if row.trend == "No data":
            col.metric(LABELS[row.metric], "No data")
        else:
            col.metric(
                LABELS[row.metric],
                show(row.avg_b, row.metric),
                f"{row.change_pct:+.1f}% - {row.trend}",
            )
    st.plotly_chart(
        bi.compare_periods_chart(summary), width="stretch", key="compare_periods_chart"
    )


def behavior_insights_section(df, all_data, start, end):
    st.divider()
    st.header("Behaviour insights")
    weekday_weekend_section(df)
    best_worst_section(df)
    activity_levels_section(df)
    unusual_days_section(df, all_data)
    compare_periods_section(all_data, start, end)


# ----------------------------------------------------------------------------
# Page: load data, sidebar filter, then the sections from top to bottom
# ----------------------------------------------------------------------------
all_data = get_user_data(PERSON_ID)
if all_data.empty:
    st.error(
        f"No data found for user {PERSON_ID}. Check FITBIT_PERSON_ID and the datafolders folder."
    )
    st.stop()

first_day, last_day = all_data["Date"].min().date(), all_data["Date"].max().date()

with st.sidebar:
    st.header("Filters")
    picked = st.date_input(
        "Period", value=(first_day, last_day), min_value=first_day, max_value=last_day
    )
    st.caption(f"Showing {USER_NAME} (ID {PERSON_ID})")

if len(picked) != 2:
    st.info("Pick an end date to apply the period filter.")
    st.stop()
start, end = picked
df = all_data[
    (all_data["Date"] >= pd.Timestamp(start)) & (all_data["Date"] <= pd.Timestamp(end))
]

welcome_section(df, start, end, last_day)

if df.empty:
    st.warning("No data for the selected period.")
    st.stop()

behavior_insights_section(df, all_data, start, end)



# ----------------------------------------------------------------------------
# wellness tracker
# ----------------------------------------------------------------------------

st.divider()
st.header("Wellness tracker")
st.caption(
    f"Daily Fitbit activity for {USER_NAME} (ID {PERSON_ID}) "
    f"from {first_day:%d %b %Y} to {last_day:%d %b %Y}"
)

# colour key, with each ring's daily goal
key = " &nbsp;&nbsp; ".join(
    f'<span style="color:{COLOURS[name]}; font-size:1.2em">&#9679;</span> {name} (goal {GOALS[name]:,})'
    for name in RINGS
)
st.markdown(
    f"{key}<br>"
    "<small>Rings run from outer to inner. A full ring means the daily goal was reached. "
    "Days with no data are left blank.</small>",
    unsafe_allow_html=True,
)

wellness_tracker(df, picked)

# ----------------------------------------------------------------------------
# Daily Goal Drill-Down
# ----------------------------------------------------------------------------

def daily_goal_drilldown_section():

    st.divider()
    st.header("Daily Goal Drill-Down")

    st.caption(
        f"Goal performance from {start:%d %b %Y} to {end:%d %b %Y}"
    )

    # User-configurable goals (R01 + R25)
    st.subheader("Goal Settings")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        step_goal = st.number_input(
            "Steps",
            min_value=1000,
            value=10000,
            step=500,
        )

    with col2:
        calorie_goal = st.number_input(
            "Calories",
            min_value=500,
            value=2000,
            step=100,
        )

    with col3:
        intensity_goal = st.number_input(
            "Active Minutes",
            min_value=0,
            value=30,
            step=5,
        )

    with col4:
        sleep_goal = st.number_input(
            "Sleep Hours",
            min_value=1.0,
            value=8.0,
            step=0.5,
        )

    results = build_daily_goal_drilldown(
        step_goal=step_goal,
        calorie_goal=calorie_goal,
        intensity_goal=intensity_goal,
        sleep_goal=sleep_goal,
        start_date=start,
        end_date=end,
    )

    ach = results["achievements"]

    # KPI cards (R18)
    st.subheader("Goal Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Perfect Days",
        ach["perfect_days"]
    )

    col2.metric(
        "Avg Goals Met",
        ach["average_goals_met"]
    )

    col3.metric(
        "Sleep Goal Days",
        ach["sleep_goal_days"]
    )

    col4.metric(
        "Avg Sleep Score",
        ach["average_sleep_score"]
    )

    # Insight box
    if ach["average_goals_met"] >= 3:
        st.success(
            "Strong performance. Most daily goals were consistently achieved."
        )

    elif ach["average_goals_met"] >= 2:
        st.info(
            "Moderate performance. Some goals were met regularly, but there is room for improvement."
        )

    else:
        st.warning(
            "Goal achievement was generally low during this period."
        )

    # Highlights
    st.subheader("Highlights")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "🏆 Best Day",
            results["best_day"]["date"],
            f'{results["best_day"]["goals_met"]}/4 goals achieved'
        )

    with col2:
        st.metric(
            "📉 Lowest Day",
            results["worst_day"]["date"],
            f'{results["worst_day"]["goals_met"]}/4 goals achieved'
        )

    # Goal Distribution Chart (Interactive)
    st.subheader("Goal Achievement Distribution")

    goal_counts = (
        results["daily_goal_breakdown"]["goals_met"]
        .value_counts()
        .sort_index()
        .reset_index()
    )

    goal_counts.columns = [
        "Goals Achieved",
        "Number of Days"
    ]

    fig = px.bar(
        goal_counts,
        x="Goals Achieved",
        y="Number of Days",
        color="Goals Achieved",
        title="Distribution of Goals Achieved"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # Weekly Trend (Interactive)
    st.subheader("Weekly Goal Achievement")

    weekly_fig = px.line(
        results["weekly_summary"],
        x="ActivityDay",
        y=["goals_met", "sleep_score"],
        markers=True,
        title="Weekly Goal Achievement Trends"
    )

    st.plotly_chart(
        weekly_fig,
        use_container_width=True
    )

    # Monthly Trend (Interactive)
    st.subheader("Monthly Goal Achievement")

    monthly_fig = px.line(
        results["monthly_summary"],
        x="ActivityDay",
        y=[
            "average_goals_met",
            "average_sleep_score"
        ],
        markers=True,
        title="Monthly Goal Achievement Trends"
    )

    st.plotly_chart(
        monthly_fig,
        use_container_width=True
    )

    # R02 Actual vs Target Table
    st.subheader("Daily Goal Breakdown")

    display_df = (
        results["daily_goal_breakdown"][
            [
                "ActivityDay",
                "StepTotal",
                "step_target",
                "step_goal_met",
                "Calories",
                "calorie_target",
                "calorie_goal_met",
                "FairlyActiveMinutes",
                "intensity_target",
                "intensity_goal_met",
                "sleep_hours",
                "sleep_target",
                "sleep_goal_met",
                "sleep_score"
            ]
        ]
    )

    display_df["step_goal_met"] = (
        display_df["step_goal_met"]
        .map({True: "✅ Met", False: "❌ Not Met"})
    )

    display_df["calorie_goal_met"] = (
        display_df["calorie_goal_met"]
        .map({True: "✅ Met", False: "❌ Not Met"})
    )

    display_df["intensity_goal_met"] = (
        display_df["intensity_goal_met"]
        .map({True: "✅ Met", False: "❌ Not Met"})
    )

    display_df["sleep_goal_met"] = (
        display_df["sleep_goal_met"]
        .map({True: "✅ Met", False: "❌ Not Met"})
    )

    display_df.rename(
        columns={
            "ActivityDay": "Date",
            "StepTotal": "Steps",
            "step_target": "Step Target",
            "step_goal_met": "Step Goal",

            "Calories": "Calories",
            "calorie_target": "Calorie Target",
            "calorie_goal_met": "Calorie Goal",

            "FairlyActiveMinutes": "Active Minutes",
            "intensity_target": "Active Target",
            "intensity_goal_met": "Activity Goal",

            "sleep_hours": "Sleep Hours",
            "sleep_target": "Sleep Target",
            "sleep_goal_met": "Sleep Goal",

            "sleep_score": "Sleep Score",
        },
        inplace=True
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

daily_goal_drilldown_section()

# Derived Fitness Features

st.divider()
walking_features_section(PERSON_ID, start, end)

st.divider()
derived_features_section(PERSON_ID, start, end)