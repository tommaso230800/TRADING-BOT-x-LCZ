import os
from typing import List

# Lista dei simboli che l'orchestrator deve processare
SYMBOLS: List[str] = [
    "BTC",
    "ETH",
    "SOL",
    "DOGE",
    "SUI",
    "ADA",
    "AAVE",
    "AVAX",
]

# Numero massimo di posizioni aperte contemporaneamente
MAX_POSITIONS: int = int(os.getenv("MAX_POSITIONS", "3"))

# Intervallo tra un'analisi e la successiva (in secondi)
# Es: 900 = 15 minuti
ANALYSIS_INTERVAL_SECONDS: int = int(
    os.getenv("ANALYSIS_INTERVAL_SECONDS", "900")
)

# Flag se Hyperliquid è in modalità testnet (lo useremo per gli altri servizi)
HYPERLIQUID_TESTNET: bool = os.getenv("HYPERLIQUID_TESTNET", "true").lower() == "true"
