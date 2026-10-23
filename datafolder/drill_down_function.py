import pandas as pd

def build_daily_goal_drilldown(
    step_goal=10000,
    calorie_goal=2000,
    intensity_goal=30,
    sleep_goal=8
):

    # Load files
    steps = pd.read_csv("dailySteps_merged.csv")
    calories = pd.read_csv("dailyCalories_merged.csv")
    intensity = pd.read_csv("dailyIntensities_merged.csv")
    sleep = pd.read_csv("sleepDay_merged.csv")

    # Standardise dates
    steps["ActivityDay"] = pd.to_datetime(steps["ActivityDay"])
    calories["ActivityDay"] = pd.to_datetime(calories["ActivityDay"])
    intensity["ActivityDay"] = pd.to_datetime(intensity["ActivityDay"])

    sleep["SleepDay"] = pd.to_datetime(sleep["SleepDay"])
    sleep["ActivityDay"] = sleep["SleepDay"].dt.date
    sleep["ActivityDay"] = pd.to_datetime(sleep["ActivityDay"])

    # Convert sleep minutes to hours
    sleep["sleep_hours"] = sleep["TotalMinutesAsleep"] / 60

    # Select required columns
    sleep = sleep[
        ["Id", "ActivityDay", "sleep_hours"]
    ]

    # Merge datasets
    df = (
        steps
        .merge(calories, on=["Id", "ActivityDay"])
        .merge(intensity, on=["Id", "ActivityDay"])
        .merge(sleep, on=["Id", "ActivityDay"], how="left")
    )

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
    )

    # Achievement board
    achievements = {
        "perfect_days": int((df["goals_met"] == 4).sum()),
        "step_goal_days": int(df["step_goal_met"].sum()),
        "calorie_goal_days": int(df["calorie_goal_met"].sum()),
        "intensity_goal_days": int(df["intensity_goal_met"].sum()),
        "sleep_goal_days": int(df["sleep_goal_met"].sum())
    }

    return {
        "daily_data": df,
        "weekly_summary": weekly_summary,
        "monthly_summary": monthly_summary,
        "achievements": achievements
    }