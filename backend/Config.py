"""
Central configuration for the liquidity signal engine.
Tweak these values to change which pairs/timeframes are scanned and how
sensitive the liquidity detection is.
"""

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
TIMEFRAME = "M15"
CANDLE_COUNT = 500
SWING_LOOKBACK = 2
EQH_EQL_TOLERANCE_PIPS = 5
SWEEP_MIN_PIPS = 1.5
CONFIRMATION_WINDOW_CANDLES = 8
SL_BUFFER_PIPS = 3
POLL_INTERVAL_SECONDS = 30

PIP_SIZE = {
    "default": 0.0001,
    "JPY": 0.01,
    "XAU": 0.1,
    "XAG": 0.01,
}


def pip_size_for(symbol: str) -> float:
    symbol = symbol.upper()
    for key, size in PIP_SIZE.items():
        if key != "default" and key in symbol:
            return size
    return PIP_SIZE["default"]
