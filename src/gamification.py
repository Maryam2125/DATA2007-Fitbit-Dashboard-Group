"""
gamification.py - streaks and the friends leaderboard.

    df          = one person's daily metrics (load_data.load_user_metrics)
    all_metrics = everyone's daily metrics   (load_data.load_all_metrics)
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from behavior_insights import DOWN, NEUTRAL, PRIMARY, UP, no_data_figure, tidy
from load_data import LABELS, PERSON_ID, show

# daily goals for streaks (move to load_data once the team agrees one set of goals)
STREAK_GOALS = {"steps": 10_000, "active_minutes": 30, "sleep_hours": 8}

MIN_LEADERBOARD_DAYS = 7
# only activity metrics on the leaderboard, so sleep/weight stay private
LEADERBOARD_METRICS = ["steps", "active_minutes"]

GREY = "#eceff1"


# Streaks
def goal_hits(df, metric, goal, start=None, end=None):
    """Mark each day in the period as goal hit, missed or no data.

    Returns a DataFrame with Date, value and hit (1 = hit, 0 = missed,
    NaN = no data). Dates missing from df are added as no data, so a gap
    can't count towards a streak.
    """
    start = df["Date"].min() if start is None else pd.Timestamp(start)
    end = df["Date"].max() if end is None else pd.Timestamp(end)
    if pd.isna(start) or pd.isna(end):
        return pd.DataFrame(columns=["Date", "value", "hit"])

    days = pd.DataFrame({"Date": pd.date_range(start, end)})
    days = days.merge(df[["Date", metric]], on="Date", how="left")
    days = days.rename(columns={metric: "value"})
    days["hit"] = np.where(days["value"].isna(), np.nan, days["value"] >= goal)
    return days


def streak_lengths(hits):
    """Streak length on each day. A missed or no-data day resets it to 0."""
    lengths = []
    run = 0
    for hit in hits:
        run = run + 1 if hit == 1 else 0
        lengths.append(run)
    return pd.Series(lengths, index=hits.index)


def streak_summary(df, metric, goal=None, start=None, end=None):
    """Current and longest streak for one metric.

    goal defaults to STREAK_GOALS. current is the streak ending on the last
    day of the period. current and longest are None if there's no data.
    """
    goal = goal or STREAK_GOALS[metric]
    days = goal_hits(df, metric, goal, start, end)
    result = {
        "metric": metric,
        "goal": goal,
        "current": None,
        "longest": None,
        "days_hit": 0,
        "days_with_data": 0,
    }
    if days.empty or days["hit"].isna().all():
        return result

    lengths = streak_lengths(days["hit"])
    result["current"] = int(lengths.iloc[-1])
    result["longest"] = int(lengths.max())
    result["days_hit"] = int((days["hit"] == 1).sum())
    result["days_with_data"] = int(days["hit"].notna().sum())
    return result


def all_streaks(df, start=None, end=None):
    """streak_summary() for every metric in STREAK_GOALS, one row each."""
    rows = [streak_summary(df, m, g, start, end) for m, g in STREAK_GOALS.items()]
    return pd.DataFrame(rows)


def streak_chart(df, metric, start=None, end=None):
    """Strip of days: green = goal hit (labelled with the streak), coral = missed,
    grey = no data."""
    goal = STREAK_GOALS[metric]
    days = goal_hits(df, metric, goal, start, end)
    if days.empty or days["hit"].isna().all():
        return no_data_figure()

    days["streak"] = streak_lengths(days["hit"])
    hit, missed = days["hit"] == 1, days["hit"] == 0
    colours = np.select([hit, missed], [UP, DOWN], GREY)
    status = np.select([hit, missed], ["Goal hit", "Missed"], "No data")
    values = [show(v, metric) for v in days["value"]]

    fig = go.Figure(
        go.Bar(
            x=days["Date"],
            y=[1] * len(days),
            marker_color=colours,
            text=np.where(hit, days["streak"].astype(str), ""),
            textposition="inside",
            insidetextanchor="middle",
            customdata=np.column_stack([status, values]),
            hovertemplate="%{x|%a %d %b}<br>%{customdata[0]}: %{customdata[1]}<extra></extra>",
        )
    )
    fig.update_yaxes(visible=False)
    fig.update_layout(
        title=f"{LABELS[metric]} goal: {show(goal, metric)} a day"
        "<br><sup>green = goal hit (number = streak), coral = missed, grey = no data</sup>",
        bargap=0.15,
    )
    return tidy(fig, height=220)


# Leaderboard
def friend_names(all_metrics, user_id=PERSON_ID):
    """Map each Id to a display name: "You" for the user, Friend 1, Friend 2...
    for everyone else, so raw IDs aren't shown."""
    others = sorted(i for i in all_metrics["Id"].unique() if i != user_id)
    names = {friend: f"Friend {n}" for n, friend in enumerate(others, start=1)}
    names[user_id] = "You"
    return names


