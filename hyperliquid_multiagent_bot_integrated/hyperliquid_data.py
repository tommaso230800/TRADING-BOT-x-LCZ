import pandas as pd
from typing import Optional

def fetch_ohlcv_hyperliquid(symbol: str, interval: str = "15m", limit: int = 200) -> Optional[pd.DataFrame]:
    """TODO: implementa il fetch delle candele da Hyperliquid.

    Deve restituire un DataFrame con le colonne:
    - timestamp (ms, int)
    - open (float)
    - high (float)
    - low (float)
    - close (float)
    - volume (float)
    """
    raise NotImplementedError("Implementa fetch_ohlcv_hyperliquid con la tua logica di dati")
