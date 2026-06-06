# MacroPulse Demo Video Script

Target length: 2 minutes.

## 0:00 - Positioning

MacroPulse is a BNB Hack Track 2 Strategy Skill. It is not a trading bot. It generates validated, backtestable crypto strategy specs from CoinMarketCap Agent Hub data, macro news signals, and risk rules.

Show:

```bash
tree -L 3
```

## 0:20 - CMC Agent Hub Routing

Show that the project knows how it would route CMC MCP, REST, Skills Marketplace, and x402 sources.

```bash
python macropulse-strategy/scripts/cmc_agent_hub_plan.py --output /tmp/macropulse-demo/cmc-agent-hub-plan.json
```

Open the JSON and point to:

- MCP endpoint
- tool routing categories
- x402 plan-only guardrail

## 0:45 - Generate Strategy

```bash
python macropulse-strategy/scripts/generate_strategy.py --demo --output /tmp/macropulse-demo/fear-rebound.yaml
```

Show:

- strategy metadata
- asset universe
- market regime
- CMC evidence
- entry, position sizing, exit, and risk

## 1:10 - Validate and Replay

```bash
python macropulse-strategy/scripts/validate_strategy.py --strategy /tmp/macropulse-demo/fear-rebound.yaml
python macropulse-strategy/scripts/backtest_strategy.py --strategy /tmp/macropulse-demo/fear-rebound.yaml --demo
```

Point out:

- required risk fields
- evidence count
- total return
- max drawdown
- fees and slippage

## 1:35 - Sponsor Extension Artifacts

```bash
python macropulse-strategy/scripts/twak_quote_plan.py --strategy /tmp/macropulse-demo/fear-rebound.yaml
python macropulse-strategy/scripts/x402_data_plan.py --strategy /tmp/macropulse-demo/fear-rebound.yaml
python macropulse-strategy/scripts/bnb_agent_manifest.py --strategy /tmp/macropulse-demo/fear-rebound.yaml
```

Explain:

- TWAK output is quote-only.
- x402 output is a no-payment budget plan.
- BNB Agent SDK output is a manifest only, with no private key and no on-chain registration.

## 1:55 - Close

MacroPulse packages CMC market intelligence into an auditable strategy compiler for AI agents: data collection, regime detection, strategy generation, validation, replay, and safe integration plans.
