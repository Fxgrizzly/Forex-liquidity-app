"""
Run with:
    uvicorn main:app --host 0.0.0.0 --port 8000

Then on your phone/other devices (same wifi network as this laptop):
    http://<this-laptop's-LAN-IP>:8000
"""

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import mt5_connector
import signal_engine
from config import SYMBOLS, TIMEFRAME, CANDLE_COUNT

app = FastAPI(title="Forex Liquidity Signal App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@app.get("/api/status")
def status():
    try:
        mt5_connector.ensure_connection()
        info = mt5_connector.get_account_info()
        return {"connected": True, "account": info.get("login"), "server": info.get("server")}
    except Exception as e:
        return {"connected": False, "error": str(e)}


@app.get("/api/symbols")
def symbols():
    return {"symbols": SYMBOLS, "timeframe": TIMEFRAME}


@app.get("/api/signals")
def signals(symbol: str = None, timeframe: str = None):
    """
    Returns liquidity signals for one symbol, or all configured symbols if
    none is specified.
    """
    tf = timeframe or TIMEFRAME
    target_symbols = [symbol] if symbol else SYMBOLS

    results = {}
    errors = {}

    for sym in target_symbols:
        try:
            df = mt5_connector.get_rates(sym, tf, CANDLE_COUNT)
            results[sym] = signal_engine.generate_signals(df, sym, tf)
        except Exception as e:
            errors[sym] = str(e)

    if not results and errors:
        raise HTTPException(status_code=502, detail=errors)

    return {"results": results, "errors": errors}


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/manifest.json")
def manifest():
    return FileResponse(str(FRONTEND_DIR / "manifest.json"))


@app.get("/service-worker.js")
def service_worker():
    return FileResponse(str(FRONTEND_DIR / "service-worker.js"), media_type="application/javascript")


@app.on_event("shutdown")
def on_shutdown():
    mt5_connector.shutdown()
