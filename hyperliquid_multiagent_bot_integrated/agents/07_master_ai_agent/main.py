from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import os, httpx, json

from shared.config import LLM_API_KEY, LLM_BASE_URL
from shared.models import AIDecision, ServiceStatus
from shared.logging_config import setup_logger

app = FastAPI(title="Master AI Agent")
logger = setup_logger("master_ai_agent")


class Context(BaseModel):
    symbol: str
    technical: Dict[str, Any]
    fibonacci: Dict[str, Any]
    gann: Dict[str, Any]
    sentiment: Dict[str, Any]
    forecast: Dict[str, Any]
    current_positions: List[Dict[str, Any]]
    equity: float
    max_positions: int = 3


class DecisionResponse(BaseModel):
    ok: bool
    decision: AIDecision


@app.get("/health", response_model=ServiceStatus)
def health() -> ServiceStatus:
    return ServiceStatus(ok=True, details={"service": "master_ai_agent"})


def _safe_parse_decision(raw: str) -> AIDecision:
    try:
        data = json.loads(raw)
    except Exception as e:
        logger.error(f"JSON parse error: {e} | raw={raw[:200]}")
        raise HTTPException(status_code=500, detail="Invalid JSON from LLM")

    action = str(data.get("action", "HOLD")).upper()
    if action not in {"OPEN", "CLOSE", "HOLD"}:
        action = "HOLD"

    side = data.get("side")
    if side is not None:
        side = str(side).lower()
        if side not in {"long", "short"}:
            side = None

    size_pct = float(data.get("size_pct_balance", 1.0))
    if size_pct < 1.0:
        size_pct = 1.0
    if size_pct > 10.0:
        size_pct = 10.0

    reason = str(data.get("reason", "")).strip()[:300]

    return AIDecision(
        action=action,
        side=side,
        size_pct_balance=size_pct,
        target_leverage=1.0,
        reason=reason,
    )


@app.post("/decide", response_model=DecisionResponse)
async def decide(ctx: Context):
    if not LLM_API_KEY:
        raise HTTPException(status_code=500, detail="Missing LLM_API_KEY")

    system_prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
    with open(system_prompt_path) as f:
        system_prompt = f.read()

    payload = ctx.dict()
    logger.info(f"Requesting decision for {ctx.symbol}, equity={ctx.equity}")

    user_prompt = (
        "Analizza il contesto di mercato seguente e rispondi SOLO in JSON puro.\n"
        "Schema:\n"
        "{\n"
        '  "action": "OPEN" | "CLOSE" | "HOLD",\n'
        '  "side": "long" | "short" | null,\n'
        '  "size_pct_balance": number,  // 1-10\n'
        '  "target_leverage": 1,\n'
        '  "reason": "stringa breve"\n'
        "}\n\n"
        f"Contesto:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            LLM_BASE_URL,
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": "gpt-5.1",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            },
        )
        if r.status_code != 200:
            logger.error(f"LLM error {r.status_code} | {r.text[:300]}")
            raise HTTPException(status_code=500, detail="LLM request failed")

        data = r.json()

    content = data["choices"][0]["message"]["content"]
    decision = _safe_parse_decision(content)
    logger.info(f"Decision for {ctx.symbol}: {decision.action} {decision.side} {decision.size_pct_balance}%")

    return DecisionResponse(ok=True, decision=decision)
