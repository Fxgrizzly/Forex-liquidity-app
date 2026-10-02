"""
MetaTrader 5 connector.

IMPORTANT: The MetaTrader5 python package only works on Windows, and only
if the MT5 terminal is installed and logged into your broker account on
the SAME machine this script runs on. This module will raise a clear
error if MT5 isn't available rather than failing silently.
"""

import pandas as pd

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

TIMEFRAME_MAP = {}
if MT5_AVAILABLE:
    TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }

_initialized = False


def ensure_connection():
    """Connect to the running MT5 terminal. Call once at startup."""
    global _initialized
    if not MT5_AVAILABLE:
        raise RuntimeError(
            "MetaTrader5 package is not installed, or you're not on Windows. "
            "Run: pip install MetaTrader5"
        )
    if _initialized:
        return
    if not mt5.initialize():
        error = mt5.last_error()
        raise RuntimeError(
            f"MT5 initialize() failed: {error}. "
            "Make sure the MT5 terminal is open and logged into your broker."
        )
    _initialized = True


def shutdown():
    global _initialized
    if MT5_AVAILABLE and _initialized:
        mt5.shutdown()
        _initialized = False


def get_rates(symbol: str, timeframe: str, count: int) -> pd.DataFrame:
    """
    Fetch the most recent `count` candles for `symbol` at `timeframe`.
    Returns a DataFrame with columns: time, open, high, low, close, tick_volume
    sorted oldest -> newest.
    """
    ensure_connection()

    tf = TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        raise ValueError(f"Unknown timeframe '{timeframe}'. Options: {list(TIMEFRAME_MAP)}")

    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(
            f"Could not select symbol '{symbol}' in Market Watch. "
            "Check the symbol name matches your broker exactly."
        )

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No rate data returned for {symbol} {timeframe}: {mt5.last_error()}")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df[["time", "open", "high", "low", "close", "tick_volume"]]


def get_account_info() -> dict:
    ensure_connection()
    info = mt5.account_info()
    if info is None:
        return {}
    return info._asdict()
