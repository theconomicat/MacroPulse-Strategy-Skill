# Strategy Schema

MacroPulse emits YAML or JSON strategy specs. The schema is intentionally simple so an AI agent, validator, and replay script can read the same file.

## Required Top-Level Fields

| Field | Type | Purpose |
|---|---|---|
| `strategy` | object | Metadata: `name`, `version`, `template`, `generated_at`, and objective. |
| `asset_universe` | object | Research universe and liquidity/security filters. |
| `market_regime` | object | Deterministic regime classification inputs, label, confidence, and fired rules. |
| `evidence` | array | At least two evidence items from CMC MCP signal categories or the deterministic classifier. |
| `entry` | object | Machine-readable entry conditions. Must not be empty. |
| `position_sizing` | object | Sizing method, allocation slices, target weights, or max position reference. |
| `execution` | object | Simulation and quote-only execution assumptions. Real execution must be disabled. |
| `exit` | object | Machine-readable exit, stop, take-profit, or time-stop rules. Must not be empty. |
| `risk` | object | Required risk limits and cost assumptions. Must not be empty. |
| `backtest` | object | Replay engine path, live snapshot requirement, and required metrics. |
| `disclaimers` | array | Required caveats, including no financial advice and no trade execution. |

## Required Strategy Metadata

```yaml
strategy:
  name: live_cmc_fear_rebound_dca
  version: "2.0.0"
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
- source: CMC MCP get_global_metrics_latest
  type: global_market
  data:
    sentiment:
      fear_greed:
        current:
          index: 24
          value: Extreme Fear
  interpretation: Global market stress and fear/greed drive regime selection.
```

Evidence should be specific enough for a reviewer to understand why a template was selected.

Preferred evidence categories:

- CoinMarketCap MCP tools inventory
- CMC global metrics and fear/greed
- CMC quotes
- CMC technical indicators
- CMC derivatives
- CMC trending narratives
- CMC macro events and latest CMC news
- CMC info, metrics, semantic search, and market-cap technical context
- Deterministic regime classifier

## Entry and Exit Conditions

Use simple lists of machine-readable dictionaries:

```yaml
entry:
  all:
    - cmc_fear_greed_lte: 30
    - primary_rsi14_lte: 42
    - global_market_cap_7d_change_lte_pct: -5

exit:
  any:
    - take_profit_pct: 12
    - stop_loss_pct: 5
    - primary_rsi14_gte: 68
```

The validator checks required structure and risk fields. Semantic checks should be handled by a richer agent workflow or future schema extension.

## Execution Safety

Execution must remain quote-only or specification-only:

```yaml
execution:
  mode: specification_only
  trade_execution: disabled
  quote_only: true
```

Any real swap, transfer, approval, private key usage, or wallet action is outside this skill.