def leaderboard(
    all_metrics,
    metric="steps",
    start=None,
    end=None,
    user_id=PERSON_ID,
    min_days=MIN_LEADERBOARD_DAYS,
):
    """Rank everyone by their average daily value of a metric.

    Assumes friends have agreed to appear. People with fewer than min_days
    days of data aren't ranked. Only metrics in LEADERBOARD_METRICS are
    allowed, anything else raises ValueError.

    Returns a DataFrame sorted first to last with rank, name, Id, average,
    days and is_you.
    """
    if metric not in LEADERBOARD_METRICS:
        raise ValueError(f"leaderboard only works for {LEADERBOARD_METRICS}")

    data = all_metrics
    if start is not None:
        data = data[data["Date"] >= pd.Timestamp(start)]
    if end is not None:
        data = data[data["Date"] <= pd.Timestamp(end)]

    board = (
        data.dropna(subset=[metric])
        .groupby("Id")[metric]
        .agg(average="mean", days="count")
        .reset_index()
    )
    board = board[board["days"] >= min_days]
    if board.empty:
        return pd.DataFrame(columns=["rank", "name", "Id", "average", "days", "is_you"])

    board["name"] = board["Id"].map(friend_names(all_metrics, user_id))
    board["is_you"] = board["Id"] == user_id
    board = board.sort_values("average", ascending=False).reset_index(drop=True)
    board["rank"] = board["average"].rank(ascending=False, method="min").astype(int)
    return board[["rank", "name", "Id", "average", "days", "is_you"]]


def your_position(board):
    """(rank, number ranked) for the user, or None if they're not on the board."""
    you = board[board["is_you"]]
    if you.empty:
        return None
    return int(you["rank"].iloc[0]), len(board)


def leaderboard_chart(board, metric="steps"):
    """Horizontal bars with number 1 at the top, the user highlighted and a
    dashed line at the daily goal."""
    if board.empty:
        return no_data_figure()

    board = board.iloc[::-1]  # Plotly draws the first row at the bottom
    labels = [
        f"{rank}. {'★ ' if you else ''}{name}"
        for rank, name, you in zip(board["rank"], board["name"], board["is_you"])
    ]
    fig = go.Figure(
        go.Bar(
            x=board["average"],
            y=labels,
            orientation="h",
            marker_color=np.where(board["is_you"], PRIMARY, NEUTRAL),
            text=[show(v, metric) for v in board["average"]],
            textposition="outside",
            customdata=board["days"],
            hovertemplate="%{y}<br>Average: %{x:,.0f}<br>%{customdata} days<extra></extra>",
        )
    )
    goal = STREAK_GOALS.get(metric)
    if goal:
        fig.add_vline(
            x=goal,
            line_dash="dash",
            line_color="grey",
            annotation_text=f"Goal {show(goal, metric)}",
            annotation_position="top",
        )
    fig.update_layout(
        xaxis_title=f"Average {LABELS[metric].lower()} per day",
        xaxis_range=[0, board["average"].max() * 1.15],
    )
    return tidy(fig, height=max(300, 26 * len(board) + 80))
