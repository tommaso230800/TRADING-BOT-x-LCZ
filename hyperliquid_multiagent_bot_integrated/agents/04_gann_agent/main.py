from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from shared.hyperliquid_data import fetch_ohlcv_hyperliquid
from shared.models import ServiceStatus
from shared.logging_config import setup_logger

app = FastAPI(title="Gann Agent")
logger = setup_logger("gann_agent")


class GannRequest(BaseModel):
    symbol: str
    interval: str = "1h"
    lookback: int = 200


class GannResponse(BaseModel):
    ok: bool
    symbol: str
    last_price: float
    hint: str


@app.get("/health", response_model=ServiceStatus)
def health() -> ServiceStatus:
    return ServiceStatus(ok=True, details={"service": "gann_agent"})


@app.post("/analyze", response_model=GannResponse)
def analyze(req: GannRequest):
    df = fetch_ohlcv_hyperliquid(req.symbol, req.interval, req.lookback)
    if df is None or df.empty:
        logger.warning(f"No data for {req.symbol}")
        raise HTTPException(status_code=400, detail="No data")

    last_price = float(df["close"].iloc[-1])
    # TODO: implementare logica Gann più evoluta
    hint = "gann_placeholder"

    return GannResponse(ok=True, symbol=req.symbol, last_price=last_price, hint=hint)
