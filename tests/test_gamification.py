"""Tests for gamification.py. Run with: pytest tests/"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
import gamification as g  # noqa: E402


def make_days(steps, user_id=1):
    dates = pd.date_range("2016-04-12", periods=len(steps))
    return pd.DataFrame({"Id": user_id, "Date": dates, "steps": steps})


# streaks
def test_streak_counts():
    df = make_days([12000, 11000, 5000, 10000, 10500, 13000])
    s = g.streak_summary(df, "steps", 10000)
    assert s["current"] == 3
    assert s["longest"] == 3
    assert s["days_hit"] == 5


def test_hitting_goal_exactly_counts():
    df = make_days([10000, 10000])
    assert g.streak_summary(df, "steps", 10000)["current"] == 2


def test_missed_last_day_resets_current():
    df = make_days([12000, 12000, 12000, 3000])
    s = g.streak_summary(df, "steps", 10000)
    assert s["current"] == 0
    assert s["longest"] == 3


def test_no_data_breaks_streak():
    df = make_days([12000, np.nan, 12000, 12000])
    s = g.streak_summary(df, "steps", 10000)
    assert s["longest"] == 2
    assert s["days_with_data"] == 3


def test_missing_date_breaks_streak():
    df = make_days([12000, 12000, 12000]).drop(index=1)
    assert g.streak_summary(df, "steps", 10000)["longest"] == 1


def test_all_no_data():
    s = g.streak_summary(make_days([np.nan, np.nan]), "steps", 10000)
    assert s["current"] is None and s["longest"] is None


def test_period_filter():
    df = make_days([12000] * 4)
    s = g.streak_summary(df, "steps", 10000, start="2016-04-14", end="2016-04-15")
    assert s["longest"] == 2


# leaderboard
def make_group():
    # user 1 = you, user 2 = more steps, user 3 = only 2 days of data
    return pd.concat(
        [
            make_days([8000] * 10, user_id=1),
            make_days([12000] * 10, user_id=2),
            make_days([20000] * 2, user_id=3),
        ]
    ).assign(active_minutes=30)


def test_leaderboard_order_and_you():
    board = g.leaderboard(make_group(), "steps", user_id=1, min_days=7)
    assert list(board["Id"]) == [2, 1]
    assert board.loc[board["is_you"], "name"].item() == "You"
    assert g.your_position(board) == (2, 2)


def test_too_few_days_not_ranked():
    board = g.leaderboard(make_group(), "steps", user_id=1, min_days=7)
    assert 3 not in board["Id"].values


def test_friends_shown_by_name_not_id():
    board = g.leaderboard(make_group(), "steps", user_id=1, min_days=7)
    assert board.loc[board["Id"] == 2, "name"].item().startswith("Friend")


def test_sleep_not_allowed_on_leaderboard():
    with pytest.raises(ValueError):
        g.leaderboard(make_group().assign(sleep_hours=7), "sleep_hours", user_id=1)


def test_empty_leaderboard():
    board = g.leaderboard(make_group(), "steps", user_id=1, min_days=50)
    assert board.empty
    assert g.your_position(board) is None
