#!/usr/bin/env python3
"""Collect CoinMarketCap market data with safe sample fallback."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_SAMPLE = SKILL_DIR / "examples" / "sample-cmc-snapshot.json"
CMC_BASE_URL = "https://pro-api.coinmarketcap.com"
CMC_MCP_URL = "https://mcp.coinmarketcap.com/mcp"


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Sample snapshot not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid sample snapshot JSON in {path}: {exc}") from exc


def cmc_get(path: str, api_key: str, params: dict[str, str]) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    url = f"{CMC_BASE_URL}{path}"
    if query:
        url = f"{url}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "X-CMC_PRO_API_KEY": api_key,
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_quote_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    data = payload.get("data", {})
    if isinstance(data, list):
        iterable_data: list[tuple[str, Any]] = [(str(item.get("symbol", "")), item) for item in data if isinstance(item, dict)]
    elif isinstance(data, dict):
        iterable_data = list(data.items())
    else:
        return result

    for symbol_or_id, quote_data in iterable_data:
        if isinstance(quote_data, list):
            candidates = quote_data
        else:
            candidates = [quote_data]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            symbol = str(candidate.get("symbol", symbol_or_id)).upper()
            usd = candidate.get("quote", {}).get("USD", {})
            if usd.get("price") is None and symbol in result:
                continue
            existing = result.get(symbol)
            if existing:
                existing_rank = existing.get("cmc_rank")
                new_rank = candidate.get("cmc_rank")
                if existing_rank is not None and new_rank is not None and float(new_rank) > float(existing_rank):
                    continue
            result[symbol] = {
                "price_usd": usd.get("price"),
                "percent_change_24h": usd.get("percent_change_24h"),
                "percent_change_7d": usd.get("percent_change_7d"),
                "volume_24h": usd.get("volume_24h"),
                "volume_change_24h": usd.get("volume_change_24h"),
                "market_cap_usd": usd.get("market_cap"),
                "cmc_rank": candidate.get("cmc_rank"),
                "last_updated": usd.get("last_updated") or candidate.get("last_updated"),
            }
    return result


def normalize_global_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", {})
    quote = data.get("quote", {}).get("USD", {}) if isinstance(data, dict) else {}
    return {
        "total_market_cap_usd": quote.get("total_market_cap"),
        "total_volume_24h_usd": quote.get("total_volume_24h"),
        "total_market_cap_24h_change_pct": quote.get("total_market_cap_yesterday_percentage_change"),
        "btc_dominance_pct": data.get("btc_dominance") if isinstance(data, dict) else None,
        "eth_dominance_pct": data.get("eth_dominance") if isinstance(data, dict) else None,
        "active_cryptocurrencies": data.get("active_cryptocurrencies") if isinstance(data, dict) else None,
        "last_updated": data.get("last_updated") if isinstance(data, dict) else None,
    }


def normalize_fear_greed(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", {})
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        return {}
    return {
        "value": data.get("value"),
        "value_classification": data.get("value_classification") or data.get("classification"),
        "timestamp": data.get("timestamp") or data.get("update_time"),
    }


def load_sample_with_note(sample_path: Path, note: str) -> dict[str, Any]:
    sample = load_json(sample_path)
    sample["collector_notes"] = [note]
    sample["source_mode"] = "sample"
    return sample


def collect_live_snapshot(api_key: str, assets: list[str], include: set[str]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    snapshot: dict[str, Any] = {
        "snapshot_time": datetime.now(timezone.utc).isoformat(),
        "source_mode": "live",
        "fear_greed": {},
        "global_metrics": {},
        "quotes": {},
        "narratives": [],
        "technical_indicators": {},
        "collector_notes": [],
        "agent_hub": {
            "mcp_url": CMC_MCP_URL,
            "data_surfaces": ["REST"],
            "precomputed_signal_targets": ["RSI", "MACD", "EMA", "ATR", "Fear & Greed"],
        },
    }

    if "fear-greed" in include or "fear_greed" in include:
        try:
            snapshot["fear_greed"] = normalize_fear_greed(cmc_get("/v3/fear-and-greed/latest", api_key, {}))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            errors.append(f"Fear and Greed request failed: {exc}")

    if "global" in include:
        try:
            snapshot["global_metrics"] = normalize_global_metrics(cmc_get("/v1/global-metrics/quotes/latest", api_key, {}))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            errors.append(f"Global metrics request failed: {exc}")

    if "quotes" in include:
        try:
            symbols = ",".join(assets)
            payload = cmc_get("/v2/cryptocurrency/quotes/latest", api_key, {"symbol": symbols, "convert": "USD"})
            snapshot["quotes"] = normalize_quote_payload(payload)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            errors.append(f"Quotes request failed: {exc}")

    if "technicals" in include:
        snapshot["collector_notes"].append(
            "Live REST quotes were collected. For richer pre-computed RSI, MACD, EMA, ATR, use CoinMarketCap Agent Hub/MCP technical analysis tools."
        )
    if "narratives" in include:
        snapshot["collector_notes"].append(
            "Trending narratives are represented in the sample snapshot. For live narrative pipelines, use CoinMarketCap Agent Hub/MCP or Skills Marketplace routing."
        )
    if "mcp-plan" in include:
        snapshot["agent_hub"]["data_surfaces"].append("MCP")
        snapshot["collector_notes"].append(
            f"MCP endpoint configured for Agent Hub workflows: {CMC_MCP_URL}. Use CMC_MCP_API_KEY with scripts/cmc_agent_hub_plan.py --check-live."
        )

    if errors:
        snapshot["source_mode"] = "live_partial" if any(snapshot.get(key) for key in ("fear_greed", "global_metrics", "quotes")) else "live_failed"
    return snapshot, errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect CoinMarketCap fear/greed, global metrics, and quote data with demo fallback.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--assets", default="BNB,BTC,ETH", help="Comma-separated asset symbols for quote collection.")
    parser.add_argument(
        "--include",
        default="fear-greed,global,quotes,technicals,narratives",
        help="Comma-separated data groups to include.",
    )
    parser.add_argument("--output", type=Path, help="Write JSON snapshot to this file instead of stdout.")
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE, help="Sample snapshot used for demo or fallback mode.")
    parser.add_argument("--demo", action="store_true", help="Force sample mode even when CMC_API_KEY is set.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    assets = [asset.strip().upper() for asset in args.assets.split(",") if asset.strip()]
    include = {item.strip().lower() for item in args.include.split(",") if item.strip()}
    api_key = os.getenv("CMC_API_KEY")

    if args.demo:
        payload = load_sample_with_note(args.sample, "Demo mode requested; using sample CoinMarketCap snapshot.")
    elif not api_key:
        payload = load_sample_with_note(
            args.sample,
            "CMC_API_KEY is not set; using sample snapshot. Set CMC_API_KEY to attempt live CoinMarketCap collection.",
        )
    else:
        live_payload, errors = collect_live_snapshot(api_key, assets, include)
        if live_payload.get("source_mode") == "live_failed":
            payload = load_sample_with_note(
                args.sample,
                "All live CoinMarketCap requests failed; using sample snapshot. Errors: " + " | ".join(errors),
            )
        else:
            live_payload["collector_errors"] = errors
            payload = live_payload

    output = json.dumps(payload, indent=2, sort_keys=False)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
        print(f"CoinMarketCap snapshot written to {args.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
