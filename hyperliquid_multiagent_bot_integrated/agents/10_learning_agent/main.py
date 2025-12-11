from fastapi import FastAPI
import asyncio, time, json, os
from typing import Dict, Any, List

from shared.models import TradeRecord, ServiceStatus
from shared.logging_config import setup_logger

TRADES_FILE = "/data/trades_history.json"
SUGGESTIONS_FILE = "/data/strategy_suggestions.json"

app = FastAPI(title="Learning Agent ProFiT")
logger = setup_logger("learning_agent")


@app.get("/health", response_model=ServiceStatus)
def health() -> ServiceStatus:
    return ServiceStatus(ok=True, details={"service": "learning_agent"})


async def evolution_loop():
    while True:
        await asyncio.sleep(48 * 3600)  # 48 ore

        if not os.path.exists(TRADES_FILE):
            continue

        try:
            with open(TRADES_FILE, "r") as f:
                raw_trades = json.load(f)
        except Exception as e:
            logger.error(f"Error reading trades file: {e}")
            continue

        trades: List[TradeRecord] = []
        for t in raw_trades:
            try:
                trades.append(TradeRecord(**t))
            except Exception:
                continue

        total = len(trades)
        if total == 0:
            continue

        wins = [t for t in trades if t.pnl > 0]
        win_rate = len(wins) / total * 100

        suggestions = {
            "timestamp": int(time.time()),
            "stats": {
                "total_trades": total,
                "win_rate": win_rate,
            },
            "proposed_params": {
                "max_positions": 3,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
            },
        }

        history: List[Dict[str, Any]]
        if os.path.exists(SUGGESTIONS_FILE):
            try:
                with open(SUGGESTIONS_FILE, "r") as f:
                    history = json.load(f)
            except Exception:
                history = []
        else:
            history = []

        history.append(suggestions)
        history = history[-100:]
        os.makedirs(os.path.dirname(SUGGESTIONS_FILE), exist_ok=True)
        with open(SUGGESTIONS_FILE, "w") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        logger.info(f"Learning cycle completed, win_rate={win_rate:.2f}%")


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(evolution_loop())
