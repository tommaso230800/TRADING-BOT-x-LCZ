from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import json, os, time

from shared.logging_config import setup_logger

app = FastAPI(title="Hyperliquid Multi-Agent Dashboard")
logger = setup_logger("dashboard")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DATA_FILE = "/data/ai_decisions.json"


@app.get("/")
def index(request: Request):
    history = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                history = json.load(f)
        except Exception as e:
            logger.error(f"Error reading {DATA_FILE}: {e}")
    history = history[-100:]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "decisions": list(reversed(history)),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
