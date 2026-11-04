"""
load_data.py - loads and cleans the CSVs the behaviour-insights features need.

Usage:
    data = FitbitData().load().clean()     # step 1: load, step 2: clean
    mine = data.for_user(PERSON_ID)        # one person's daily metrics
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

# Settings
DATA_FOLDER = (
    Path(__file__).resolve().parent.parent / "datafolder" / "FitBit Dataset-20261009"
)
PERSON_ID = int(os.environ.get("FITBIT_PERSON_ID", 2022484408))  # <- our person
USER_NAME = os.environ.get("FITBIT_USER_NAME", "Athlete")  # dataset has no real names

DATE_FORMAT = "%m/%d/%Y"  # e.g. 4/12/2016
DATETIME_FORMAT = "%m/%d/%Y %I:%M:%S %p"  # e.g. 4/12/2016 12:00:00 AM

LABELS = {
    "steps": "Steps",
    "calories": "Calories burned",
    "active_minutes": "Active minutes",
    "sleep_hours": "Sleep (hours)",
}

# the four activity levels: column name -> label shown on charts
LEVEL_COLUMNS = {
    "sedentary_minutes": "Sedentary",
    "light_minutes": "Lightly active",
    "fairly_minutes": "Fairly active",
    "very_minutes": "Very active",
}

# column names in the intensities file -> our names
LEVEL_RENAME = {
    "SedentaryMinutes": "sedentary_minutes",
    "LightlyActiveMinutes": "light_minutes",
    "FairlyActiveMinutes": "fairly_minutes",
    "VeryActiveMinutes": "very_minutes",
}


class FitbitData:
    def __init__(self, folder=DATA_FOLDER):
        self.folder = Path(folder)

    def load(self):
        """Step 1: read the CSVs, untouched."""
        self.activity = pd.read_csv(self.folder / "dailyActivity_merged.csv")
        self.intensities = pd.read_csv(self.folder / "dailyIntensities_merged.csv")
        self.sleep = pd.read_csv(self.folder / "sleepDay_merged.csv")
        return self

    def clean(self):
        """Step 2: tidy into one table (one row per person per day). Run load() first."""
        # 1. Turn the date text into real dates
        activity = self.activity.assign(
            Date=pd.to_datetime(self.activity["ActivityDate"], format=DATE_FORMAT)
        )
        levels = self.intensities.assign(
            Date=pd.to_datetime(self.intensities["ActivityDay"], format=DATE_FORMAT)
        )
        sleep = self.sleep.assign(
            Date=pd.to_datetime(
                self.sleep["SleepDay"], format=DATETIME_FORMAT
            ).dt.normalize()
        )
        sleep = sleep.drop_duplicates(["Id", "Date"])  # a few days have two sleep rows

        # 2. Join the three files, keeping only the columns we need
        m = (
            activity[["Id", "Date", "TotalSteps", "Calories"]]
            .rename(columns={"TotalSteps": "steps", "Calories": "calories"})
            .merge(
                levels[["Id", "Date", *LEVEL_RENAME]].rename(columns=LEVEL_RENAME),
                on=["Id", "Date"],
                how="left",
            )
            .merge(
                sleep[["Id", "Date", "TotalMinutesAsleep"]],
                on=["Id", "Date"],
                how="left",
            )
        )

        # 3. Work out the extra columns
        m["active_minutes"] = m["fairly_minutes"] + m["very_minutes"]
        m["sleep_hours"] = m["TotalMinutesAsleep"] / 60

        # 4. Tracker not worn all day (1440 sedentary minutes) -> not real zeros, so mark as "no data"
        not_worn = m["sedentary_minutes"] == 1440
        m.loc[not_worn, ["steps", "calories", "active_minutes", *LEVEL_COLUMNS]] = (
            np.nan
        )

        # 5. The data stops mid-afternoon on the last day, so it looks too low. Leave it out.
        m = m[m["Date"] < m["Date"].max()]

        self.metrics = m[
            [
                "Id",
                "Date",
                "steps",
                "calories",
                "active_minutes",
                "sleep_hours",
                *LEVEL_COLUMNS,
            ]
        ]
        return self

    def for_user(self, user_id):
        """One person's daily metrics, sorted by date."""
        mine = self.metrics[self.metrics["Id"] == user_id]
        return mine.sort_values("Date").reset_index(drop=True)


def load_user_metrics(user_id=PERSON_ID):
    """Load + clean, then return one person's daily metrics."""
    return FitbitData().load().clean().for_user(user_id)


def show(value, metric):
    """Format a number for display - or say 'No data' instead of showing a misleading zero."""
    if pd.isna(value):
        return "No data"
    return f"{value:.1f}" if metric == "sleep_hours" else f"{value:,.0f}"

def load_all_metrics():
    """Load + clean, then return everyone's daily metrics (for the friends leaderboard)."""
    return FitbitData().load().clean().metrics
