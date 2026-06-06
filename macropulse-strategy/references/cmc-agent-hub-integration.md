# CoinMarketCap Agent Hub Integration

MacroPulse targets the CMC Agent Hub pattern: agent-ready structured data, MCP tool discovery, repeatable strategy workflows, and optional x402 access planning.

## Official Surfaces Used

| Surface | MacroPulse Use | Status |
|---|---|---|
| CMC MCP | Live structured data access for quotes, technicals, news, holder metrics, trending narratives, macro events, derivatives, and global market data. | Implemented in `scripts/collect_cmc_data.py`. |
| CMC Skills Marketplace | Reference pattern for reusable CMC-powered workflows. | Documented and represented in the Agent Hub plan. |
| CMC x402 | Pay-per-request data access with USDC on Base for external runtimes. | Plan-only guardrails in `scripts/x402_data_plan.py`. |

## MCP Configuration

```json
{
  "mcpServers": {
    "cmc-mcp": {
      "url": "https://mcp.coinmarketcap.com/mcp",
      "headers": {
        "X-CMC-MCP-API-KEY": "your-api-key"
      }
    }
  }
}
```

Use `CMC_MCP_API_KEY` or `CMC_API_KEY` in the environment. Never commit keys.

## Live Probe

```bash
python3 macropulse-strategy/scripts/cmc_agent_hub_plan.py \
  --check-live \
  --output /tmp/cmc-agent-hub-plan.json
```

With a key, the script attempts `initialize` and `tools/list` against the CMC MCP endpoint and records the result. Without a key, it emits the routing plan and marks the live probe as not attempted.

## Tool Routing Map

MacroPulse maps live CMC MCP tools into strategy fields:

- `search_cryptos` -> `asset_universe`, CMC ID resolution
- `get_crypto_quotes_latest` -> `asset_universe`, `evidence`, `market_regime`, `backtest`
- `get_crypto_info` -> `evidence`, asset context
- `get_crypto_metrics` -> `risk`, `asset_universe`, `evidence`
- `get_crypto_technical_analysis` -> `entry`, `exit`, `market_regime`
- `get_crypto_latest_news` -> `evidence`, catalyst context
- `search_crypto_info` -> `evidence`, semantic concept context
- `get_global_metrics_latest` -> `market_regime`, `risk`
- `get_global_crypto_derivatives_metrics` -> `market_regime`, `risk`, `exit`
- `get_upcoming_macro_events` -> `market_regime`, `evidence`
- `trending_crypto_narratives` -> `asset_universe`, `entry`, `evidence`
- `get_crypto_marketcap_technical_analysis` -> `market_regime`, broad technical context

## x402 Plan

MacroPulse does not sign x402 payments. It emits a budgeted request plan:

```bash
python3 macropulse-strategy/scripts/x402_data_plan.py \
  --strategy /tmp/live-strategy.yaml \
  --max-budget-usdc 0.08
```

An external agent runtime can decide whether to fund USDC on Base and execute paid calls.

## Why This Matters for Track 2

Track 2 asks for CMC Skills that generate backtestable trading strategies from market data. This integration makes the CMC path explicit:

```text
CMC Agent Hub MCP
-> live normalized market snapshot
-> deterministic regime and strategy template
-> validated strategy spec
-> CMC MCP replay metrics
```
