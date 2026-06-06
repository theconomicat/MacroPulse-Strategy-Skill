# Strategy Schema

MacroPulse emits YAML or JSON strategy specs. The schema is intentionally simple so an AI agent, validator, and replay script can read the same file.

## Required Top-Level Fields

| Field | Type | Purpose |
|---|---|---|
| `strategy` | object | Metadata: `name`, `version`, `template`, `generated_at`, and objective. |
| `asset_universe` | object | Tradable research universe and liquidity/security filters. |
| `market_regime` | object | Deterministic regime classification inputs, label, confidence, and fired rules. |
| `evidence` | array | At least two evidence items from CMC, news, technical, narrative, or classifier sources. |
| `entry` | object | Machine-readable entry conditions. Must not be empty. |
| `position_sizing` | object | Sizing method, allocation slices, target weights, or max position reference. |
| `execution` | object | Simulation and quote-only execution assumptions. Real execution must be disabled. |
| `exit` | object | Machine-readable exit, stop, take-profit, or time-stop rules. Must not be empty. |
| `risk` | object | Required risk limits and cost assumptions. Must not be empty. |
| `backtest` | object | Replay engine path, data assumptions, interval, and required metrics. |
| `disclaimers` | array | Required caveats, including no financial advice and no trade execution. |

## Required Strategy Metadata

```yaml
strategy:
  name: fear_rebound_bnb_dca
  version: "1.0.0"
  template: Fear Rebound DCA
```

`strategy.name` should be lowercase snake_case. `strategy.version` should be a string.

## Required Risk Fields

The validator fails when any of these fields are missing or non-positive:

```yaml
risk:
  max_position_pct: 20
  stop_loss_pct: 5
  max_drawdown_pct: 8
```

Recommended optional fields:

```yaml
risk:
  max_daily_loss_pct: 2
  fee_bps: 10
  slippage_bps: 8
  risk_score: medium
  risk_notes:
    - DCA entries stop after the stop-loss or drawdown limit is hit.
```

## Evidence Item Contract

Each evidence item should include:

```yaml
- source: CoinMarketCap fear and greed
  type: sentiment
  data:
    value: 24
    classification: Extreme Fear
  interpretation: Market sentiment is used as a regime input, not as a standalone trade signal.
```

Evidence should be specific enough for a reviewer to understand why a template was selected.

## Entry and Exit Conditions

Use simple lists of machine-readable dictionaries:

```yaml
entry:
  all:
    - cmc_fear_greed_lte: 30
    - bnb_rsi_14_lte: 40
    - news_macro_sentiment_gte: -0.35

exit:
  any:
    - take_profit_pct: 12
    - stop_loss_pct: 5
    - bnb_rsi_14_gte: 68
```

The validator checks only required structure and risk fields. Semantic checks should be handled by a richer agent workflow or future schema extension.

## Execution Safety

Execution must remain quote-only or specification-only:

```yaml
execution:
  mode: specification_only
  trade_execution: disabled
  quote_only: true
```

Any real swap, transfer, approval, private key usage, or wallet action is outside this skill.
