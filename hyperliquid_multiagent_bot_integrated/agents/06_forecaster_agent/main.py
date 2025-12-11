from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import pandas as pd
from prophet import Prophet

from shared.hyperliquid_data import fetch_ohlcv_hyperliquid
from shared.models import ForecastSnapshot, ServiceStatus
from shared.logging_config import setup_logger

app = FastAPI(title="Forecaster Agent")
logger = setup_logger("forecaster_agent")


class ForecastRequest(BaseModel):
    symbol: str
    interval: str = "1h"
    periods_ahead: int = 24


class ForecastResponse(BaseModel):
    ok: bool
    symbol: str
    forecast: ForecastSnapshot


@app.get("/health", response_model=ServiceStatus)
def health() -> ServiceStatus:
    return ServiceStatus(ok=True, details={"service": "forecaster_agent"})


@app.post("/forecast", response_model=ForecastResponse)
def forecast(req: ForecastRequest):
    df = fetch_ohlcv_hyperliquid(req.symbol, req.interval, 500)
    if df is None or df.empty:
        logger.warning(f"No data for {req.symbol}")
        raise HTTPException(status_code=400, detail="No data")

    model_df = pd.DataFrame({
        "ds": pd.to_datetime(df["timestamp"], unit="ms"),
        "y": df["close"].astype(float),
    })

    m = Prophet()
    m.fit(model_df)
    future = m.make_future_dataframe(periods=req.periods_ahead, freq="H")
    fcst = m.predict(future)

    last_fcst = fcst.tail(req.periods_ahead)
    start_price = float(model_df["y"].iloc[-1])
    end_price = float(last_fcst["yhat"].iloc[-1])

    if end_price > start_price * 1.01:
        direction = "up"
    elif end_price < start_price * 0.99:
        direction = "down"
    else:
        direction = "flat"

    snap = ForecastSnapshot(direction=direction, start_price=start_price, end_price=end_price)
    return ForecastResponse(ok=True, symbol=req.symbol, forecast=snap)
