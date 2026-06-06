# Demo Prompts

Use these prompts to test the skill as an AI-agent workflow.

## Fear Rebound DCA

```text
Use MacroPulse Strategy Skill to generate a 7-day BNB strategy from sample macro news, CoinMarketCap fear and greed, BNB technicals, and global market data. Return a YAML strategy spec, validate it, and run the demo replay.
```

Expected commands:

```bash
python macropulse-strategy/scripts/generate_strategy.py --demo --template fear-rebound-dca --output /tmp/fear-rebound.yaml
python macropulse-strategy/scripts/validate_strategy.py --strategy /tmp/fear-rebound.yaml
python macropulse-strategy/scripts/backtest_strategy.py --strategy /tmp/fear-rebound.yaml --demo
```

## Risk-Off Rotation

```text
Create a risk-off crypto strategy for a week with CPI, FOMC, BTC dominance, and market drawdown evidence. The output must block new illiquid altcoin entries and include risk limits.
```

Expected command:

```bash
python macropulse-strategy/scripts/generate_strategy.py --demo --template risk-off-rotation
```

## Narrative Momentum

```text
Use CMC trending narratives and the sample news feed to generate a narrative momentum strategy. Include liquidity filters, evidence, validation, and caveats.
```

Expected command:

```bash
python macropulse-strategy/scripts/generate_strategy.py --demo --template narrative-momentum
```

## Trust Wallet Quote-Only Plan

```text
Convert the generated strategy into a Trust Wallet Agent Kit quote-only execution plan. Do not execute any transaction.
```

Expected command:

```bash
python macropulse-strategy/scripts/twak_quote_plan.py --strategy /tmp/fear-rebound.yaml
```

## Live CoinMarketCap Collection

```text
Use my CMC_API_KEY to collect live BNB, BTC, and ETH market context, then generate a strategy spec from the live snapshot and sample news input.
```

Expected commands:

```bash
export CMC_API_KEY="..."
python macropulse-strategy/scripts/collect_cmc_data.py --assets BNB,BTC,ETH --output /tmp/cmc-live.json
python macropulse-strategy/scripts/generate_strategy.py --input macropulse-strategy/examples/sample-news-input.json --cmc-snapshot /tmp/cmc-live.json
```
