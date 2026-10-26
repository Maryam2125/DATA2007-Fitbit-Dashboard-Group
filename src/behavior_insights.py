"""
behavior_insights.py - the five behaviour-insight features.
Each feature = a data function (returns a DataFrame) + a chart function (returns a Plotly figure).
`df` is one person's daily metrics from load_data.load_user_metrics().
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from load_data import LABELS, LEVEL_COLUMNS, show

CORE_METRICS = ["steps", "calories", "active_minutes"]
ALL_METRICS = CORE_METRICS + ["sleep_hours"]

MIN_DAYS = 3  # days needed in each group before comparing them
MIN_BASELINE_DAYS = 7  # days needed to know someone's "usual" level
Z_THRESHOLD = 1.5  # unusual = more than 1.5 standard deviations from usual
CHANGE_TOLERANCE_PCT = 2  # changes smaller than this count as "No change"
SIMILAR_PCT = (
    5  # weekday/weekend differences smaller than this count as "about the same"
)

# Colour palette: calm teal, sage and coral
NEUTRAL = "#b8c4cc"  # cool grey: comparison "A" bars and ordinary days
PRIMARY = "#1b6a72"  # deep teal: main accent ("B" bars)
UP = "#4c9f70"  # sage green: best day / increase
DOWN = "#e07a5f"  # soft coral: worst day / decrease
LINE = "#5f6b76"  # slate: the daily line on the unusual-days chart
LEVEL_COLORS = ["#cfd8dc", "#8ecfc9", "#3fa7a0", "#0f6b6b"]  # sedentary -> very active


# Helpers used by several features
def tidy(fig, height=360):
    fig.update_layout(
        height=height, margin=dict(t=60, b=20, l=10, r=10), plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig


def no_data_figure():
    """A chart that just says 'No data' instead of an error or a misleading zero."""
    fig = go.Figure()
    fig.add_annotation(
        text="No data",
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=16, color="grey"),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return tidy(fig, height=300)


def compare_groups(group_a, group_b, metrics):
    """Average each metric in two groups of days (NaN if a group has too few days)."""
    rows = []
    for metric in metrics:
        a, b = (
            group_a[metric].dropna(),
            group_b[metric].dropna(),
        )  # days with no data are left out
        enough = len(a) >= MIN_DAYS and len(b) >= MIN_DAYS
        rows.append(
            {
                "metric": metric,
                "days_a": len(a),
                "days_b": len(b),
                "avg_a": a.mean() if enough else np.nan,
                "avg_b": b.mean() if enough else np.nan,
            }
        )
    return pd.DataFrame(rows)


def paired_bar_chart(summary, label_a, label_b):
    """One panel per metric, two bars each. `summary` comes from compare_groups()."""
    titles = ["<b>" + LABELS[m] + "</b>" for m in summary["metric"]]
    fig = make_subplots(rows=1, cols=len(summary), subplot_titles=titles)
    for col, row in enumerate(summary.itertuples(), start=1):
        if pd.isna(row.avg_a) or pd.isna(row.avg_b):
            fig.add_annotation(
                text="Not enough data",
                row=1,
                col=col,
                xref="x domain",
                yref="y domain",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14, color="grey"),
            )
            fig.update_xaxes(visible=False, row=1, col=col)
            fig.update_yaxes(visible=False, row=1, col=col)
            continue
        fig.add_trace(
            go.Bar(
                x=[
                    f"{label_a}<br>({row.days_a} days)",
                    f"{label_b}<br>({row.days_b} days)",
                ],
                y=[row.avg_a, row.avg_b],
                marker_color=[NEUTRAL, PRIMARY],
                text=[show(row.avg_a, row.metric), show(row.avg_b, row.metric)],
                textposition="outside",
                hoverinfo="skip",
            ),
            row=1,
            col=col,
        )
        fig.update_yaxes(
            visible=False, range=[0, max(row.avg_a, row.avg_b) * 1.35], row=1, col=col
        )
    fig.update_layout(showlegend=False)
    return tidy(fig, height=380)


def usual_level(baseline, metric):
    """A person's usual level = (average, standard deviation), or (None, None) if too little data."""
    values = baseline[metric].dropna()
    if len(values) < MIN_BASELINE_DAYS or values.std() == 0:
        return None, None
    return values.mean(), values.std()


# 1. Weekday vs weekend
def weekday_weekend_summary(df, metrics=CORE_METRICS):
    is_weekend = df["Date"].dt.day_of_week >= 5
    return compare_groups(
        df[~is_weekend], df[is_weekend], metrics
    )  # A = weekdays, B = weekends


def weekday_weekend_chart(df, metrics=CORE_METRICS):
    return paired_bar_chart(
        weekday_weekend_summary(df, metrics), "Weekdays", "Weekends"
    )


# wording for each metric: (higher, lower, about the same)
WEEKEND_WORDING = {
    "active_minutes": ("are more active", "are less active", "are about as active"),
    "steps": (
        "take more steps",
        "take fewer steps",
        "take about the same number of steps",
    ),
    "calories": (
        "burn more calories",
        "burn fewer calories",
        "burn about the same number of calories",
    ),
}


