# CoinMarketCap Agent Hub Integration

MacroPulse targets the CMC Agent Hub pattern: agent-ready structured data, pre-computed signals, repeatable Skills workflows, and MCP/x402 access paths.

## Official Surfaces Used

| Surface | MacroPulse Use | Status |
|---|---|---|
| CMC MCP | Live structured data access for quotes, technicals, news, holder metrics, trending narratives, and global market data. | Config and live probe supported by `scripts/cmc_agent_hub_plan.py`. |
| CMC REST API | Fallback direct integration for fear/greed, global metrics, and quotes. | Implemented in `scripts/collect_cmc_data.py`. |
| CMC Skills Marketplace | Intended routing layer for repeatable market report, token research, and strategy workflows. | Documented and represented in the Agent Hub plan. |
| CMC x402 | Pay-per-request data access with USDC on Base when no API key is available. | Plan-only guardrails in `scripts/x402_data_plan.py`. |

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
python macropulse-strategy/scripts/cmc_agent_hub_plan.py \
  --check-live \
  --output /tmp/cmc-agent-hub-plan.json
```

Without a key, the script still emits a complete integration plan. With a key, it attempts `initialize` and `tools/list` against the CMC MCP endpoint.

## Tool Routing Map

MacroPulse maps CMC Agent Hub data categories into strategy fields:

- Quotes -> `asset_universe`, `evidence`, `market_regime`
- Technical analysis -> `entry`, `exit`, `market_regime`
- Global market data -> `market_regime`, `risk`
- Fear and Greed -> `market_regime`, `entry`, `exit`
- Trending narratives -> `asset_universe`, `entry`, `evidence`
- News and sentiment -> `market_regime`, `evidence`
- On-chain and holder data -> `risk`, `asset_universe`
- Derivatives -> `market_regime`, `risk`, `exit`
- DEX liquidity and security -> `asset_universe`, `risk`
- Historical OHLCV -> `backtest`

## x402 Plan

MacroPulse does not sign x402 payments. It emits a budgeted request plan:

```bash
python macropulse-strategy/scripts/x402_data_plan.py \
  --strategy /tmp/fear-rebound.yaml \
  --max-budget-usdc 0.08
```

An external agent runtime can decide whether to fund USDC on Base and execute paid calls.

## Why This Matters for Track 2

Track 2 asks for CMC Skills that generate backtestable trading strategies from market data. This integration makes the CMC path explicit:

```text
CMC Agent Hub / MCP / Skills / x402
-> normalized market snapshot
-> deterministic regime and strategy template
-> validated strategy spec
-> replay metrics
```
