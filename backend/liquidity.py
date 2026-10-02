"""
Implements the liquidity concepts from your reference material:

- Swing highs / swing lows (fractals)
- Equal Highs [EQH] / Equal Lows [EQL] pools
- Previous Day/Week/Month High & Low (PDH/PDL/PWH/PWL/PMH/PML)
"""

from typing import List, Dict
import pandas as pd

from config import SWING_LOOKBACK, EQH_EQL_TOLERANCE_PIPS, pip_size_for


def find_swings(df: pd.DataFrame, lookback: int = SWING_LOOKBACK) -> pd.DataFrame:
    """
    Adds 'swing_high' and 'swing_low' boolean columns.
    A swing high = a candle whose high is the max within +/- lookback candles.
    A swing low  = a candle whose low is the min within +/- lookback candles.
    """
    df = df.copy()
    df["swing_high"] = False
    df["swing_low"] = False

    highs = df["high"].values
    lows = df["low"].values
    n = len(df)

    for i in range(lookback, n - lookback):
        window_high = highs[i - lookback: i + lookback + 1]
        window_low = lows[i - lookback: i + lookback + 1]
        if highs[i] == window_high.max() and (window_high == highs[i]).sum() == 1:
            df.at[df.index[i], "swing_high"] = True
        if lows[i] == window_low.min() and (window_low == lows[i]).sum() == 1:
            df.at[df.index[i], "swing_low"] = True

    return df


def find_equal_highs_lows(df: pd.DataFrame, symbol: str,
                           tolerance_pips: float = EQH_EQL_TOLERANCE_PIPS) -> List[Dict]:
    """
    Groups nearby swing highs into EQH (BSL) pools and nearby swing lows
    into EQL (SSL) pools.
    """
    pip = pip_size_for(symbol)
    tolerance = tolerance_pips * pip

    levels = []

    swing_highs = df[df["swing_high"]][["time", "high"]].values.tolist()
    swing_lows = df[df["swing_low"]][["time", "low"]].values.tolist()

    def group(points, price_key_index):
        groups = []
        used = [False] * len(points)
        for i in range(len(points)):
            if used[i]:
                continue
            cluster = [points[i]]
            used[i] = True
            for j in range(i + 1, len(points)):
                if used[j]:
                    continue
                if abs(points[j][price_key_index] - points[i][price_key_index]) <= tolerance:
                    cluster.append(points[j])
                    used[j] = True
            if len(cluster) >= 2:
                avg_price = sum(p[price_key_index] for p in cluster) / len(cluster)
                latest_time = max(p[0] for p in cluster)
                groups.append((avg_price, latest_time, len(cluster)))
        return groups

    for price, time, count in group(swing_highs, 1):
        levels.append({
            "price": price, "type": "BSL",
            "source": f"EQH (x{count})", "time": time,
        })

    for price, time, count in group(swing_lows, 1):
        levels.append({
            "price": price, "type": "SSL",
            "source": f"EQL (x{count})", "time": time,
        })

    return levels


def get_htf_levels(df: pd.DataFrame) -> List[Dict]:
    """
    Computes Previous Day/Week/Month High & Low from the candle data.
    """
    levels = []
    data = df.set_index("time")

    for label, rule in [("Day", "D"), ("Week", "W"), ("Month", "ME")]:
        resampled = data.resample(rule).agg({"high": "max", "low": "min"})
        if len(resampled) >= 2:
            prev = resampled.iloc[-2]
            prev_time = resampled.index[-2]
            levels.append({
                "price": prev["high"], "type": "BSL",
                "source": f"P{label[0]}H", "time": prev_time,
            })
            levels.append({
                "price": prev["low"], "type": "SSL",
                "source": f"P{label[0]}L", "time": prev_time,
            })

    return levels


def get_swing_liquidity(df: pd.DataFrame) -> List[Dict]:
    """Every individual (non-grouped) swing high/low also counts as a liquidity pool,
    just a weaker one than an EQH/EQL cluster."""
    levels = []
    for _, row in df[df["swing_high"]].iterrows():
        levels.append({"price": row["high"], "type": "BSL", "source": "Swing High", "time": row["time"]})
    for _, row in df[df["swing_low"]].iterrows():
        levels.append({"price": row["low"], "type": "SSL", "source": "Swing Low", "time": row["time"]})
    return levels


def build_liquidity_levels(df: pd.DataFrame, symbol: str) -> List[Dict]:
    """Full pipeline: find swings, then build all liquidity pool types."""
    df = find_swings(df)
    levels = []
    levels += get_swing_liquidity(df)
    levels += find_equal_highs_lows(df, symbol)
    levels += get_htf_levels(df)
    return df, levels
