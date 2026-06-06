# MacroPulse Demo Video Script

Target length: 2 minutes.

## 0:00 - Positioning

MacroPulse is a BNB Hack Track 2 Strategy Skill. It is not a trading bot. It generates validated, backtestable crypto strategy specs from live CoinMarketCap MCP data and risk rules.

Show:

```bash
tree -L 3
```

## 0:20 - CMC MCP Live Collection

Show that the key is local and not committed, then collect live CMC MCP data:

```bash
set -a
. ./.env
set +a
python3 macropulse-strategy/scripts/collect_cmc_data.py --assets BNB,BTC,ETH --primary BNB --output /tmp/macropulse-demo/live-cmc.json
```

Open the JSON and point to:

- `source_mode: live_cmc_mcp`
- `mcp.tools_used`
- quotes, technicals, global metrics, derivatives, macro events, latest news, and narratives

## 0:45 - Generate Strategy

```bash
python3 macropulse-strategy/scripts/generate_strategy.py --cmc-snapshot /tmp/macropulse-demo/live-cmc.json --output /tmp/macropulse-demo/fear-rebound.yaml
```

Show:

- strategy metadata
- asset universe
- market regime
- CMC MCP evidence
- entry, position sizing, exit, and risk

## 1:10 - Validate and Replay

```bash
python3 macropulse-strategy/scripts/validate_strategy.py --strategy /tmp/macropulse-demo/fear-rebound.yaml
python3 macropulse-strategy/scripts/backtest_strategy.py --strategy /tmp/macropulse-demo/fear-rebound.yaml --cmc-snapshot /tmp/macropulse-demo/live-cmc.json
```

Point out:

- required risk fields
- evidence count
- total return
- max drawdown
- fees and slippage

## 1:35 - Sponsor Extension Artifacts

```bash
python3 macropulse-strategy/scripts/twak_quote_plan.py --strategy /tmp/macropulse-demo/fear-rebound.yaml
python3 macropulse-strategy/scripts/x402_data_plan.py --strategy /tmp/macropulse-demo/fear-rebound.yaml
python3 macropulse-strategy/scripts/bnb_agent_manifest.py --strategy /tmp/macropulse-demo/fear-rebound.yaml
```

Explain:

- TWAK output is quote-only.
- x402 output is a no-payment budget plan.
- BNB Agent SDK output is a manifest only, with no private key and no on-chain registration.

## 1:55 - Close

MacroPulse packages live CMC market intelligence into an auditable strategy compiler for AI agents: data collection, regime detection, strategy generation, validation, replay, and safe integration plans.