def weekday_weekend_insight(df):
    """One sentence comparing weekends with weekdays, or None if there is not enough data."""
    summary = weekday_weekend_summary(df).set_index("metric")
    parts = []
    for metric, (higher, lower, same) in WEEKEND_WORDING.items():
        weekday_avg, weekend_avg = (
            summary.loc[metric, "avg_a"],
            summary.loc[metric, "avg_b"],
        )
        if pd.isna(weekday_avg) or weekday_avg == 0:
            continue
        change = (weekend_avg - weekday_avg) / weekday_avg * 100
        if change > SIMILAR_PCT:
            parts.append(f"{higher} ({change:+.0f}%)")
        elif change < -SIMILAR_PCT:
            parts.append(f"{lower} ({change:+.0f}%)")
        else:
            parts.append(same)
    if not parts:
        return None
    joined = (
        parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    )
    return f"On weekends you {joined} compared with weekdays."


# 2. Best and worst day
TITLE_PHRASE = {
    "steps": "steps taken",
    "calories": "calories burned",
    "active_minutes": "active minutes",
    "sleep_hours": "sleep",
}


def best_worst_days(df, metrics=ALL_METRICS):
    rows = []
    for metric in metrics:
        days = df.dropna(subset=[metric])
        if days.empty:
            rows.append({"metric": metric})  # the other columns become NaN = "No data"
            continue
        best, worst = days.loc[days[metric].idxmax()], days.loc[days[metric].idxmin()]
        rows.append(
            {
                "metric": metric,
                "best_date": best["Date"],
                "best_value": best[metric],
                "worst_date": worst["Date"],
                "worst_value": worst[metric],
            }
        )
    return pd.DataFrame(
        rows, columns=["metric", "best_date", "best_value", "worst_date", "worst_value"]
    )


def best_worst_chart(df, metric):
    days = df.dropna(subset=[metric])
    if days.empty:
        return no_data_figure()
    best_date = days.loc[days[metric].idxmax(), "Date"]
    worst_date = days.loc[days[metric].idxmin(), "Date"]
    colors = np.where(
        days["Date"] == best_date,
        UP,
        np.where(days["Date"] == worst_date, DOWN, NEUTRAL),
    )
    fig = go.Figure(go.Bar(x=days["Date"], y=days[metric], marker_color=colors))
    fig.update_layout(
        title=f"Best and worst day for {TITLE_PHRASE[metric]}"
        "<br><sup>green = best day, red = worst day</sup>",
        yaxis_title=LABELS[metric],
    )
    return tidy(fig, height=360)


# 3. Time at each activity level
def activity_level_totals(df):
    """Average minutes per day at each level, and each level's share of the tracked day."""
    days = df.dropna(subset=list(LEVEL_COLUMNS))
    if days.empty:
        return pd.DataFrame(columns=["level", "avg_minutes", "share_pct"])
    avg_minutes = days[list(LEVEL_COLUMNS)].mean()
    return pd.DataFrame(
        {
            "level": list(LEVEL_COLUMNS.values()),
            "avg_minutes": avg_minutes.values,
            "share_pct": avg_minutes.values / avg_minutes.sum() * 100,
        }
    )


def activity_levels_chart(df):
    """One bar per day, split into colours showing the share of the day spent at each activity level."""
    days = df.dropna(subset=list(LEVEL_COLUMNS))
    if days.empty:
        return no_data_figure()
    minutes = days[list(LEVEL_COLUMNS)]
    share = (
        minutes.div(minutes.sum(axis=1), axis=0) * 100
    )  # % of the day, so every bar is 100%

    fig = go.Figure()
    for i, level in reversed(
        list(enumerate(LEVEL_COLUMNS))
    ):  # very active at the bottom of each bar
        fig.add_trace(
            go.Bar(
                x=days["Date"],
                y=share[level],
                name=LEVEL_COLUMNS[level],
                marker_color=LEVEL_COLORS[i],
                customdata=minutes[level],
                hovertemplate="%{x|%a %d %b}<br>"
                + LEVEL_COLUMNS[level]
                + ": %{customdata:.0f} min (%{y:.0f}%)<extra></extra>",
            )
        )
    fig.update_layout(
        barmode="stack",
        yaxis=dict(title="% of the day", range=[0, 100]),
        legend=dict(orientation="h", y=1.1),
    )
    return tidy(fig, height=400)


# 4. Unusual days vs the person's usual level
def significant_changes(df, baseline=None, metrics=ALL_METRICS):
    """Days that are unusually high/low. `baseline` = the data that defines "usual" (default: df)."""
    baseline = df if baseline is None else baseline
    found = []
    for metric in metrics:
        usual, spread = usual_level(baseline, metric)
        if usual is None:
            continue
        days = df.dropna(subset=[metric])
        z_score = (
            days[metric] - usual
        ) / spread  # how many standard deviations from usual
        unusual = days[z_score.abs() >= Z_THRESHOLD]
        if unusual.empty:
            continue
        found.append(
            pd.DataFrame(
                {
                    "Date": unusual["Date"],
                    "metric": metric,
                    "value": unusual[metric],
                    "usual": usual,
                    "change_pct": (unusual[metric] - usual) / usual * 100,
                    "z_score": z_score[unusual.index],
                    "direction": np.where(
                        unusual[metric] > usual, "Increase", "Decrease"
                    ),
                }
            )
        )
    if not found:
        return pd.DataFrame(
            columns=[
                "Date",
                "metric",
                "value",
                "usual",
                "change_pct",
                "z_score",
                "direction",
            ]
        )
    return pd.concat(found).sort_values("Date", ascending=False).reset_index(drop=True)


