#!/usr/bin/env python3
"""Create a CoinMarketCap Agent Hub integration plan for MacroPulse.

The script is intentionally safe by default: demo mode creates a reproducible
MCP/x402/Skills routing plan without calling paid or authenticated services.
When an API key is present, --check-live attempts a minimal MCP initialization
and tools/list probe so reviewers can see the live integration path.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CMC_MCP_URL = "https://mcp.coinmarketcap.com/mcp"
CMC_REST_URL = "https://pro-api.coinmarketcap.com"
X402_BASE_CHAIN_ID = 8453

OFFICIAL_TOOL_CATEGORIES = [
    {
        "category": "quotes",
        "macro_pulse_use": "BNB/BTC/ETH anchor prices, market cap, volume, and 24h/7d changes.",
        "strategy_fields": ["evidence", "asset_universe", "market_regime"],
    },
    {
        "category": "technical_analysis",
        "macro_pulse_use": "RSI, MACD, EMA, ATR, support/resistance, and breakout/reversal signals.",
        "strategy_fields": ["entry", "exit", "market_regime"],
    },
    {
        "category": "global_market_data",
        "macro_pulse_use": "Total market cap, BTC dominance, ETH dominance, and broad risk appetite.",
        "strategy_fields": ["market_regime", "risk"],
    },
    {
        "category": "fear_and_greed",
        "macro_pulse_use": "Primary sentiment state for fear rebound and risk-on/risk-off switching.",
        "strategy_fields": ["market_regime", "entry", "exit"],
    },
    {
        "category": "trending_narratives",
        "macro_pulse_use": "Narrative momentum ranking and related asset universe construction.",
        "strategy_fields": ["asset_universe", "entry", "evidence"],
    },
    {
        "category": "news",
        "macro_pulse_use": "Macro event and catalyst context for strategy evidence.",
        "strategy_fields": ["evidence", "market_regime"],
    },
    {
        "category": "sentiment",
        "macro_pulse_use": "Social/community sentiment confirmation and divergence checks.",
        "strategy_fields": ["market_regime", "entry", "risk"],
    },
    {
        "category": "on_chain",
        "macro_pulse_use": "Holder, wallet, and flow context for risk and adoption filters.",
        "strategy_fields": ["risk", "asset_universe", "evidence"],
    },
    {
        "category": "derivatives",
        "macro_pulse_use": "Funding, liquidation, and leverage stress checks for risk-off overlays.",
        "strategy_fields": ["market_regime", "risk", "exit"],
    },
    {
        "category": "dex_liquidity_security",
        "macro_pulse_use": "BNB Chain token liquidity and security filters for narrative assets.",
        "strategy_fields": ["asset_universe", "risk"],
    },
    {
        "category": "historical_ohlcv",
        "macro_pulse_use": "Replay/backtest input and walk-forward validation.",
        "strategy_fields": ["backtest"],
    },
    {
        "category": "market_pairs",
        "macro_pulse_use": "Venue, pair concentration, and liquidity distribution checks.",
        "strategy_fields": ["asset_universe", "risk"],
    },
]


def mcp_request(api_key: str, method: str, params: dict[str, Any] | None = None, request_id: int = 1) -> dict[str, Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }
    if params is not None:
        payload["params"] = params
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        CMC_MCP_URL,
        data=data,
        headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "X-CMC-MCP-API-KEY": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return parse_mcp_response(raw)


def parse_mcp_response(raw: str) -> dict[str, Any]:
    stripped = raw.strip()
    if stripped.startswith("data:"):
        chunks = []
        for line in stripped.splitlines():
            if line.startswith("data:"):
                chunks.append(line[5:].strip())
        stripped = "\n".join(chunks).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return {"raw_response": raw[:4000]}


def build_plan(live_status: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "integration": "CoinMarketCap Agent Hub",
        "purpose": "Route CMC MCP, REST, Skills, and x402 data into MacroPulse strategy specs.",
        "official_capabilities_targeted": {
            "mcp_server": CMC_MCP_URL,
            "rest_base_url": CMC_REST_URL,
            "skills_marketplace": "https://coinmarketcap.com/api/skills-marketplace/",
            "x402": {
                "supported": True,
                "chain_id": X402_BASE_CHAIN_ID,
                "settlement_asset": "USDC on Base",
                "mode_in_this_repo": "plan_only_no_payment",
            },
        },
        "mcp_server_config": {
            "mcpServers": {
                "cmc-mcp": {
                    "url": CMC_MCP_URL,
                    "headers": {
                        "X-CMC-MCP-API-KEY": "${CMC_MCP_API_KEY}"
                    },
                }
            }
        },
        "macro_pulse_tool_routing": OFFICIAL_TOOL_CATEGORIES,
        "agent_hub_workflow": [
            "Use CMC MCP or Skills Marketplace routing for real-time structured market context.",
            "Normalize quotes, technicals, fear/greed, narratives, derivatives, on-chain, news, and DEX security into a snapshot.",
            "Generate a deterministic strategy spec with evidence and risk limits.",
            "Validate schema/risk before any final answer.",
            "Run lightweight replay or attach a held-out backtest report.",
            "Optionally produce TWAK quote-only and BNB Agent SDK service deliverables.",
        ],
        "live_probe": live_status or {
            "attempted": False,
            "reason": "Run with --check-live and CMC_MCP_API_KEY to probe initialize/tools-list.",
        },
    }


def check_live() -> dict[str, Any]:
    api_key = os.getenv("CMC_MCP_API_KEY") or os.getenv("CMC_API_KEY")
    if not api_key:
        return {
            "attempted": False,
            "live": False,
            "reason": "CMC_MCP_API_KEY or CMC_API_KEY is not set.",
        }
    status: dict[str, Any] = {
        "attempted": True,
        "live": False,
        "mcp_url": CMC_MCP_URL,
        "responses": {},
        "errors": [],
    }
    try:
        status["responses"]["initialize"] = mcp_request(
            api_key,
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "macropulse-strategy", "version": "1.1.0"},
            },
            1,
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        status["errors"].append(f"initialize failed: {exc}")
    try:
        status["responses"]["tools_list"] = mcp_request(api_key, "tools/list", {}, 2)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        status["errors"].append(f"tools/list failed: {exc}")
    status["live"] = bool(status["responses"]) and not status["errors"]
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a CMC Agent Hub/MCP/x402 integration plan for MacroPulse.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--check-live", action="store_true", help="Probe CMC MCP initialize/tools-list when an API key is available.")
    parser.add_argument("--output", type=Path, help="Write the plan JSON to this file instead of stdout.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    live_status = check_live() if args.check_live else None
    plan = build_plan(live_status)
    rendered = json.dumps(plan, indent=2, sort_keys=False)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"CMC Agent Hub integration plan written to {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
