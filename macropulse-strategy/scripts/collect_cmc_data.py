#!/usr/bin/env python3
"""Collect a live CoinMarketCap MCP snapshot for MacroPulse.

This collector is live-only. It calls every CMC MCP tool currently exposed by
https://mcp.coinmarketcap.com/mcp and normalizes the result for strategy
generation.
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

MCP_TOOL_NAMES = [
    "get_crypto_metrics",
    "get_global_crypto_derivatives_metrics",
    "search_cryptos",
    "get_upcoming_macro_events",
    "get_crypto_quotes_latest",
    "get_crypto_info",
    "trending_crypto_narratives",
    "search_crypto_info",
    "get_crypto_latest_news",
    "get_crypto_technical_analysis",
    "get_global_metrics_latest",
    "get_crypto_marketcap_technical_analysis",
]


def parse_mcp_payload(raw: str) -> dict[str, Any]:
    stripped = raw.strip()
    if stripped.startswith("data:"):
        stripped = "\n".join(line[5:].strip() for line in stripped.splitlines() if line.startswith("data:")).strip()
    return json.loads(stripped)


def mcp_request(api_key: str, method: str, params: dict[str, Any] | None = None, request_id: int = 1) -> dict[str, Any]:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params
    request = urllib.request.Request(
        CMC_MCP_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "X-CMC-MCP-API-KEY": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        return parse_mcp_payload(response.read().decode("utf-8", errors="replace"))


def mcp_tool_call(api_key: str, name: str, arguments: dict[str, Any] | None = None, request_id: int = 1) -> dict[str, Any]:
    return mcp_request(api_key, "tools/call", {"name": name, "arguments": arguments or {}}, request_id)


def extract_text_content(response: dict[str, Any]) -> str:
    content = response.get("result", {}).get("content", [])
    if not content:
        return ""
    text_chunks = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
    return "\n".join(text_chunks).strip()


def parse_tool_content(response: dict[str, Any]) -> Any:
    text = extract_text_content(response)
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}


def table_to_records(table: Any) -> list[dict[str, Any]]:
    if not isinstance(table, dict):
        return []
    headers = table.get("headers")
    rows = table.get("rows")
    if not isinstance(headers, list) or not isinstance(rows, list):
        return []
    records: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, list):
            records.append({str(header): row[index] if index < len(row) else None for index, header in enumerate(headers)})
    return records


def records_from_tool_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and "headers" in payload and "rows" in payload:
        return table_to_records(payload)
    return []


def resolve_assets(api_key: str, symbols: list[str]) -> tuple[dict[str, int], dict[str, Any], list[dict[str, Any]]]:
    asset_ids: dict[str, int] = {}
    search_payloads: dict[str, Any] = {}
    search_records: list[dict[str, Any]] = []
    for index, symbol in enumerate(symbols, start=100):
        response = mcp_tool_call(api_key, "search_cryptos", {"query": symbol, "limit": 5}, index)
        if response.get("result", {}).get("isError"):
            raise SystemExit(f"CMC MCP search_cryptos failed for {symbol}: {extract_text_content(response)}")
        payload = parse_tool_content(response)
        search_payloads[symbol] = payload
        if isinstance(payload, list):
            matches = [item for item in payload if isinstance(item, dict)]
        else:
            matches = []
        exact_matches = [item for item in matches if str(item.get("symbol", "")).upper() == symbol.upper()]
        candidates = exact_matches or matches
        if not candidates:
            raise SystemExit(f"CMC MCP search_cryptos returned no candidate for symbol: {symbol}")
        best = sorted(candidates, key=lambda item: int(item.get("rank") or 999999))[0]
        if best.get("id") is None:
            raise SystemExit(f"CMC MCP search_cryptos candidate has no id for symbol: {symbol}")
        asset_ids[symbol.upper()] = int(best["id"])
        search_records.append(best)
    return asset_ids, search_payloads, search_records


def normalize_quotes(payload: Any) -> dict[str, dict[str, Any]]:
    records = records_from_tool_payload(payload)
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        symbol = str(record.get("symbol", "")).upper()
        if not symbol:
            continue
        existing = result.get(symbol)
        if existing:
            existing_rank = existing.get("rank")
            new_rank = record.get("rank")
            if existing_rank is not None and new_rank is not None and float(new_rank) > float(existing_rank):
                continue
        result[symbol] = record
    return result


def normalize_narratives(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("categoryList"), dict):
        return table_to_records(payload["categoryList"])
    return []


def collect_mcp_snapshot(api_key: str, assets: list[str], primary_symbol: str, news_limit: int, concept_prompt: str) -> dict[str, Any]:
    initialized = mcp_request(
        api_key,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "macropulse-strategy", "version": "2.0.0"},
        },
        1,
    )
    tools_list = mcp_request(api_key, "tools/list", {}, 2)
    tool_names = [tool.get("name") for tool in tools_list.get("result", {}).get("tools", []) if isinstance(tool, dict)]
    missing_tools = [name for name in MCP_TOOL_NAMES if name not in tool_names]
    if missing_tools:
        raise SystemExit(f"CMC MCP server is missing expected tools: {', '.join(missing_tools)}")

    asset_ids, search_payloads, search_records = resolve_assets(api_key, assets)
    primary = primary_symbol.upper()
    if primary not in asset_ids:
        raise SystemExit(f"Primary symbol {primary} must be included in --assets.")
    ids_csv = ",".join(str(asset_ids[symbol]) for symbol in assets)
    primary_id = str(asset_ids[primary])

    raw_results: dict[str, Any] = {}

    def call_and_parse(tool_name: str, arguments: dict[str, Any] | None = None, request_id: int = 200) -> Any:
        response = mcp_tool_call(api_key, tool_name, arguments or {}, request_id)
        payload = parse_tool_content(response)
        raw_results[tool_name] = payload
        return payload

    raw_results["search_cryptos"] = search_payloads
    global_metrics = call_and_parse("get_global_metrics_latest", {}, 201)
    derivatives = call_and_parse("get_global_crypto_derivatives_metrics", {}, 202)
    macro_events = call_and_parse("get_upcoming_macro_events", {}, 203)
    narratives_payload = call_and_parse("trending_crypto_narratives", {}, 204)
    quotes_payload = call_and_parse("get_crypto_quotes_latest", {"id": ids_csv}, 205)
    info_payload = call_and_parse("get_crypto_info", {"id": primary_id}, 206)
    metrics_payload = call_and_parse("get_crypto_metrics", {"id": primary_id}, 207)
    concept_payload = call_and_parse("search_crypto_info", {"id": primary_id, "prompt": concept_prompt}, 208)
    news_payload = call_and_parse("get_crypto_latest_news", {"id": primary_id, "limit": news_limit}, 209)
    marketcap_technicals = call_and_parse("get_crypto_marketcap_technical_analysis", {}, 210)

    technicals: dict[str, Any] = {}
    for offset, symbol in enumerate(assets, start=211):
        technicals[symbol] = call_and_parse("get_crypto_technical_analysis", {"id": str(asset_ids[symbol])}, offset)

    return {
        "snapshot_time": datetime.now(timezone.utc).isoformat(),
        "source_mode": "live_cmc_mcp",
        "mcp": {
            "url": CMC_MCP_URL,
            "initialize_ok": "result" in initialized,
            "tools_list_ok": "result" in tools_list,
            "tools_required": MCP_TOOL_NAMES,
            "tools_available": tool_names,
            "tools_used": MCP_TOOL_NAMES,
        },
        "asset_ids": asset_ids,
        "search_results": search_records,
        "primary_asset": primary,
        "quotes": normalize_quotes(quotes_payload),
        "technicals": technicals,
        "global_metrics": global_metrics,
        "global_derivatives": derivatives,
        "upcoming_macro_events": macro_events,
        "trending_narratives": normalize_narratives(narratives_payload),
        "primary_asset_info": info_payload,
        "primary_asset_metrics": metrics_payload,
        "primary_asset_concept_search": concept_payload,
        "primary_asset_news": records_from_tool_payload(news_payload),
        "marketcap_technical_analysis": marketcap_technicals,
        "raw_tool_results": raw_results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect a live CMC MCP snapshot using all currently exposed CMC MCP tools.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--assets", default="BNB,BTC,ETH", help="Comma-separated asset symbols to resolve and quote through CMC MCP.")
    parser.add_argument("--primary", default="BNB", help="Primary asset symbol used for single-asset MCP tools.")
    parser.add_argument("--news-limit", type=int, default=5, help="Latest CMC news items to request for the primary asset.")
    parser.add_argument(
        "--concept-prompt",
        default="ecosystem utility, adoption catalysts, security risks, and trading strategy relevance",
        help="Prompt passed to CMC semantic crypto info search for the primary asset.",
    )
    parser.add_argument("--output", type=Path, help="Write the live CMC MCP snapshot JSON to this file instead of stdout.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    api_key = os.getenv("CMC_MCP_API_KEY") or os.getenv("CMC_API_KEY")
    if not api_key:
        raise SystemExit("CMC_MCP_API_KEY or CMC_API_KEY is required. This collector is live-only and has no offline fallback.")
    assets = [symbol.strip().upper() for symbol in args.assets.split(",") if symbol.strip()]
    if not assets:
        raise SystemExit("At least one asset symbol is required.")
    snapshot = collect_mcp_snapshot(api_key, assets, args.primary, args.news_limit, args.concept_prompt)
    rendered = json.dumps(snapshot, indent=2, sort_keys=False)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Live CMC MCP snapshot written to {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
