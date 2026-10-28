import pandas as pd

def build_daily_goal_drilldown(
    step_goal=10000,
    calorie_goal=2000,
    intensity_goal=30,
    sleep_goal=8,
    start_date=None,
    end_date=None
):

    """
    Daily Goals Drill-Down

    Loads Fitbit daily datasets, calculates goal achievement,
    generates weekly/monthly summaries, and returns achievement metrics.

    Requirements covered:
    - R01: User-defined goals
    - R02: Actual vs target + met/not met indicators
    - R17: Sleep score (0-10)
    - R18: KPI metrics

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
    sleep["ActivityDay"] = pd.to_datetime(sleep["SleepDay"].dt.date)

    # Convert sleep minutes to hours
    sleep["sleep_hours"] = (
        sleep["TotalMinutesAsleep"] / 60
    )

    sleep = (
        sleep[["Id", "ActivityDay", "sleep_hours"]]
        .groupby(
            ["Id", "ActivityDay"],
            as_index=False
        )
        .mean()
    )

    # Merge datasets
    df = (
        steps
        .merge(
            calories,
            on=["Id", "ActivityDay"]
        )
        .merge(
            intensity,
            on=["Id", "ActivityDay"]
        )
        .merge(
            sleep,
            on=["Id", "ActivityDay"],
            how="left"
        )
    )

    df["sleep_hours"] = (
        df["sleep_hours"]
        .fillna(0)
    )

    # Date range filter (R02)
    if start_date is not None:
        df = df[
            df["ActivityDay"]
            >= pd.to_datetime(start_date)
        ]

    if end_date is not None:
        df = df[
            df["ActivityDay"]
            <= pd.to_datetime(end_date)
        ]

    # Sleep score (R17)
    # Scale against goal and cap at 10
    df["sleep_score"] = (
        (df["sleep_hours"] / sleep_goal) * 10
    ).clip(0, 10).round(1)

    # Goal checks (R02)
    df["step_goal_met"] = (
        df["StepTotal"] >= step_goal
    )

    df["calorie_goal_met"] = (
        df["Calories"] >= calorie_goal
    )

    df["intensity_goal_met"] = (
        df["FairlyActiveMinutes"]
        >= intensity_goal
    )

    df["sleep_goal_met"] = (
        df["sleep_hours"] >= sleep_goal
    )

    goal_columns = [
        "step_goal_met",
        "calorie_goal_met",
        "intensity_goal_met",
        "sleep_goal_met"
    ]

    df["goals_met"] = (
        df[goal_columns]
        .sum(axis=1)
    )

    # Daily goal comparison table (R02)
    daily_goal_breakdown = df[[
        "ActivityDay",
        "StepTotal",
        "Calories",
        "FairlyActiveMinutes",
        "sleep_hours",
        "sleep_score",
        "step_goal_met",
        "calorie_goal_met",
        "intensity_goal_met",
        "sleep_goal_met",
        "goals_met"
    ]].copy()

    daily_goal_breakdown["step_target"] = step_goal
    daily_goal_breakdown["calorie_target"] = calorie_goal
    daily_goal_breakdown["intensity_target"] = intensity_goal
    daily_goal_breakdown["sleep_target"] = sleep_goal

    # Weekly summary
    weekly_summary = (
        df
        .set_index("ActivityDay")
        .resample("W")
        .agg({
            "goals_met": "mean",
            "sleep_score": "mean"
        })
        .reset_index()
    )

    # Monthly summary
    monthly_summary = (
        df
        .set_index("ActivityDay")
        .resample("ME")
        .agg({
            "goals_met": "mean",
            "sleep_score": "mean"
        })
        .reset_index()
        .rename(
            columns={
                "goals_met":
                    "average_goals_met",
                "sleep_score":
                    "average_sleep_score"
            }
        )
    )

    # Best / worst day
    best_day = df.loc[
        df["goals_met"].idxmax()
    ]

    worst_day = df.loc[
        df["goals_met"].idxmin()
    ]

    # KPI metrics (R18)
    achievements = {
        "perfect_days":
            int((df["goals_met"] == 4).sum()),

        "step_goal_days":
            int(df["step_goal_met"].sum()),

        "calorie_goal_days":
            int(df["calorie_goal_met"].sum()),

        "intensity_goal_days":
            int(df["intensity_goal_met"].sum()),

        "sleep_goal_days":
            int(df["sleep_goal_met"].sum()),

        "average_sleep_score":
            round(df["sleep_score"].mean(), 1),

        "average_goals_met":
            round(df["goals_met"].mean(), 2)
    }

    return {
        "daily_data": df,
        "daily_goal_breakdown":
            daily_goal_breakdown,
        "weekly_summary":
            weekly_summary,
        "monthly_summary":
            monthly_summary,
        "achievements":
            achievements,
        "best_day": {
            "date":
                str(best_day["ActivityDay"].date()),
            "goals_met":
                int(best_day["goals_met"])
        },
        "worst_day": {
            "date":
                str(worst_day["ActivityDay"].date()),
            "goals_met":
                int(worst_day["goals_met"])
        }
    }