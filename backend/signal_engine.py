"""
The core signal logic, directly implementing the "Sharp Entry Setup" from
your Understanding Liquidity notes:

    Stop Hunt (SH)  ->  Break in Market Structure (BMS/ChoCh)  ->  Entry

This is a rules-based pattern matcher, NOT a guarantee. Treat every
signal as a candidate to review, not an automatic trade.
"""

from typing import List, Dict
import pandas as pd

from config import SWEEP_MIN_PIPS, CONFIRMATION_WINDOW_CANDLES, SL_BUFFER_PIPS, pip_size_for
from liquidity import build_liquidity_levels
from structure import detect_structure_events


def find_sweeps(df: pd.DataFrame, levels: List[Dict], symbol: str) -> List[Dict]:
    """
    A sweep of a BSL level: candle high > level price (by at least SWEEP_MIN_PIPS)
    AND candle close < level price (wick rejected back below).
    A sweep of an SSL level: candle low < level price (by at least SWEEP_MIN_PIPS)
    AND candle close > level price (wick rejected back above).
    """
    pip = pip_size_for(symbol)
    min_dist = SWEEP_MIN_PIPS * pip
    sweeps = []

    for level in levels:
        relevant_candles = df[df["time"] > level["time"]]
        for _, row in relevant_candles.iterrows():
            if level["type"] == "BSL":
                if row["high"] >= level["price"] + min_dist and row["close"] < level["price"]:
                    sweeps.append({
                        "time": row["time"], "level": level, "direction": "bearish",
                        "sweep_price": row["high"],
                    })
                    break
            else:
                if row["low"] <= level["price"] - min_dist and row["close"] > level["price"]:
                    sweeps.append({
                        "time": row["time"], "level": level, "direction": "bullish",
                        "sweep_price": row["low"],
                    })
                    break

    return sweeps


def confirm_with_structure(sweeps: List[Dict], structure_events: List[Dict],
                            df: pd.DataFrame) -> List[Dict]:
    """
    For each sweep, look forward up to CONFIRMATION_WINDOW_CANDLES for a
    ChoCh or BOS event in the direction implied by the sweep.
    """
    confirmed = []
    times = df["time"].tolist()

    for sweep in sweeps:
        try:
            sweep_idx = times.index(sweep["time"])
        except ValueError:
            continue

        window_end_idx = min(sweep_idx + CONFIRMATION_WINDOW_CANDLES, len(times) - 1)
        window_start_time = sweep["time"]
        window_end_time = times[window_end_idx]

        for event in structure_events:
            if window_start_time < event["time"] <= window_end_time:
                if event["direction"] == sweep["direction"]:
                    confirmed.append({
                        "sweep": sweep,
                        "structure_event": event,
                    })
                    break

    return confirmed


def build_signal(confirmed: Dict, symbol: str, timeframe: str) -> Dict:
    sweep = confirmed["sweep"]
    event = confirmed["structure_event"]
    pip = pip_size_for(symbol)

    direction = "BUY" if sweep["direction"] == "bullish" else "SELL"
    entry = event["price"]

    if direction == "BUY":
        stop_loss = sweep["sweep_price"] - (SL_BUFFER_PIPS * pip)
    else:
        stop_loss = sweep["sweep_price"] + (SL_BUFFER_PIPS * pip)

    risk = abs(entry - stop_loss)
    take_profit = entry + (2 * risk) if direction == "BUY" else entry - (2 * risk)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": direction,
        "entry": round(entry, 5),
        "stop_loss": round(stop_loss, 5),
        "take_profit": round(take_profit, 5),
        "risk_reward": 2.0,
        "reason": (
            f"Swept {sweep['level']['source']} liquidity ({sweep['level']['type']}) "
            f"at {round(sweep['level']['price'], 5)}, then {event['event']} confirmed "
            f"{event['direction']} reversal."
        ),
        "sweep_time": str(sweep["time"]),
        "confirmation_time": str(event["time"]),
    }


def generate_signals(df: pd.DataFrame, symbol: str, timeframe: str) -> Dict:
    """
    Full pipeline. Returns:
        {"signals": [...], "levels": [...]}
    """
    df_with_swings, levels = build_liquidity_levels(df, symbol)
    structure_events = detect_structure_events(df_with_swings)
    sweeps = find_sweeps(df_with_swings, levels, symbol)
    confirmed = confirm_with_structure(sweeps, structure_events, df_with_swings)

    signals = [build_signal(c, symbol, timeframe) for c in confirmed]
    signals.sort(key=lambda s: s["confirmation_time"], reverse=True)

    serializable_levels = [
        {**lvl, "time": str(lvl["time"]), "price": round(lvl["price"], 5)}
        for lvl in levels
    ]

    return {"signals": signals, "levels": serializable_levels}
