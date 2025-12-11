import logging
from typing import Dict, Any, List

from .logging_config import setup_logger

logger = setup_logger("HyperliquidTrader")


class HyperliquidTrader:
    """WRAPPER PER IL TUO CODICE ESISTENTE.

    TODO:
    - Incolla qui dentro la tua implementazione attuale di HyperliquidTrader
      (quella che usa leverage 1x, SL -2%, trailing +1.8%, ecc.).
    - Mantieni la stessa interfaccia pubblica indicata sotto, o adatta questa ai tuoi metodi.
    """

    def __init__(self, testnet: bool = True):
        raise NotImplementedError("Incolla qui la tua implementazione di HyperliquidTrader.__init__")

    def open_position(self, symbol: str, side: str, usd_amount: float, sl_pct: float) -> Dict[str, Any]:
        """Apre una posizione LONG/SHORT su Hyperliquid con leva 1x e SL iniziale sl_pct (es. 0.02 per 2%)."""
        raise NotImplementedError("Incolla qui la tua logica di apertura posizione")

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """Chiude la posizione su un symbol."""
        raise NotImplementedError("Incolla qui la tua logica di chiusura posizione")

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Ritorna una lista di posizioni aperte."""
        raise NotImplementedError("Incolla qui la tua logica di lettura posizioni")

    def update_trailing_stops(self) -> List[Dict[str, Any]]:
        """Applica la tua logica di trailing stop (attivazione a +1.8%, update ogni 60s, ecc.)."""
        raise NotImplementedError("Incolla qui la tua logica di trailing")
