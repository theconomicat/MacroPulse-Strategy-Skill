# Market Regime Rules

MacroPulse uses deterministic rules to classify market regimes before selecting a strategy template. Rules are deliberately transparent so another AI agent can audit or modify them.

## Inputs

- CMC MCP `get_global_metrics_latest`: fear/greed, total market cap trend, BTC dominance, liquidity, and TradFi flow context.
- CMC MCP `get_crypto_quotes_latest`: BNB/BTC/ETH prices, market cap, volume, and performance horizons.
- CMC MCP `get_crypto_technical_analysis`: RSI, MACD, moving averages, pivots, and Fibonacci levels.
- CMC MCP `get_global_crypto_derivatives_metrics`: funding, open interest, and liquidation risk.
- CMC MCP `get_upcoming_macro_events`: macro calendar and event catalysts.
- CMC MCP `get_crypto_latest_news`: recent asset-specific news.
- CMC MCP `trending_crypto_narratives`: market narrative attention.

## Regime: Extreme Fear Rebound

Use this regime when broad sentiment is weak but technical conditions indicate a potential large-cap rebound setup.

Typical rules:

- CMC fear/greed index is at or below 30.
- BNB or the primary large-cap RSI is below 40 to 42.
- Global market cap is down over the last week.
- The primary asset must use live CMC quotes and technical analysis.
- Entry should require a pivot reclaim or stabilization gate.

Preferred template:

- Fear Rebound DCA

Main risk:

- Extreme fear can persist and become trend continuation.

## Regime: Risk-Off MCP Derivatives Pressure

Use this regime when market structure or event risk dominates upside potential.

Typical rules:

- Derivatives risk score is elevated.
- BTC dominance is rising.
- Global market cap trend is weak.
- Macro events or latest CMC news indicate material catalyst risk.
- New illiquid altcoin entries should be blocked.

Preferred template:

- Risk-Off Rotation

Main risk:

- Defensive allocation can underperform if the market rapidly returns to risk-on behavior.

## Regime: CMC Narrative Momentum

Use this regime when CMC trending narratives and asset technicals indicate concentrated attention without extreme derivatives risk.

Typical rules:

- A CMC trending narrative is available and rising.
- MACD histogram is not deeply negative.
- Derivatives risk is below the elevated threshold.
- Related assets pass liquidity and market-cap filters.
- CMC latest news and semantic concept search are attached as evidence.

Preferred template:

- Narrative Momentum

Main risk:

- Narrative attention can reverse quickly, and CMC quote horizons are not a substitute for full market microstructure.

## Template Selection Priority

1. If derivatives risk is high or BTC dominance is rising sharply, select Risk-Off Rotation.
2. Else if Fear and Greed is at or below 30 and primary RSI is weak, select Fear Rebound DCA.
3. Else if CMC narratives are rising and technicals are not deeply bearish, select Narrative Momentum.
4. Else use the closest conservative template and lower confidence.

## Explainability Requirement

The final strategy must expose:

- The regime label.
- The confidence score.
- The selected template.
- The raw CMC MCP input values used for classification.
- The fired rules.
- Evidence items from multiple CMC MCP signal categories.
