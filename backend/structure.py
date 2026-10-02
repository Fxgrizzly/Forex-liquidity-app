"""
Market structure detection: turns the swing high/low sequence into a
Higher-High / Higher-Low / Lower-High / Lower-Low labeling, then flags:

- BOS (Break of Structure): price breaks a swing point IN the direction
  of the current trend (continuation).
- ChoCh (Change of Character): price breaks a swing point AGAINST the
  current trend (early signal of a reversal).
"""

from typing import List, Dict
import pandas as pd


def get_swing_sequence(df: pd.DataFrame) -> List[Dict]:
    """Returns an ordered list of swing points: {time, price, kind: 'high'|'low'}"""
    points = []
    for _, row in df.iterrows():
        if row.get("swing_high"):
            points.append({"time": row["time"], "price": row["high"], "kind": "high"})
        if row.get("swing_low"):
            points.append({"time": row["time"], "price": row["low"], "kind": "low"})
    points.sort(key=lambda p: p["time"])
    return points


def detect_structure_events(df: pd.DataFrame) -> List[Dict]:
    """
    Walks through candles after each swing point and checks whether price
    later closes beyond that swing point (a "break"). Classifies each break
    as BOS or ChoCh based on the prevailing trend at the time.

    Returns a list of events:
        {"time", "price", "event": "BOS"|"ChoCh", "direction": "bullish"|"bearish"}
    """
    swings = get_swing_sequence(df)
    events = []
    trend = None

    last_high = None
    last_low = None

    for point in swings:
        if point["kind"] == "high":
            if last_high is not None:
                if point["price"] > last_high["price"]:
                    label = "HH"
                else:
                    label = "LH"
                    if trend == "bullish":
                        trend = None
            last_high = point
        else:
            if last_low is not None:
                if point["price"] > last_low["price"]:
                    label = "HL"
                else:
                    label = "LL"
                    if trend == "bullish":
                        trend = None
            last_low = point

    trend = None
    prev_swing_high = None
    prev_swing_low = None

    df_sorted = df.sort_values("time").reset_index(drop=True)

    for i, row in df_sorted.iterrows():
        if row.get("swing_high"):
            prev_swing_high = row["high"]
        if row.get("swing_low"):
            prev_swing_low = row["low"]

        close = row["close"]

        if prev_swing_high is not None and close > prev_swing_high:
            direction = "bullish"
            event = "BOS" if trend == "bullish" else "ChoCh"
            events.append({"time": row["time"], "price": prev_swing_high,
                            "event": event, "direction": direction})
            trend = "bullish"
            prev_swing_high = None

        elif prev_swing_low is not None and close < prev_swing_low:
            direction = "bearish"
            event = "BOS" if trend == "bearish" else "ChoCh"
            events.append({"time": row["time"], "price": prev_swing_low,
                            "event": event, "direction": direction})
            trend = "bearish"
            prev_swing_low = None

    return events