# what to say about an unusual day: {much} / {far} become "much " / "far " for very unusual days,
# and {date}, {value} and {usual} are filled in
COMMENTS = {
    (
        "steps",
        "Increase",
    ): "You took {far}more steps than usual on {date} ({value} vs {usual}).",
    (
        "steps",
        "Decrease",
    ): "You took {far}fewer steps than usual on {date} ({value} vs {usual}).",
    (
        "calories",
        "Increase",
    ): "You burned {far}more calories than usual on {date} ({value} vs {usual}).",
    (
        "calories",
        "Decrease",
    ): "You burned {far}fewer calories than usual on {date} ({value} vs {usual}).",
    (
        "active_minutes",
        "Increase",
    ): "You were {much}more active than usual on {date} ({value} vs {usual} active minutes).",
    (
        "active_minutes",
        "Decrease",
    ): "You were {much}less active than usual on {date} ({value} vs {usual} active minutes).",
    (
        "sleep_hours",
        "Increase",
    ): "You slept {much}longer than usual on {date} ({value} vs {usual} hours).",
    (
        "sleep_hours",
        "Decrease",
    ): "You slept {much}less than usual on {date} ({value} vs {usual} hours).",
}


def unusual_day_insights(df, baseline=None, top=3):
    """The `top` most unusual days (one per date) as a list of {"direction", "text"} dictionaries."""
    changes = significant_changes(df, baseline)
    if changes.empty:
        return []
    changes["strength"] = changes["z_score"].abs()
    strongest = (
        changes.sort_values("strength", ascending=False)
        .drop_duplicates("Date")
        .head(top)
    )

    insights = []
    for row in strongest.itertuples():
        text = COMMENTS[(row.metric, row.direction)].format(
            much="much " if row.strength >= 2 else "",
            far="far " if row.strength >= 2 else "",
            date=f"{row.Date:%a %d %b}",
            value=show(row.value, row.metric),
            usual=show(row.usual, row.metric),
        )
        insights.append({"direction": row.direction, "text": text})
    return insights


def significant_change_chart(df, metric, baseline=None):
    baseline = df if baseline is None else baseline
    usual, spread = usual_level(baseline, metric)
    if usual is None or df[metric].dropna().empty:
        return no_data_figure()

    fig = go.Figure()
    fig.add_hrect(
        y0=usual - Z_THRESHOLD * spread,
        y1=usual + Z_THRESHOLD * spread,
        fillcolor="grey",
        opacity=0.15,
        line_width=0,
    )  # the usual range
    fig.add_hline(
        y=usual,
        line_dash="dash",
        line_color="grey",
        annotation_text=f"Usual: {show(usual, metric)}",
        annotation_position="top left",
    )
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df[metric],
            mode="lines+markers",
            name=LABELS[metric],
            line=dict(color=LINE),
        )
    )
    changes = significant_changes(df, baseline, [metric])
    fig.add_trace(
        go.Scatter(
            x=changes["Date"],
            y=changes["value"],
            mode="markers",
            name="Unusual day (green = up, red = down)",
            marker=dict(
                size=13, color=np.where(changes["direction"] == "Increase", UP, DOWN)
            ),
        )
    )
    fig.update_layout(yaxis_title=LABELS[metric], legend=dict(orientation="h", y=1.1))
    return tidy(fig, height=380)


# 5. Compare periods
def describe_change(change_pct):
    """Turn a % change into a word (higher counts as better)."""
    if pd.isna(change_pct):
        return "No data"
    if change_pct > CHANGE_TOLERANCE_PCT:
        return "Improved"
    if change_pct < -CHANGE_TOLERANCE_PCT:
        return "Declined"
    return "No change"


def compare_periods(df, period_a, period_b, metrics=CORE_METRICS):
    """Compare period B with period A. Each period is a (start_date, end_date) pair."""

    def days_in(period):
        return df[
            (df["Date"] >= pd.Timestamp(period[0]))
            & (df["Date"] <= pd.Timestamp(period[1]))
        ]

    summary = compare_groups(days_in(period_a), days_in(period_b), metrics)
    summary["change_pct"] = (
        (summary["avg_b"] - summary["avg_a"])
        / summary["avg_a"].replace(0, np.nan)
        * 100
    )
    summary["trend"] = summary["change_pct"].apply(describe_change)
    return summary


def compare_periods_chart(summary, label_a="Period A", label_b="Period B"):
    return paired_bar_chart(summary, label_a, label_b)
