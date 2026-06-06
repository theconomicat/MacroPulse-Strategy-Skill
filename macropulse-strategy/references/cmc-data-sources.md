# CoinMarketCap MCP Data Sources

MacroPulse uses live CoinMarketCap MCP as the primary data source. The collector requires `CMC_MCP_API_KEY` or `CMC_API_KEY` and does not use offline snapshots.

Official CMC MCP endpoint:

```text
https://mcp.coinmarketcap.com/mcp
```

## Environment

```bash
export CMC_MCP_API_KEY="your_key_here"
```

`CMC_API_KEY` is also accepted for convenience. Never commit either variable.

## Live Collection

```bash
python3 macropulse-strategy/scripts/collect_cmc_data.py \
  --assets BNB,BTC,ETH \
  --primary BNB \
  --news-limit 5 \
  --output /tmp/live-cmc.json
```

The collector performs:

1. `initialize`
2. `tools/list`
3. Validation that all expected CMC MCP tools are available
4. Live tool calls
5. Normalization into one agent-readable market snapshot

## CMC MCP Tools Used

MacroPulse currently uses every CMC MCP tool exposed by the live server:

| Tool | MacroPulse Use |
|---|---|
| `search_cryptos` | Resolve asset symbols into CMC IDs. |
| `get_crypto_quotes_latest` | Price, market cap, volume, and performance horizons for BNB/BTC/ETH. |
| `get_crypto_info` | Primary asset metadata, descriptions, tags, and links. |
| `get_crypto_metrics` | Primary asset holder and address metrics. |
| `get_crypto_technical_analysis` | RSI, MACD, moving averages, pivots, and Fibonacci levels. |
| `get_crypto_latest_news` | Recent CMC news for the primary asset. |
| `search_crypto_info` | Semantic concept search for adoption, utility, and risk context. |
| `get_global_metrics_latest` | Global market cap, liquidity, dominance, fear/greed, and TradFi flow context. |
| `get_global_crypto_derivatives_metrics` | Funding, open interest, and liquidation risk context. |
| `get_upcoming_macro_events` | Macro calendar events and market catalysts. |
| `trending_crypto_narratives` | Narrative momentum and sector attention. |
| `get_crypto_marketcap_technical_analysis` | Market-wide technical context. |

## Normalized Snapshot Fields

The collector writes a JSON object with these major fields:

```json
{
  "source_mode": "live_cmc_mcp",
  "mcp": {
    "tools_used": ["search_cryptos", "get_crypto_quotes_latest"]
  },
  "asset_ids": {"BNB": 1839, "BTC": 1, "ETH": 1027},
  "primary_asset": "BNB",
  "quotes": {},
  "technicals": {},
  "global_metrics": {},
  "global_derivatives": {},
  "upcoming_macro_events": {},
  "trending_narratives": [],
  "primary_asset_info": {},
  "primary_asset_metrics": {},
  "primary_asset_concept_search": {},
  "primary_asset_news": [],
  "marketcap_technical_analysis": {}
}
```

## Failure Behavior

The collector exits with a clear message when:

- No CMC key is available.
- The MCP server cannot be reached.
- `tools/list` is missing an expected tool.
- A requested symbol cannot be resolved.
- The primary asset is not included in `--assets`.

This behavior is intentional because the current project is designed to demonstrate a real live CMC MCP pipeline.

## Security

- Keys are read only from environment variables.
- `.env` is ignored by `.gitignore`.
- No script prints the key value.
- CMC MCP is used for read-only market data; it does not execute trades.
