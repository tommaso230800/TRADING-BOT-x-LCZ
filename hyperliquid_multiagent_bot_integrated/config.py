import os
from dotenv import load_dotenv

load_dotenv()

HYPERLIQUID_ADDRESS = os.getenv("HYPERLIQUID_ADDRESS", "")
HYPERLIQUID_PRIVATE_KEY = os.getenv("HYPERLIQUID_PRIVATE_KEY", "")
HYPERLIQUID_TESTNET = os.getenv("HYPERLIQUID_TESTNET", "true").lower() == "true"

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1/chat/completions")

SYMBOLS = ["BTC", "ETH", "SOL", "DOGE", "SUI", "ADA", "AAVE", "AVAX"]

MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "3"))
ANALYSIS_INTERVAL_SECONDS = int(os.getenv("ANALYSIS_INTERVAL_SECONDS", str(15 * 60)))
TRAILING_TICK_SECONDS = int(os.getenv("TRAILING_TICK_SECONDS", "60"))
