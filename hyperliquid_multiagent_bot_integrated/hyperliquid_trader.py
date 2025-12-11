import logging
import os
import time
from decimal import Decimal
from typing import Dict, Any, List, Optional

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

from .logging_config import setup_logger

logger = setup_logger("HyperliquidTrader")


class HyperliquidTrader:
    """
    Wrapper per operare su Hyperliquid (Perp) con leva 1x.

    Trailing Stop Logica:
    - SL iniziale: -2% (configurabile via INITIAL_SL_PCT)
    - A +0.5% profit: SL a -0.5%
    - A +1.0% profit: SL a 0% (break-even)
    - A +1.1% profit: SL a +0.1%
    - A +2.1% profit: SL a +1.1%
      ... in generale:
        se profit% >= 0.5 ⇒ SL% = profit% - 1.0

    - Long:
        profit% = (last - entry) / entry
        SL price = entry * (1 + sl_pct)
    - Short:
        profit% = (entry - last) / entry
        SL price = entry * (1 - sl_pct)

    - Lo SL non torna mai indietro:
        sl_pct cresce solo (per ogni symbol).
    """

    def __init__(self, testnet: bool = True):
        self.testnet = testnet

        pk = os.getenv("HYPERLIQUID_PRIVATE_KEY")
        address = os.getenv("HYPERLIQUID_ADDRESS")

        if not pk or not address:
            raise RuntimeError(
                "❌ Missing HYPERLIQUID_PRIVATE_KEY or HYPERLIQUID_ADDRESS in environment."
            )

        self.address = address
        api_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL

        self.wallet = Account.from_key(pk)
        self.info = Info(api_url, skip_ws=True)
        self.exchange = Exchange(self.wallet, api_url, account_address=self.address)

        # SL iniziale di default (2%)
        self.default_sl_pct = float(os.getenv("INITIAL_SL_PCT", "0.02"))

        logger.info(
            f"✅ HyperliquidTrader inizializzato | testnet={self.testnet}, address={self.address}"
        )

        # Stato interno trailing
        # es: {"BTC": {"sl_pct": -0.02}}
        self.trailing_state: Dict[str, Dict[str, Any]] = {}

        # Best effort login
        try:
            state = self.info.user_state(self.address)
            if (not state) or (isinstance(state, dict) and not state.get("isLoggedIn", True)):
                if hasattr(self.exchange, "login_if_needed"):
                    logger.info("⏳ Eseguo login_if_needed su Hyperliquid…")
                    self.exchange.login_if_needed()
        except Exception as e:
            logger.warning(f"⚠️ Impossibile verificare login Hyperliquid: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_last_price(self, symbol: str) -> Optional[float]:
        """Prende l'ultimo prezzo (close) da candles 1m."""
        try:
            now_ms = int(time.time() * 1000)
            start_ms = now_ms - 60 * 60 * 1000  # ultima ora

            candles = self.info.candles_snapshot(
                name=symbol,
                interval="1m",
                startTime=start_ms,
                endTime=now_ms,
            )
            if not candles:
                logger.warning(f"⚠️ Nessuna candela trovata per {symbol}")
                return None

            last = candles[-1]
            if isinstance(last, dict):
                px = float(last.get("c", 0.0))
            else:
                px = float(last[4])

            if px <= 0:
                logger.warning(f"⚠️ Prezzo non valido per {symbol}: {px}")
                return None

            return px
        except Exception as e:
            logger.error(f"❌ Errore nel fetch del prezzo per {symbol}: {e}")
            return None

    def _usd_to_size(self, symbol: str, usd_amount: float) -> float:
        """Converte USD -> size (coin) usando l'ultimo prezzo."""
        px = self._get_last_price(symbol)
        if px is None:
            raise RuntimeError(f"Impossibile ottenere il prezzo per {symbol} per calcolare la size.")

        size = Decimal(str(usd_amount)) / Decimal(str(px))
        size_f = float(size)
        if size_f <= 0:
            raise RuntimeError(f"Size calcolata non valida per {symbol}: {size_f}")
        return size_f

    def _compute_sl_pct_from_profit(self, pnl_pct: float) -> float:
        """
        Data una % di profit (0.012 = 1.2%), calcola SL%:

        - Se profit < +0.5%  -> SL = -default_sl_pct (es. -2%)
        - Da +0.5% in su     -> SL = profit% - 1.0%

        Output decimale (0.01 = 1%, -0.02 = -2%).
        """
        pnl_percent = pnl_pct * 100.0

        if pnl_percent < 0.5:
            return -abs(self.default_sl_pct)

        sl_percent = pnl_percent - 1.0
        return sl_percent / 100.0

    # ------------------------------------------------------------------
    # API pubblica
    # ------------------------------------------------------------------

    def open_position(
        self,
        symbol: str,
        side: str,
        usd_amount: float,
        sl_pct: float,
    ) -> Dict[str, Any]:
        """
        Apre una posizione LONG/SHORT su Hyperliquid con leva 1x.
        """
        side = side.lower().strip()
        if side not in {"long", "short"}:
            raise ValueError(f"side non valido: {side}")

        is_buy = side == "long"

        # Leverage 1x
        try:
            self.exchange.update_leverage(1, symbol, is_cross=True)
        except Exception as e:
            logger.warning(f"⚠️ Impossibile settare leverage 1x per {symbol}: {e}")

        size = self._usd_to_size(symbol, usd_amount)

        logger.info(
            f"▶️ OPEN {symbol} | side={side} | size={size:.6f} | notional≈{usd_amount:.2f} USD | sl_init={sl_pct}"
        )

        try:
            resp = self.exchange.market_open(
                name=symbol,
                is_buy=is_buy,
                sz=size,
                px=None,
                slippage=0.05,
            )
            logger.info(f"✅ Order result OPEN {symbol}: {resp}")
        except Exception as e:
            logger.error(f"❌ Errore apertura posizione {symbol}: {e}")
            return {"ok": False, "error": str(e)}

        # Inizializza SL a default (-2%)
        self.trailing_state[symbol] = {
            "sl_pct": -abs(self.default_sl_pct)
        }

        return {"ok": True, "response": resp}

    def close_position(self, symbol: str) -> Dict[str, Any]:
        """Chiude interamente la posizione su un symbol."""
        logger.info(f"▶️ CLOSE {symbol} (market_close)")

        try:
            resp = self.exchange.market_close(
                coin=symbol,
                sz=None,
                px=None,
                slippage=0.05,
            )
            logger.info(f"✅ Order result CLOSE {symbol}: {resp}")
        except Exception as e:
            logger.error(f"❌ Errore chiusura posizione {symbol}: {e}")
            return {"ok": False, "error": str(e)}

        if symbol in self.trailing_state:
            del self.trailing_state[symbol]

        return {"ok": True, "response": resp}

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Ritorna lista di posizioni aperte in formato semplice."""
        try:
            state = self.info.user_state(self.address)
        except Exception as e:
            logger.error(f"❌ Errore lettura user_state Hyperliquid: {e}")
            return []

        positions: List[Dict[str, Any]] = []

        if not state:
            return positions

        asset_positions = state.get("assetPositions", [])
        for pos in asset_positions:
            raw_pos = pos.get("position", pos)
            try:
                szi = float(raw_pos.get("szi", "0"))
            except Exception:
                szi = 0.0

            if szi == 0:
                continue

            side = "long" if szi > 0 else "short"
            symbol = raw_pos.get("coin", "")

            entry_px = float(raw_pos.get("entryPx", "0") or 0.0)
            lev = float(raw_pos.get("leverage", "1") or 1.0)
            unrealized = float(raw_pos.get("unrealizedPnl", "0") or 0.0)

            positions.append(
                {
                    "symbol": symbol,
                    "side": side,
                    "size": abs(szi),
                    "entry_price": entry_px,
                    "leverage": lev,
                    "unrealizedPnl": unrealized,
                    "raw": raw_pos,
                }
            )

        return positions

    def update_trailing_stops(self) -> List[Dict[str, Any]]:
        """
        Trailing stop:
        - SL iniziale = -2%
        - Se profit < 0.5% -> SL = -2%
        - Da +0.5% in poi  -> SL = profit% - 1%

        Lo SL NON torna mai indietro (solo migliora).
        Se il prezzo raggiunge lo SL → chiudiamo la posizione.
        """
        positions = self.get_open_positions()
        results: List[Dict[str, Any]] = []

        for p in positions:
            symbol = p["symbol"]
            side = p["side"]
            entry = p["entry_price"]
            if entry <= 0:
                continue

            last = self._get_last_price(symbol)
            if not last:
                continue

            # Profit % attuale
            if side == "long":
                pnl_pct = (last - entry) / entry
            else:
                pnl_pct = (entry - last) / entry

            state = self.trailing_state.get(symbol, {"sl_pct": -abs(self.default_sl_pct)})
            current_sl_pct = state["sl_pct"]

            target_sl_pct = self._compute_sl_pct_from_profit(pnl_pct)

            # mai peggiorare lo SL
            new_sl_pct = max(current_sl_pct, target_sl_pct)

            # calcolo prezzo stop
            if side == "long":
                sl_price = entry * (1.0 + new_sl_pct)
                stop_hit = last <= sl_price
            else:
                sl_price = entry * (1.0 - new_sl_pct)
                stop_hit = last >= sl_price

            # aggiorna stato
            self.trailing_state[symbol] = {"sl_pct": new_sl_pct}

            if stop_hit:
                logger.info(
                    f"🛑 TRAILING STOP HIT {symbol} | side={side} | "
                    f"entry={entry:.4f} last={last:.4f} sl_px={sl_price:.4f} "
                    f"pnl={pnl_pct*100:.2f}% sl_pct={new_sl_pct*100:.2f}%"
                )
                try:
                    self.exchange.market_close(
                        coin=symbol,
                        sz=None,
                        px=None,
                        slippage=0.05,
                    )
                    if symbol in self.trailing_state:
                        del self.trailing_state[symbol]
                except Exception as e:
                    logger.error(f"❌ Errore chiusura posizione trailing {symbol}: {e}")
            else:
                logger.debug(
                    f"🔁 TRAILING {symbol} | side={side} | entry={entry:.4f} last={last:.4f} "
                    f"pnl={pnl_pct*100:.2f}% sl_pct={new_sl_pct*100:.2f}% sl_px={sl_price:.4f}"
                )

            results.append(
                {
                    "symbol": symbol,
                    "side": side,
                    "entry_price": entry,
                    "last_price": last,
                    "pnl_pct": pnl_pct,
                    "sl_pct": self.trailing_state[symbol]["sl_pct"],
                    "sl_price": sl_price,
                    "stop_hit": stop_hit,
                }
            )

        return results
