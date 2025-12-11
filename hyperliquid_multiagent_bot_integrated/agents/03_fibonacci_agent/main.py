from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from shared.hyperliquid_data import fetch_ohlcv_hyperliquid
from shared.models import FibonacciLevels, ServiceStatus
from shared.logging_config import setup_logger

app = FastAPI(title="Fibonacci Agent")
logger = setup_logger("fibonacci_agent")


class FibRequest(BaseModel):
    symbol: str
    interval: str = "4h"
    lookback: int = 100


class FibResponse(BaseModel):
    ok: bool
    symbol: str
    levels: FibonacciLevels


@app.get("/health", response_model=ServiceStatus)
def health() -> ServiceStatus:
    return ServiceStatus(ok=True, details={"service": "fibonacci_agent"})


@app.post("/analyze", response_model=FibResponse)
def analyze(req: FibRequest):
    df = fetch_ohlcv_hyperliquid(req.symbol, req.interval, req.lookback)
    if df is None or df.empty:
        logger.warning(f"No data for {req.symbol}")
        raise HTTPException(status_code=400, detail="No data")

    high = df["high"].max()
    low = df["low"].min()
    diff = high - low
    if diff == 0:
        raise HTTPException(status_code=400, detail="Invalid price range")

    levels = FibonacciLevels(
        level_0=float(high),
        level_0236=float(high - 0.236 * diff),
        level_0382=float(high - 0.382 * diff),
        level_0500=float((high + low) / 2),
        level_0618=float(high - 0.618 * diff),
        level_0786=float(high - 0.786 * diff),
        level_1=float(low),
    )

    return FibResponse(ok=True, symbol=req.symbol, levels=levels)
