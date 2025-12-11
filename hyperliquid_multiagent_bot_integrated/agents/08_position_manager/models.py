from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ServiceStatus(BaseModel):
    ok: bool
    details: Dict[str, Any] = {}


class AIDecision(BaseModel):
    action: str                     # "OPEN" / "CLOSE" / "HOLD"
    side: Optional[str] = None      # "long" / "short" (se OPEN)
    size_pct_balance: float = 0.0   # percentuale di equity da usare
    target_leverage: int = 1
    reason: Optional[str] = None


class Position(BaseModel):
    symbol: str
    side: str
    size_usd: float
    entry_price: float
    pnl: float
    leverage: float
    ts_open: int


class AIDecisionRecord(BaseModel):
    ts: int                         # timestamp epoch
    symbol: str
    context: Dict[str, Any]
    decision: AIDecision
