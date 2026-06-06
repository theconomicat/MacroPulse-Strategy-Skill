# CoinMarketCap Data Sources

MacroPulse is designed to use CoinMarketCap data through live REST calls, CoinMarketCap AI Agent Hub/MCP sources, x402 plan mode, or bundled sample snapshots.

For Agent Hub-specific MCP, Skills Marketplace, and x402 routing, see `cmc-agent-hub-integration.md`.

## Demo Mode

Demo mode reads:

```text
macropulse-strategy/examples/sample-cmc-snapshot.json
```

This file includes:

- Agent Hub routing metadata for MCP, REST, Skills Marketplace, and x402 plan mode.
- Fear and Greed latest value.
- Global market metrics.
- BNB, BTC, and ETH quotes.
- Technical indicator examples such as RSI and EMA trend.
- Trending narrative examples and related assets.
- Macro event annotations.
- Derivatives, on-chain, and DEX security/liquidity examples.

Demo mode requires no API key.

## Live REST Mode

Set:

```bash
export CMC_API_KEY="your_key_here"
```

Then run:

```bash
python macropulse-strategy/scripts/collect_cmc_data.py \
  --assets BNB,BTC,ETH \
  --include fear-greed,global,quotes,technicals,narratives \
  --output /tmp/cmc-live.json
```

The lightweight collector attempts these CoinMarketCap REST resources:

- Fear and Greed latest: `/v3/fear-and-greed/latest`
- Global metrics: `/v1/global-metrics/quotes/latest`
- Quotes: `/v3/cryptocurrency/quotes/latest`

If a request fails, the script prints clear collector errors and falls back to the sample snapshot when no live data is usable.

## AI Agent Hub / MCP Extension

For richer agent deployments, connect the CoinMarketCap AI Agent Hub or CMC MCP server to add:

- Historical Fear and Greed.
- Historical OHLCV and quotes.
- Market cap technical analysis.
- Crypto technical analysis.
- Trending narratives.
- Macro events.
- DEX liquidity and security data.

The strategy schema does not depend on one transport. Live API, MCP, and sample snapshots normalize into the same fields consumed by the generator.

Generate the Agent Hub integration plan:

```bash
python macropulse-strategy/scripts/cmc_agent_hub_plan.py --output /tmp/cmc-agent-hub-plan.json
```

Probe the MCP server when a key is available:

```bash
export CMC_MCP_API_KEY="..."
python macropulse-strategy/scripts/cmc_agent_hub_plan.py --check-live
```

## Required Normalized Fields

```json
{
  "fear_greed": {
    "value": 24,
    "value_classification": "Extreme Fear"
  },
  "global_metrics": {
    "total_market_cap_7d_change_pct": -7.4,
    "btc_dominance_pct": 55.8,
    "btc_dominance_7d_change_pct": 0.35
  },
  "quotes": {
    "BNB": {
      "price_usd": 613.2,
      "percent_change_7d": -6.8,
      "rsi_14": 36.4
    }
  },
  "narratives": [
    {
      "tag": "DeFi",
      "strength_score": 0.78,
      "related_assets": ["BNB", "CAKE", "AAVE", "UNI"]
    }
  ],
  "derivatives": {
    "funding_rate_bias": "neutral_to_slightly_negative",
    "liquidation_risk_score": 0.42
  },
  "on_chain": {
    "bnb_chain_active_addresses_7d_change_pct": 5.6
  },
  "dex_security_liquidity": {
    "bnb_chain_screening_required": true
  }
}
```

## Security

Never commit API keys. The collector reads `CMC_API_KEY` only from the environment.
