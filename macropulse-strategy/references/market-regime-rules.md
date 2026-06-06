# Market Regime Rules

MacroPulse uses deterministic rules to classify market regimes before selecting a strategy template. These rules are intentionally transparent and easy to modify.

## Inputs

- CoinMarketCap Fear and Greed value and classification.
- CoinMarketCap global market cap trend.
- BTC dominance and BTC dominance change.
- BNB, BTC, and ETH quotes and technical indicators.
- Macro news sentiment and risk event score.
- CoinMarketCap trending narrative strength and related assets.

## Regime: Extreme Fear Rebound

Use this regime when the market is in panic or post-panic conditions but macro news is no longer deteriorating.

Typical rules:

- `fear_greed_index <= 30`
- BNB or large-cap RSI is below 40 to 42.
- Global market cap is down over the last week.
- Macro sentiment is mixed or improving, not in free fall.
- No unresolved exchange, bridge, or chain security event blocks new entries.

Preferred template:

- Fear Rebound DCA

Main risk:

- Extreme fear can persist and become a trend continuation selloff.

## Regime: Risk-Off Macro Pressure

Use this regime when macro risk or regulatory/event risk dominates market behavior.

Typical rules:

- News risk event score is elevated.
- CPI, FOMC, inflation, regulation, liquidation, hack, or insolvency topics are active.
- BTC dominance is rising.
- Fear and Greed is falling or below neutral.
- New illiquid altcoin entries should be blocked.

Preferred template:

- Risk-Off Rotation

Main risk:

- Defensive allocation can underperform if the market rapidly returns to risk-on behavior.

## Regime: Narrative Momentum

Use this regime when CMC trending narratives and news narrative signals align.

Typical rules:

- CMC narrative strength is at least 0.75.
- News narrative mentions confirm the same sector.
- Related assets pass liquidity and security filters.
- Macro risk event score is not extreme.
- Volume change confirms attention and tradability.

Preferred template:

- Narrative Momentum

Main risk:

- Narrative attention can reverse faster than daily OHLCV replay can react.

## Template Selection Priority

1. If macro event risk is high and BTC dominance is rising, select Risk-Off Rotation.
2. Else if Fear and Greed is at or below 30 and BNB RSI is weak but stabilizing, select Fear Rebound DCA.
3. Else if CMC narrative strength and news narrative match are strong, select Narrative Momentum.
4. Else use the closest conservative template and lower confidence.

## Explainability Requirement

The final strategy must expose:

- The regime label.
- The confidence score.
- The raw input values used for classification.
- The fired rules.
- Evidence items from both market data and news data.
