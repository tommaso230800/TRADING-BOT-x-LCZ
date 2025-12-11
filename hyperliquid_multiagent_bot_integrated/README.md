# Hyperliquid Multi-Agent Trading Bot (Skeleton)

Questo progetto è una struttura multi-agente ispirata all'architettura LCZ, adattata per Hyperliquid
e per il tuo stile di rischio (leva 1x, SL iniziale, trailing dinamico).

Contiene:
- shared/: config, modelli comuni, logging, stub Hyperliquid
- agents/: agenti (technical, fibonacci, gann, sentiment, forecaster, master AI, position manager, learning)
- orchestrator/: il loop principale che coordina gli agenti
- dashboard/: una dashboard base (da trasformare in stile MITRAGLIERE)

⚠️ Importante:
- `shared/hyperliquid_trader.py` e `shared/hyperliquid_data.py` contengono solo stub.
  Devi incollare lì dentro la tua implementazione reale di HyperliquidTrader
  e la funzione per fetchare le candele da Hyperliquid.
