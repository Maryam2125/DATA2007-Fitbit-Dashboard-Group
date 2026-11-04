
import pandas as pd
import plotly.express as px
import streamlit as st

from load_data import DATA_FOLDER


# Load data for one participant
def load_user_data(filename, user_id, columns):
    parts = []

    for chunk in pd.read_csv(
        DATA_FOLDER / filename,
        usecols=columns,
        chunksize=200000
    ):
        part = chunk[chunk["Id"] == int(user_id)]
        if not part.empty:
            parts.append(part)

    return (
        pd.concat(parts, ignore_index=True)
        if parts else pd.DataFrame(columns=columns)
    )


# Calculate weekly VO2max
@st.cache_data(ttl=604800)
def weekly_vo2max(user_id):
    hr = load_user_data(
        "heartrate_seconds_merged.csv",
        user_id, ["Id", "Time", "Value"]
    )

    if hr.empty:
        return pd.DataFrame(columns=["Week", "VO2max"])

    mets = load_user_data(
        "minuteMETsNarrow_merged.csv",
        user_id, ["Id", "ActivityMinute", "METs"]
    )

    if mets.empty:
        return pd.DataFrame(columns=["Week", "VO2max"])

    hr["Time"] = pd.to_datetime(hr["Time"])
    mets["ActivityMinute"] = pd.to_datetime(mets["ActivityMinute"])
    mets["METs"] = mets["METs"] / 10

    hr["Minute"] = hr["Time"].dt.floor("min")
    hr = hr.groupby("Minute", as_index=False)["Value"].median()

    df = hr.merge(
        mets[["ActivityMinute", "METs"]],
        left_on="Minute",
        right_on="ActivityMinute"
    )

    df["Week"] = df["Minute"].dt.to_period("W").dt.start_time
    results = []

    for week, data in df.groupby("Week"):
        resting = data.loc[
            data["METs"].between(0.8, 1.3), "Value"
        ]

        if len(resting) < 30 or len(data) < 100:
            continue

        low = resting.quantile(0.10)
        high = data["Value"].quantile(0.99)

        if low > 0 and high > low:
            results.append({
                "Week": week,
                "VO2max": 15.3 * high / low
            })

    return pd.DataFrame(results, columns=["Week", "VO2max"])


# Demo fitness categories
def fitness_level(value):
    if value < 30:
        return "Developing"
    if value < 40:
        return "Good"
    if value < 50:
        return "Excellent"
    return "Elite"


# Display VO2max
def derived_features_section(user_id, start, end):
    st.header("Derived Fitness Features")
    st.subheader("VO2max")

    data = weekly_vo2max(int(user_id))

    if data.empty:
        st.info("VO2max unavailable for this participant.")
        return

    data = data[
        data["Week"].between(
            pd.Timestamp(start) - pd.Timedelta(days=6),
            pd.Timestamp(end)
        )
    ]

    if data.empty:
        st.info("No VO2max data for the selected period.")
        return

    latest = data.iloc[-1]["VO2max"]

    col1, col2 = st.columns(2)
    col1.metric("VO2max", f"{latest:.1f} mL/kg/min")
    col2.metric("Fitness Level", fitness_level(latest))

    with st.expander("View VO2max Trend"):
        fig = px.line(
            data,
            x="Week",
            y="VO2max",
            markers=True,
            color_discrete_sequence=["#1b6a72"]
        )
        st.plotly_chart(
            fig, use_container_width=True,
            key="vo2max_trend"
        )


# Load walking data
@st.cache_data(ttl=604800)
def walking_data(user_id):
    df = pd.read_csv(DATA_FOLDER / "dailyActivity_merged.csv")
    df = df[df["Id"] == int(user_id)].copy()

    if df.empty:
        return df

    df["Date"] = pd.to_datetime(df["ActivityDate"])
    df = df.sort_values("Date")

    return df


# Get minutes with likely walking activity
@st.cache_data(ttl=604800)
def walking_minutes(user_id, start, end):
    steps = load_user_data(
        "minuteStepsNarrow_merged.csv",
        user_id, ["Id", "ActivityMinute", "Steps"]
    )

    if steps.empty:
        return steps

    steps["DateTime"] = pd.to_datetime(steps["ActivityMinute"])
    steps["Date"] = steps["DateTime"].dt.normalize()

    # Use the selected period and minutes with 60+ steps
    steps = steps[
        steps["Date"].between(
            pd.Timestamp(start),
            pd.Timestamp(end)
        )
        & (steps["Steps"] >= 60)
    ].copy()

    return steps


# Display walking analysis
def walking_features_section(user_id, start, end):
    st.subheader("Walking Analysis")

    user_id = int(user_id)
    df = walking_data(user_id)

    if df.empty:
        st.info("Walking data unavailable.")
        return

    period = df[
        df["Date"].between(
            pd.Timestamp(start),
            pd.Timestamp(end)
        )
    ].copy()

    if period.empty:
        st.info("No walking data for this period.")
        return

    steps = walking_minutes(user_id, start, end)

    if steps.empty:
        st.info("No likely walking minutes found.")
        return

    # Estimate metres travelled per step each day
    period["MetresPerStep"] = (
        period["TotalDistance"] * 1000 /
        period["TotalSteps"].replace(0, float("nan"))
    )

    steps = steps.merge(
        period[["Date", "MetresPerStep"]],
        on="Date",
        how="left"
    ).dropna(subset=["MetresPerStep"])

    steps = steps[steps["MetresPerStep"] > 0].copy()

    if steps.empty:
        st.info("Not enough distance data.")
        return

    # Calculate estimated walking speed
    steps["Distance"] = steps["Steps"] * steps["MetresPerStep"]
    steps["Speed"] = steps["Distance"] * 60 / 1000

    speed = steps["Distance"].sum() * 60 / len(steps) / 1000
    cadence = steps["Steps"].mean()
    distance_per_step = steps["Distance"].sum() / steps["Steps"].sum()

    col1, col2, col3 = st.columns(3)

    col1.metric("Walking Speed", f"{speed:.2f} km/h")
    col2.metric("Walking Cadence", f"{cadence:.0f} steps/min")
    col3.metric("Distance per Step", f"{distance_per_step:.2f} m")

    # Show daily speed changes
    daily = steps.groupby("Date", as_index=False)["Speed"].mean()

    st.subheader("Walking Speed Over Time")

    fig = px.line(
        daily,
        x="Date",
        y="Speed",
        markers=True,
        color_discrete_sequence=["#1b6a72"]
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Estimated Walking Speed (km/h)"
    )

    st.plotly_chart(
        fig, use_container_width=True,
        key="walking_speed_trend"
    )
