import pandas as pd

def build_daily_goal_drilldown(
    step_goal=10000,
    calorie_goal=2000,
    intensity_goal=30,
    sleep_goal=8
):

    """
    Daily Goals Drill-Down

    Loads Fitbit daily datasets, calculates goal achievement,
    generates weekly/monthly summaries, and returns achievement metrics.

    Parameters
    ----------
    step_goal : int
        Daily step target.
    calorie_goal : int
        Daily calorie burn target.
    intensity_goal : int
        Fairly active minutes target.
    sleep_goal : int
        Sleep target in hours.

    Returns
    -------
    dict
        {
            "daily_data": DataFrame,
            "weekly_summary": DataFrame,
            "monthly_summary": DataFrame,
            "achievements": dict,
            "best_day": dict,
            "worst_day": dict
        }
    """

    # Load files
    steps = pd.read_csv("dailySteps_merged.csv")
    calories = pd.read_csv("dailyCalories_merged.csv")
    intensity = pd.read_csv("dailyIntensities_merged.csv")
    sleep = pd.read_csv("sleepDay_merged.csv")

    # Standardise activity dates
    steps["ActivityDay"] = pd.to_datetime(steps["ActivityDay"])
    calories["ActivityDay"] = pd.to_datetime(calories["ActivityDay"])
    intensity["ActivityDay"] = pd.to_datetime(intensity["ActivityDay"])

    # Standardise sleep dates
    sleep["SleepDay"] = pd.to_datetime(sleep["SleepDay"])
    sleep["ActivityDay"] = sleep["SleepDay"].dt.date
    sleep["ActivityDay"] = pd.to_datetime(sleep["ActivityDay"])

    # Convert sleep minutes to hours
    sleep["sleep_hours"] = sleep["TotalMinutesAsleep"] / 60

    # Select required columns
    sleep = sleep[
        ["Id", "ActivityDay", "sleep_hours"]
    ]

    # Handle duplicate sleep entries per day
    sleep = (
        sleep.groupby(
            ["Id", "ActivityDay"],
            as_index=False
        )
        .agg({"sleep_hours": "mean"})
    )

    # Merge all datasets
    df = (
        steps
        .merge(calories, on=["Id", "ActivityDay"])
        .merge(intensity, on=["Id", "ActivityDay"])
        .merge(sleep, on=["Id", "ActivityDay"], how="left")
    )

    # Fill missing sleep values
    df["sleep_hours"] = df["sleep_hours"].fillna(0)
    
    # Goal achievement flags
    df["step_goal_met"] = df["StepTotal"] >= step_goal
    df["calorie_goal_met"] = df["Calories"] >= calorie_goal
    df["intensity_goal_met"] = (
        df["FairlyActiveMinutes"] >= intensity_goal
    )
    df["sleep_goal_met"] = (
        df["sleep_hours"] >= sleep_goal
    )

    # Number of goals met each day
    goal_columns = [
        "step_goal_met",
        "calorie_goal_met",
        "intensity_goal_met",
        "sleep_goal_met"
    ]

    df["goals_met"] = df[goal_columns].sum(axis=1)

    # Weekly summary
    weekly_summary = (
        df
        .set_index("ActivityDay")
        .resample("W")["goals_met"]
        .mean()
        .reset_index()
    )

    # Monthly summary
    monthly_summary = (
        df
        .set_index("ActivityDay")
        .resample("M")["goals_met"]
        .mean()
        .reset_index()
        .rename(
            columns={
                "goals_met": "average_goals_met"
            }
        )
    )

    # Monthly summary
    monthly_summary = (
        df
        .set_index("ActivityDay")
        .resample("ME")["goals_met"]
        .mean()
        .reset_index()
        .rename(
            columns={
                "goals_met": "average_goals_met"
            }
        )
    )

    # Highlights and low points
    best_day = df.loc[df["goals_met"].idxmax()]

    worst_day = df.loc[df["goals_met"].idxmin()]

    # Achievement board
    achievements = {
        "perfect_days": int(
            (df["goals_met"] == 4).sum()
        ),
        "step_goal_days": int(
            df["step_goal_met"].sum()
        ),
        "calorie_goal_days": int(
            df["calorie_goal_met"].sum()
        ),
        "intensity_goal_days": int(
            df["intensity_goal_met"].sum()
        ),
        "sleep_goal_days": int(
            df["sleep_goal_met"].sum()
        )
    }

    return {
        "daily_data": df,
        "weekly_summary": weekly_summary,
        "monthly_summary": monthly_summary,
        "achievements": achievements,
        "best_day": {
            "date": str(best_day["ActivityDay"].date()),
            "goals_met": int(best_day["goals_met"])
        },
        "worst_day": {
            "date": str(worst_day["ActivityDay"].date()),
            "goals_met": int(worst_day["goals_met"])
        }
    }

# Example Streamlit Usage
# import streamlit as st

# results = build_daily_goal_drilldown()

# st.title("Daily Goals Drill-Down")

# st.subheader("Achievement Board")
# st.json(results["achievements"])

# st.subheader("Highlights")

# col1, col2 = st.columns(2)

# with col1:
#     st.write("🏆 Best Day")
#     st.write(results["best_day"])

# with col2:
#     st.write("📉 Lowest Day")
#     st.write(results["worst_day"])

# st.subheader("Daily Breakdown")
# st.dataframe(results["daily_data"])

# st.subheader("Weekly Summary")
# st.line_chart(
#     results["weekly_summary"].set_index("ActivityDay")
# )

# st.subheader("Monthly Summary")
# st.bar_chart(
#     results["monthly_summary"].set_index("ActivityDay")
# )