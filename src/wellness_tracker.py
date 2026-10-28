import numpy as np
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import calendar
import streamlit as st

from load_data import PERSON_ID, USER_NAME, load_user_metrics

# one person's cleaned daily metrics
df = load_user_metrics(PERSON_ID)
 
# --- settings ---------------------------------------------------------------
GOALS = {"Sleep (h)": 8, "Steps": 10_000, "Calories burned (kcal)": 600}
COLOURS = {"Sleep (h)": "#7F77DD", "Steps": "#1D9E75", "Calories burned (kcal)": "#D85A30"}
# (inner radius, thickness) for each ring, outermost first
RINGS = {"Sleep (h)": (2.4, 0.7), "Steps": (1.5, 0.7), "Calories burned (kcal)": (0.6, 0.7)}


def ring_traces(day_values, show_legend=False):
    """Return the Barpolar traces (track + progress) for one day.
 
    day_values: dict like {"Sleep (h)": 7.4, "Steps": 8200, "Calories burned (kcal)": 540}
    """
    traces = []
    for name, (inner, thick) in RINGS.items():
        value = day_values[name]
        sweep = min(value / GOALS[name], 1.0) * 360  # degrees; capped at a full ring
        # faint full-circle track
        traces.append(go.Barpolar(
            r=[thick], base=[inner], theta=[180], width=[360],
            marker=dict(color=COLOURS[name], opacity=0.18, line=dict(width=0)),
            hoverinfo="skip", showlegend=False,
        ))
        # progress arc, starting at the top (rotation is set in the layout)
        traces.append(go.Barpolar(
            r=[thick], base=[inner], theta=[sweep / 2], width=[sweep],
            marker=dict(color=COLOURS[name], line=dict(width=0)),
            name=name, showlegend=show_legend,
            hovertemplate=f"{name}: {value:,.1f} / {GOALS[name]:,}<extra></extra>",
        ))
    return traces
 
def polar_layout():
    """Layout settings shared by every polar subplot: hidden axes, start at top, clockwise."""
    return dict(
        radialaxis=dict(range=[0, 5.0], visible=False),
        angularaxis=dict(rotation=90, direction="clockwise", visible=False),
        bgcolor="rgba(0,0,0,0)",
    )
 

def month_grid(year, month, data):
    """data: {day_of_month: {"Sleep (h)": .., "Steps": .., "Calories burned (kcal)": ..}}"""
    weeks = calendar.monthcalendar(year, month)  # Monday first; 0 = not in this month
    weeks = [w for w in weeks if any(d in data for d in w if d != 0)]
    rows = len(weeks)
    fig = make_subplots(
        rows=rows, cols=7,
        specs=[[{"type": "polar"}] * 7 for _ in range(rows)],
        horizontal_spacing=0.01, vertical_spacing=0.02,
    )

    for r, week in enumerate(weeks, start=1):
        for c, day in enumerate(week, start=1):
            if day == 0 or day not in data:
                continue

            dom = fig.get_subplot(r, c).domain
            fig.add_annotation(
                x=dom.x[0], y=dom.y[1], xref="paper", yref="paper",
                text=ordinal(day), showarrow=False,
                xanchor="left", yanchor="top", font=dict(size=12),
            )
            for t in ring_traces(data[day]):
                fig.add_trace(t, row=r, col=c)
    annotations = []

    # apply the shared polar layout to every subplot
    fig.update_polars(**polar_layout())
    # weekday headings
    for i, d in enumerate(calendar.day_abbr):
        fig.add_annotation(x=(i + 0.5) / 7, y=1.03, xref="paper", yref="paper",
                           text=d, showarrow=False, font=dict(size=12))
    fig.update_layout(
        title=dict(text=f"{calendar.month_name[month]} {year}", font=dict(size=36)),
        barmode="overlay",
        height=170 * rows + 80, margin=dict(l=10, r=10, t=90, b=10),
        showlegend=False,
    )
    return fig


def ordinal(n):
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def wellness_tracker(df, picked):
    """Draw a month-by-month wellness calendar for a chosen period in Streamlit.

    Filters the daily metrics to the selected dates and draws one calendar per
    month the period touches. Each day shows three concentric rings (sleep,
    steps, calories burned), filled in proportion to that day's goal. Missing
    values are treated as zero.

    Args:
        df (pd.DataFrame): Daily metrics for one person, one row per day. Needs a
            datetime column ``Date`` and numeric columns ``sleep_hours``,
            ``steps`` and ``calories``.
        picked (tuple[datetime.date, ...]): The value returned by
            ``st.date_input`` for a date range. It holds one date while the
            user is still choosing and two, ``(start, end)``, once complete.

    Returns:
        None: The calendars are drawn directly on the Streamlit page.
    """
    COLUMNS = { "Sleep (h)": "sleep_hours", "Steps": "steps", "Calories burned (kcal)": "calories"}

                         
    DATE_COL = "Date"   
    #df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df[list(COLUMNS.values())] = df[list(COLUMNS.values())].fillna(0)
    # month picker, limited to months that exist in the data (latest first)
    first_day, last_day = df["Date"].min().date(), df["Date"].max().date()



    # while the user is mid-selection, picked has only one date
    if len(picked) != 2:
        st.info("Pick an end date to show the calendar.")
        st.stop()
    start, end = picked

    # keep only rows inside the chosen period
    in_range = (df[DATE_COL].dt.date >= start) & (df[DATE_COL].dt.date <= end)
    period_df = df[in_range]

    if period_df.empty:
        st.warning("No data in this period.")
        st.stop()

    # one calendar per month the period touches
    for month_period in pd.period_range(pd.Timestamp(start), pd.Timestamp(end), freq="M"):
        month_df = period_df[period_df[DATE_COL].dt.to_period("M") == month_period]
        data = {
            row[DATE_COL].day: {name: row[col] for name, col in COLUMNS.items()}
            for _, row in month_df.iterrows()
        }
        st.plotly_chart(
            month_grid(month_period.year, month_period.month, data),
            width="stretch", key=f"cal_{month_period}",
        )
