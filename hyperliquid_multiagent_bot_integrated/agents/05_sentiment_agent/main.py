from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
import time, json, os

from shared.models import SentimentSnapshot, ServiceStatus
from shared.logging_config import setup_logger

DATA_FILE = "/data/sentiment_cache.json"

app = FastAPI(title="Sentiment Agent")
logger = setup_logger("sentiment_agent")


class SentimentRequest(BaseModel):
    symbol: str


class SentimentResponse(BaseModel):
    ok: bool
    symbol: str
    sentiment: SentimentSnapshot
    cached: bool


def load_cache() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


@app.get("/health", response_model=ServiceStatus)
def health() -> ServiceStatus:
    return ServiceStatus(ok=True, details={"service": "sentiment_agent"})


@app.post("/analyze", response_model=SentimentResponse)
def analyze(req: SentimentRequest):
    cache = load_cache()
    now = int(time.time())
    key = req.symbol.upper()
    cached = cache.get(key)
    if cached and now - cached["ts"] < 600:
        logger.info(f"Using cached sentiment for {req.symbol}")
        snap = SentimentSnapshot(**cached["sentiment"])
        return SentimentResponse(ok=True, symbol=req.symbol, sentiment=snap, cached=True)

    # TODO: chiamare API reali per news/sentiment
    sentiment = SentimentSnapshot(score=0.0, label="neutral", sources=[])

    cache[key] = {"ts": now, "sentiment": sentiment.dict()}
    save_cache(cache)

    return SentimentResponse(ok=True, symbol=req.symbol, sentiment=sentiment, cached=False)
