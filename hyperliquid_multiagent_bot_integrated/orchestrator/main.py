from fastapi import FastAPI
import asyncio, os, time, json
from typing import Dict, Any, List, Optional
import httpx

from shared.config import SYMBOLS, MAX_POSITIONS, ANALYSIS_INTERVAL_SECONDS
from shared.models import AIDecisionRecord, Position, ServiceStatus, AIDecision
from shared.logging_config import setup_logger

DATA_FILE = "/data/ai_decisions.json"

app = FastAPI(title="Orchestrator")
logger = setup_logger("orchestrator")


@app.get("/health", response_model=ServiceStatus)
def health() -> ServiceStatus:
    return ServiceStatus(ok=True, details={"service": "orchestrator"})


async def _safe_post(client: httpx.AsyncClient, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    for attempt in range(3):
        try:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                return r.json()
            logger.warning(f"{url} -> status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            logger.error(f"Error calling {url}: {e}")
        await asyncio.sleep(1 + attempt)
    return {"ok": False, "error": f"Failed after retries: {url}"}


async def _safe_get(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    for attempt in range(3):
        try:
            r = await client.get(url)
            if r.status_code == 200:
                return r.json()
            logger.warning(f"{url} -> status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            logger.error(f"Error calling {url}: {e}")
        await asyncio.sleep(1 + attempt)
    return {"ok": False, "error": f"Failed after retries: {url}"}


def _load_decisions() -> List[Dict[str, Any]]:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_decision(record: AIDecisionRecord) -> None:
    history = _load_decisions()
    history.append(record.dict())
    history = history[-500:]
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


async def _apply_decision(client: httpx.AsyncClient, symbol: str, decision: Dict[str, Any],
                          equity: float, open_positions: List[Position]) -> None:
    d = AIDecision(**decision)

    cur_total = len(open_positions)

    if d.action == "OPEN":
        if cur_total >= MAX_POSITIONS:
            logger.info(f"Max positions {MAX_POSITIONS} reached, skip OPEN for {symbol}")
            return
        if d.side not in {"long", "short"}:
            logger.info(f"No valid side for OPEN {symbol}")
            return
        if equity <= 0:
            logger.info(f"No equity, skipping OPEN {symbol}")
            return

        size_usd = equity * d.size_pct_balance / 100.0
        logger.info(f"OPEN {symbol} {d.side} size={size_usd:.2f} usd ({d.size_pct_balance}%)")
        await client.post(
            "http://position_manager:8000/open_position",
            json={
                "symbol": symbol,
                "side": d.side,
                "size_usd": size_usd,
                "max_risk_pct": 2.0,
            },
        )

    elif d.action == "CLOSE":
        logger.info(f"CLOSE {symbol}")
        await client.post(
            "http://position_manager:8000/close_position",
            json={"symbol": symbol},
        )
    else:
        logger.info(f"HOLD {symbol}")


async def process_symbol(client: httpx.AsyncClient, symbol: str, equity: float,
                         open_positions: List[Position]) -> Optional[AIDecisionRecord]:
    logger.info(f"Processing {symbol}")

    tech = await _safe_post(client, "http://technical_analyzer:8000/analyze",
                            {"symbol": symbol})
    fib = await _safe_post(client, "http://fibonacci_agent:8000/analyze",
                           {"symbol": symbol})
    gann = await _safe_post(client, "http://gann_agent:8000/analyze",
                            {"symbol": symbol})
    sent = await _safe_post(client, "http://sentiment_agent:8000/analyze",
                            {"symbol": symbol})
    fcst = await _safe_post(client, "http://forecaster_agent:8000/forecast",
                            {"symbol": symbol})

    if not tech.get("ok"):
        logger.warning(f"Skipping {symbol}: tech not ok")
        return None

    ctx = {
        "symbol": symbol,
        "technical": tech,
        "fibonacci": fib,
        "gann": gann,
        "sentiment": sent,
        "forecast": fcst,
        "current_positions": [p.dict() for p in open_positions if p.symbol == symbol],
        "equity": equity,
        "max_positions": MAX_POSITIONS,
    }

    decision_resp = await _safe_post(client, "http://master_ai_agent:8000/decide", ctx)
    if not decision_resp.get("ok"):
        logger.warning(f"Decision not ok for {symbol}: {decision_resp}")
        return None

    decision = decision_resp["decision"]
    record = AIDecisionRecord(
        ts=int(time.time()),
        symbol=symbol,
        context=ctx,
        decision=AIDecision(**decision),
    )
    _save_decision(record)

    await _apply_decision(client, symbol, decision, equity, open_positions)
    return record


async def main_loop():
    while True:
        equity = 1000.0  # TODO: sostituire con equity reale (DB/Hyperliquid)

        async with httpx.AsyncClient(timeout=40) as client:
            pos_resp = await _safe_get(client, "http://position_manager:8000/positions")
            raw_positions = pos_resp.get("positions", [])
            open_positions = [Position(**p) for p in raw_positions]

            tasks = [process_symbol(client, s, equity, open_positions) for s in SYMBOLS]
            await asyncio.gather(*tasks)

            await client.post("http://position_manager:8000/tick_trailing")

        logger.info(f"Sleeping {ANALYSIS_INTERVAL_SECONDS} seconds")
        await asyncio.sleep(ANALYSIS_INTERVAL_SECONDS)


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(main_loop())
