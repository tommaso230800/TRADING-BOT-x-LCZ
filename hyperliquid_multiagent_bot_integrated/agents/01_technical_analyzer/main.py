from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from shared.hyperliquid_data import fetch_ohlcv_hyperliquid
from shared.models import TechnicalSnapshot, ServiceStatus
from shared.logging_config import setup_logger
from .indicators import compute_indicators

app = FastAPI(title="Technical Analyzer - Hyperliquid")
logger = setup_logger("technical_analyzer")


class AnalyzeRequest(BaseModel):
    symbol: str
    interval: str = "15m"
    limit: int = 200


class AnalyzeResponse(BaseModel):
    ok: bool
    symbol: str
    interval: str
    indicators: TechnicalSnapshot


@app.get("/health", response_model=ServiceStatus)
def health() -> ServiceStatus:
    return ServiceStatus(ok=True, details={"service": "technical_analyzer"})


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    logger.info(f"Analyzing {req.symbol} @ {req.interval}, limit={req.limit}")
    df = fetch_ohlcv_hyperliquid(req.symbol, req.interval, req.limit)
    if df is None or df.empty:
        logger.warning(f"No data for {req.symbol}")
        raise HTTPException(status_code=400, detail="No data")

    df = compute_indicators(df)
    last = df.iloc[-1]

    indicators = TechnicalSnapshot(
        rsi=float(last["rsi"]),
        macd=float(last["macd"]),
        macd_signal=float(last["macd_signal"]),
        atr=float(last["atr"]),
        pivot=float(last["pivot"]),
    )
    return AnalyzeResponse(
        ok=True,
        symbol=req.symbol,
        interval=req.interval,
        indicators=indicators,
    )
