# Demo Prompts

Use these prompts to test the skill as an AI-agent workflow with live CMC MCP data.

## Full Live Strategy

```text
Use MacroPulse Strategy Skill with live CoinMarketCap MCP data for BNB, BTC, and ETH. Collect the CMC MCP snapshot, generate a 7-day strategy spec, validate it, run the replay, and return the evidence and risk limits.
```

Expected commands:

```bash
python3 macropulse-strategy/scripts/collect_cmc_data.py --assets BNB,BTC,ETH --primary BNB --output /tmp/live-cmc.json
python3 macropulse-strategy/scripts/generate_strategy.py --cmc-snapshot /tmp/live-cmc.json --output /tmp/live-strategy.yaml
python3 macropulse-strategy/scripts/validate_strategy.py --strategy /tmp/live-strategy.yaml
python3 macropulse-strategy/scripts/backtest_strategy.py --strategy /tmp/live-strategy.yaml --cmc-snapshot /tmp/live-cmc.json
```

## Fear Rebound DCA

```text
Generate a BNB Fear Rebound DCA strategy from live CMC MCP fear/greed, BNB RSI, global market cap trend, CMC quotes, and macro event context.
```

Expected command:

```bash
python3 macropulse-strategy/scripts/generate_strategy.py --cmc-snapshot /tmp/live-cmc.json --template fear-rebound-dca --output /tmp/fear-rebound.yaml
```

## Risk-Off Rotation

```text
Create a risk-off crypto rotation strategy using live CMC MCP global metrics, BTC dominance, derivatives pressure, macro events, and BNB/BTC/ETH technical analysis. The output must block new illiquid altcoin entries and include risk limits.
```

Expected command:

```bash
python3 macropulse-strategy/scripts/generate_strategy.py --cmc-snapshot /tmp/live-cmc.json --template risk-off-rotation --output /tmp/risk-off.yaml
```

## Narrative Momentum

```text
Use CMC MCP trending narratives, latest CMC news, quotes, technical indicators, and semantic concept search to generate a narrative momentum strategy. Include liquidity filters, evidence, validation, replay metrics, and caveats.
```

Expected command:

```bash
python3 macropulse-strategy/scripts/generate_strategy.py --cmc-snapshot /tmp/live-cmc.json --template narrative-momentum --output /tmp/narrative.yaml
```

## Trust Wallet Quote-Only Plan

```text
Convert the generated strategy into a Trust Wallet Agent Kit quote-only execution plan. Do not execute any transaction.
```

Expected command:

```bash
python3 macropulse-strategy/scripts/twak_quote_plan.py --strategy /tmp/live-strategy.yaml
```

## Full Judge Pipeline

```text
Run the complete MacroPulse live CMC MCP pipeline and show every artifact produced for DoraHacks judging.
```

Expected command:

```bash
PYTHON_BIN=.venv/bin/python ./demo/run_demo.sh /tmp/macropulse-live-demo
```

Expected artifacts:

- CMC Agent Hub live probe plan
- live CMC MCP snapshot
- strategy YAML
- validation output
- CMC MCP replay metrics
- TWAK quote-only plan
- x402 data plan
- BNB Agent SDK manifest
