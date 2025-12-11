from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ServiceStatus(BaseModel):
    ok: bool
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class Candle(BaseModel):
    timestamp: int  # ms
    open: float
    high: float
    low: float
    close: float
    volume: float


class TechnicalSnapshot(BaseModel):
    rsi: float
    macd: float
    macd_signal: float
    atr: float
    pivot: float


class FibonacciLevels(BaseModel):
    level_0: float
    level_0236: float
    level_0382: float
    level_0500: float
    level_0618: float
    level_0786: float
    level_1: float


class SentimentSnapshot(BaseModel):
    score: float     # -1..1
    label: str       # "bearish"/"neutral"/"bullish"
    sources: List[Dict[str, Any]] = Field(default_factory=list)


class ForecastSnapshot(BaseModel):
    direction: str   # "up"/"down"/"flat"
    start_price: float
    end_price: float


class Position(BaseModel):
    symbol: str
    side: str            # "long"/"short"
    size_usd: float
    entry_price: float
    pnl: float
    leverage: float = 1.0
    ts_open: int


class AIDecision(BaseModel):
    action: str              # "OPEN"/"CLOSE"/"HOLD"
    side: Optional[str]      # "long"/"short"/None
    size_pct_balance: float  # 1–10
    target_leverage: float
    reason: str


class AIDecisionRecord(BaseModel):
    ts: int
    symbol: str
    context: Dict[str, Any]
    decision: AIDecision


class TradeRecord(BaseModel):
    symbol: str
    side: str
    size_usd: float
    entry_price: float
    exit_price: float
    pnl: float
    ts_open: int
    ts_close: int
