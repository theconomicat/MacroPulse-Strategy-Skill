#!/usr/bin/env python3
"""Generate a live CMC MCP-backed crypto strategy specification."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

from collect_cmc_data import collect_mcp_snapshot


TEMPLATE_ALIASES = {
    "fear-rebound-dca": "Fear Rebound DCA",
    "risk-off-rotation": "Risk-Off Rotation",
    "narrative-momentum": "Narrative Momentum",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"CMC snapshot file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"CMC snapshot must be a JSON object: {path}")
    return data


def dump_yaml(data: dict[str, Any]) -> str:
    if yaml is None:
        raise SystemExit("PyYAML is required for YAML output. Install dependencies with: pip install -r requirements.txt")
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


def parse_number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    multiplier = 1.0
    if text.endswith("%"):
        text = text[:-1]
    suffix_match = re.search(r"([KMBT])$", text, re.IGNORECASE)
    if suffix_match:
        suffix = suffix_match.group(1).upper()
        multiplier = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[suffix]
        text = text[:-1].strip()
    try:
        return float(text) * multiplier
    except ValueError:
        return default


def quote_for(snapshot: dict[str, Any], symbol: str) -> dict[str, Any]:
    return dict(snapshot.get("quotes", {}).get(symbol.upper(), {}))


def technicals_for(snapshot: dict[str, Any], symbol: str) -> dict[str, Any]:
    return dict(snapshot.get("technicals", {}).get(symbol.upper(), {}))


def global_fear(snapshot: dict[str, Any]) -> tuple[float, str]:
    current = snapshot.get("global_metrics", {}).get("sentiment", {}).get("fear_greed", {}).get("current", {})
    return parse_number(current.get("index"), 50.0), str(current.get("value", "unknown"))


def market_cap_7d_change(snapshot: dict[str, Any]) -> float:
    return parse_number(
        snapshot.get("global_metrics", {})
        .get("market_size", {})
        .get("total_crypto_market_cap_usd", {})
        .get("percent_change", {})
        .get("7d"),
        0.0,
    )


def btc_dominance_change(snapshot: dict[str, Any]) -> float:
    dominance = snapshot.get("global_metrics", {}).get("dominance", {}).get("btc", {})
    current = parse_number(dominance.get("current"), 0.0)
    last_week = parse_number(dominance.get("history", {}).get("last_week"), current)
    return current - last_week


def bnb_rsi(snapshot: dict[str, Any]) -> float:
    primary = snapshot.get("primary_asset", "BNB")
    return parse_number(technicals_for(snapshot, primary).get("rsi", {}).get("rsi14"), 50.0)


def bnb_macd_histogram(snapshot: dict[str, Any]) -> float:
    primary = snapshot.get("primary_asset", "BNB")
    return parse_number(technicals_for(snapshot, primary).get("macd", {}).get("histogram"), 0.0)


def derivatives_risk_score(snapshot: dict[str, Any]) -> float:
    derivatives = snapshot.get("global_derivatives", {})
    funding = abs(parse_number(derivatives.get("fundingRate", {}).get("current"), 0.0))
    oi_24h = parse_number(derivatives.get("totalOpenInterest", {}).get("percentage_change_24h"), 0.0)
    liquidation = parse_number(
        derivatives.get("btc_liquidations", {}).get("total", {}).get("usd_24h")
        or derivatives.get("btc_liquidations", {}).get("total_usd_24h"),
        0.0,
    )
    score = min(1.0, (funding * 30) + max(0.0, oi_24h) / 12 + min(liquidation / 1_000_000_000, 0.25))
    return round(score, 4)


def strongest_narrative(snapshot: dict[str, Any]) -> dict[str, Any]:
    narratives = [item for item in snapshot.get("trending_narratives", []) if isinstance(item, dict)]
    if not narratives:
        return {}
    return sorted(narratives, key=lambda item: int(parse_number(item.get("trendingRank"), 999999)))[0]


def classify_market_regime(snapshot: dict[str, Any]) -> dict[str, Any]:
    fear, fear_label = global_fear(snapshot)
    rsi = bnb_rsi(snapshot)
    market_cap_7d = market_cap_7d_change(snapshot)
    dominance_7d = btc_dominance_change(snapshot)
    deriv_risk = derivatives_risk_score(snapshot)
    narrative = strongest_narrative(snapshot)
    narrative_24h = parse_number(narrative.get("marketCapChangePercentage24h"), 0.0)
    macd_hist = bnb_macd_histogram(snapshot)

    if deriv_risk >= 0.65 or dominance_7d >= 1.0:
        template = "risk-off-rotation"
        label = "risk_off_mcp_derivatives_pressure"
        confidence = min(0.92, 0.58 + deriv_risk * 0.28 + max(0.0, dominance_7d) * 0.03)
    elif fear <= 30 and rsi <= 42 and market_cap_7d <= -5:
        template = "fear-rebound-dca"
        label = "extreme_fear_cmc_rebound_setup"
        confidence = min(0.93, 0.58 + (30 - fear) * 0.007 + (42 - rsi) * 0.006 + abs(min(market_cap_7d, 0)) * 0.006)
    elif narrative and narrative_24h > 0 and deriv_risk < 0.65 and macd_hist >= -15:
        template = "narrative-momentum"
        label = "cmc_narrative_momentum"
        confidence = min(0.88, 0.56 + min(narrative_24h, 20) * 0.01)
    else:
        template = "risk-off-rotation" if market_cap_7d < -10 else "fear-rebound-dca"
        label = "defensive_cmc_market_stress"
        confidence = 0.62

    rules = []
    if fear <= 30:
        rules.append("cmc_fear_greed_lte_30")
    if rsi <= 42:
        rules.append("primary_rsi14_lte_42")
    if market_cap_7d <= -5:
        rules.append("global_market_cap_7d_lte_minus_5")
    if dominance_7d >= 1:
        rules.append("btc_dominance_7d_rising")
    if deriv_risk >= 0.65:
        rules.append("derivatives_risk_elevated")
    if narrative:
        rules.append("cmc_trending_narrative_available")

    return {
        "label": label,
        "confidence": round(confidence, 3),
        "selected_template": template,
        "inputs": {
            "fear_greed_index": fear,
            "fear_greed_label": fear_label,
            "primary_rsi14": rsi,
            "primary_macd_histogram": macd_hist,
            "global_market_cap_7d_change_pct": market_cap_7d,
            "btc_dominance_7d_change_points": round(dominance_7d, 4),
            "derivatives_risk_score": deriv_risk,
            "top_narrative": narrative.get("categoryName"),
            "top_narrative_24h_change_pct": narrative_24h,
        },
        "rules_fired": rules,
    }


def build_evidence(snapshot: dict[str, Any], regime: dict[str, Any]) -> list[dict[str, Any]]:
    primary = snapshot.get("primary_asset", "BNB")
    return [
        {
            "source": "CoinMarketCap MCP tools inventory",
            "type": "mcp",
            "data": snapshot.get("mcp", {}),
            "interpretation": "The strategy is generated from live CMC MCP tools discovered through tools/list.",
        },
        {
            "source": "CMC MCP get_global_metrics_latest",
            "type": "global_market",
            "data": {
                "fear_greed": snapshot.get("global_metrics", {}).get("sentiment", {}).get("fear_greed", {}),
                "market_size": snapshot.get("global_metrics", {}).get("market_size", {}),
                "dominance": snapshot.get("global_metrics", {}).get("dominance", {}),
                "liquidity": snapshot.get("global_metrics", {}).get("liquidity", {}),
            },
            "interpretation": "Global market stress, liquidity, dominance, and fear/greed drive regime selection.",
        },
        {
            "source": "CMC MCP get_crypto_quotes_latest",
            "type": "quotes",
            "data": snapshot.get("quotes", {}),
            "interpretation": "Live quotes and multi-horizon performance are used for universe filters and replay.",
        },
        {
            "source": "CMC MCP get_crypto_technical_analysis",
            "type": "technicals",
            "data": snapshot.get("technicals", {}),
            "interpretation": "RSI, MACD, moving averages, pivots, and Fibonacci levels define entry and exit rules.",
        },
        {
            "source": "CMC MCP get_global_crypto_derivatives_metrics",
            "type": "derivatives",
            "data": snapshot.get("global_derivatives", {}),
            "interpretation": "Funding, open interest, and liquidation context act as risk-off guardrails.",
        },
        {
            "source": "CMC MCP trending_crypto_narratives",
            "type": "narratives",
            "data": snapshot.get("trending_narratives", [])[:5],
            "interpretation": "Trending narratives inform momentum templates and related asset selection.",
        },
        {
            "source": "CMC MCP get_upcoming_macro_events and get_crypto_latest_news",
            "type": "catalysts",
            "data": {
                "macro_events": snapshot.get("upcoming_macro_events", {}),
                "primary_asset_news": snapshot.get("primary_asset_news", [])[:5],
            },
            "interpretation": "CMC-provided macro events and latest asset news provide catalyst context.",
        },
        {
            "source": "CMC MCP on-chain, info, semantic search, and marketcap technical tools",
            "type": "context",
            "data": {
                "primary_asset": primary,
                "primary_asset_info": snapshot.get("primary_asset_info", {}),
                "primary_asset_metrics": snapshot.get("primary_asset_metrics", {}),
                "primary_asset_concept_search": snapshot.get("primary_asset_concept_search", {}),
                "marketcap_technical_analysis": snapshot.get("marketcap_technical_analysis", {}),
            },
            "interpretation": "All remaining CMC MCP context tools are attached for auditability and future agent reasoning.",
        },
        {
            "source": "MacroPulse deterministic regime classifier",
            "type": "classification",
            "data": copy.deepcopy(regime),
            "interpretation": "Template selection is rule-based and validated before final output.",
        },
    ]


def base_strategy(snapshot: dict[str, Any], regime: dict[str, Any], template_key: str) -> dict[str, Any]:
    primary = snapshot.get("primary_asset", "BNB")
    assets = list(snapshot.get("asset_ids", {}).keys()) or [primary]
    quote = quote_for(snapshot, primary)
    tech = technicals_for(snapshot, primary)
    return {
        "strategy": {
            "name": "",
            "version": "2.0.0",
            "template": TEMPLATE_ALIASES[template_key],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "objective": "Create a live CMC MCP-backed, backtestable crypto strategy specification for agent review.",
        },
        "asset_universe": {
            "primary": assets,
            "focus_asset": primary,
            "quote_asset": "USDC",
            "filters": {
                "require_live_cmc_mcp_snapshot": True,
                "min_market_cap_usd": 1_000_000_000,
                "min_24h_volume_usd": 50_000_000,
                "require_cmc_rank_lte": 100,
            },
        },
        "market_regime": regime,
        "evidence": build_evidence(snapshot, regime),
        "entry": {},
        "position_sizing": {
            "method": "template_defined",
            "sizing_basis": "percentage_of_simulated_equity",
            "max_position_pct": None,
        },
        "execution": {
            "mode": "specification_only",
            "trade_execution": "disabled",
            "quote_only": True,
            "reference_price_usd": quote.get("price"),
            "primary_pivot_point": tech.get("pivotPoint"),
        },
        "exit": {},
        "risk": {},
        "backtest": {
            "engine": "macropulse-strategy/scripts/backtest_strategy.py",
            "mode": "cmc_mcp_performance_replay",
            "requires_live_cmc_snapshot": True,
            "include_fees": True,
            "include_slippage": True,
            "metrics_required": [
                "total_return_pct",
                "max_drawdown_pct",
                "win_rate",
                "trade_count",
                "fees_paid_pct",
                "slippage_assumption_bps",
            ],
        },
        "disclaimers": [
            "This is not financial advice.",
            "This strategy specification is for research, simulation, and backtesting only.",
            "No trades, swaps, transfers, approvals, wallet signing, or private key operations are executed by this skill.",
            "Human review is required before any real-world use outside this repository.",
        ],
    }


def build_fear_rebound_strategy(snapshot: dict[str, Any], regime: dict[str, Any]) -> dict[str, Any]:
    spec = base_strategy(snapshot, regime, "fear-rebound-dca")
    spec["strategy"]["name"] = "live_cmc_fear_rebound_dca"
    spec["entry"] = {
        "all": [
            {"cmc_fear_greed_lte": 30},
            {"primary_rsi14_lte": 42},
            {"global_market_cap_7d_change_lte_pct": -5},
            {"primary_price_above_pivot_or_reclaim_required": True},
        ],
        "confirmation": [
            "Use CMC MCP technical analysis pivot point and RSI as the entry gate.",
            "Skip entries when CMC derivatives risk score is elevated.",
        ],
    }
    spec["position_sizing"].update({"method": "dca_equal_slices", "allocation_per_entry_pct": 4, "max_entries": 5, "max_position_pct": 20})
    spec["execution"].update({"type": "dca", "interval": "1d", "max_entries": 5, "allocation_per_entry_pct": 4, "max_position_pct": 20})
    spec["exit"] = {
        "any": [
            {"cmc_fear_greed_gte": 55},
            {"take_profit_pct": 12},
            {"stop_loss_pct": 5},
            {"primary_rsi14_gte": 68},
            {"macd_histogram_deteriorates": True},
        ],
        "time_stop_days": 14,
    }
    spec["risk"] = {
        "max_position_pct": 20,
        "stop_loss_pct": 5,
        "max_drawdown_pct": 8,
        "max_daily_loss_pct": 2,
        "fee_bps": 10,
        "slippage_bps": 8,
        "risk_score": "medium",
        "risk_notes": ["The strategy uses live CMC MCP fear/greed, RSI, market cap, and derivatives evidence."],
    }
    return spec


def build_risk_off_strategy(snapshot: dict[str, Any], regime: dict[str, Any]) -> dict[str, Any]:
    spec = base_strategy(snapshot, regime, "risk-off-rotation")
    spec["strategy"]["name"] = "live_cmc_risk_off_rotation"
    spec["asset_universe"]["defensive_assets"] = ["USDC"]
    spec["entry"] = {
        "all": [
            {"derivatives_risk_score_gte": 0.65},
            {"btc_dominance_7d_change_points_gte": 1.0},
            {"new_altcoin_entries_allowed": False},
        ],
        "rotation_targets": {"USDC": 60, "BTC": 25, "ETH": 10, "BNB": 5},
    }
    spec["position_sizing"].update({"method": "defensive_rotation_targets", "target_allocations_pct": {"USDC": 60, "BTC": 25, "ETH": 10, "BNB": 5}, "max_position_pct": 10})
    spec["execution"].update({"type": "rotation", "rebalance_interval": "1d", "max_entries": 3, "allocation_per_entry_pct": 3, "max_position_pct": 10})
    spec["exit"] = {
        "any": [
            {"derivatives_risk_score_lte": 0.35},
            {"cmc_fear_greed_gte": 45},
            {"stop_loss_pct": 4.5},
            {"max_holding_days": 10},
        ]
    }
    spec["risk"] = {
        "max_position_pct": 10,
        "stop_loss_pct": 4.5,
        "max_drawdown_pct": 5,
        "max_daily_loss_pct": 1.5,
        "fee_bps": 10,
        "slippage_bps": 6,
        "risk_score": "low_medium",
        "risk_notes": ["This template blocks new illiquid alt exposure during CMC MCP derivatives or dominance stress."],
    }
    return spec


def build_narrative_momentum_strategy(snapshot: dict[str, Any], regime: dict[str, Any]) -> dict[str, Any]:
    spec = base_strategy(snapshot, regime, "narrative-momentum")
    narrative = strongest_narrative(snapshot)
    top_coin_list = narrative.get("topCoinList", {}) if isinstance(narrative, dict) else {}
    related = [row.get("coinSymbol") for row in table_to_records(top_coin_list) if row.get("coinSymbol")]
    primary = []
    for asset in list(snapshot.get("asset_ids", {}).keys()) + related:
        if asset and asset not in primary:
            primary.append(asset)
    spec["strategy"]["name"] = "live_cmc_narrative_momentum"
    spec["asset_universe"]["primary"] = primary[:8] or spec["asset_universe"]["primary"]
    spec["asset_universe"]["narrative"] = narrative.get("categoryName")
    spec["entry"] = {
        "all": [
            {"cmc_trending_narrative_rank_lte": 5},
            {"narrative_market_cap_24h_change_gt_pct": 0},
            {"primary_macd_histogram_gte": -15},
            {"derivatives_risk_score_lte": 0.65},
        ],
        "confirmation": ["Require CMC MCP narrative ranking and quote volume confirmation before inclusion."],
    }
    spec["position_sizing"].update({"method": "narrative_momentum_slices", "allocation_per_entry_pct": 3, "max_entries": 4, "max_position_pct": 12})
    spec["execution"].update({"type": "momentum", "rebalance_interval": "1d", "max_entries": 4, "allocation_per_entry_pct": 3, "max_position_pct": 12})
    spec["exit"] = {
        "any": [
            {"narrative_rank_drops_below": 10},
            {"take_profit_pct": 15},
            {"stop_loss_pct": 6},
            {"primary_rsi14_gte": 72},
        ],
        "time_stop_days": 12,
    }
    spec["risk"] = {
        "max_position_pct": 12,
        "stop_loss_pct": 6,
        "max_drawdown_pct": 10,
        "max_daily_loss_pct": 2,
        "fee_bps": 12,
        "slippage_bps": 12,
        "risk_score": "medium_high",
        "risk_notes": ["Narrative assets require extra CMC MCP liquidity, quote, and risk review."],
    }
    return spec


def table_to_records(table: Any) -> list[dict[str, Any]]:
    if not isinstance(table, dict):
        return []
    headers = table.get("headers")
    rows = table.get("rows")
    if not isinstance(headers, list) or not isinstance(rows, list):
        return []
    return [{str(header): row[index] if index < len(row) else None for index, header in enumerate(headers)} for row in rows if isinstance(row, list)]


def generate_strategy(snapshot: dict[str, Any], template: str) -> dict[str, Any]:
    if snapshot.get("source_mode") != "live_cmc_mcp":
        raise SystemExit("Strategy generation now requires a live CMC MCP snapshot from collect_cmc_data.py.")
    regime = classify_market_regime(snapshot)
    if template != "auto":
        regime = copy.deepcopy(regime)
        regime["selected_template"] = template
        regime["template_selection_mode"] = "forced_by_cli"
    selected_template = regime["selected_template"]
    if selected_template == "fear-rebound-dca":
        spec = build_fear_rebound_strategy(snapshot, regime)
    elif selected_template == "risk-off-rotation":
        spec = build_risk_off_strategy(snapshot, regime)
    elif selected_template == "narrative-momentum":
        spec = build_narrative_momentum_strategy(snapshot, regime)
    else:
        raise SystemExit(f"Unsupported strategy template: {selected_template}")
    spec["generation_inputs"] = {
        "cmc_snapshot_time": snapshot.get("snapshot_time"),
        "cmc_source_mode": snapshot.get("source_mode"),
        "cmc_mcp_tools_used": snapshot.get("mcp", {}).get("tools_used", []),
        "primary_asset": snapshot.get("primary_asset"),
        "asset_ids": snapshot.get("asset_ids"),
    }
    return spec


def collect_live_snapshot_from_args(args: argparse.Namespace) -> dict[str, Any]:
    api_key = os.getenv("CMC_MCP_API_KEY") or os.getenv("CMC_API_KEY")
    if not api_key:
        raise SystemExit("CMC_MCP_API_KEY or CMC_API_KEY is required for --live.")
    assets = [symbol.strip().upper() for symbol in args.assets.split(",") if symbol.strip()]
    return collect_mcp_snapshot(api_key, assets, args.primary.upper(), args.news_limit, args.concept_prompt)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a strategy spec from a live CMC MCP snapshot.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--live", action="store_true", help="Collect a live CMC MCP snapshot before generating the strategy.")
    source.add_argument("--cmc-snapshot", type=Path, help="Path to a live CMC MCP snapshot JSON produced by collect_cmc_data.py.")
    parser.add_argument("--assets", default="BNB,BTC,ETH", help="Assets to collect when --live is used.")
    parser.add_argument("--primary", default="BNB", help="Primary asset symbol when --live is used.")
    parser.add_argument("--news-limit", type=int, default=5, help="CMC latest news item count when --live is used.")
    parser.add_argument("--concept-prompt", default="ecosystem utility, adoption catalysts, security risks, and trading strategy relevance", help="CMC semantic search prompt when --live is used.")
    parser.add_argument("--template", choices=["auto", "fear-rebound-dca", "risk-off-rotation", "narrative-momentum"], default="auto", help="Strategy template to force, or auto for CMC MCP regime-based selection.")
    parser.add_argument("--format", choices=["yaml", "json"], default="yaml", help="Output serialization format.")
    parser.add_argument("--output", type=Path, help="Write the generated strategy to this file instead of stdout.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    snapshot = collect_live_snapshot_from_args(args) if args.live else load_json(args.cmc_snapshot)
    spec = generate_strategy(snapshot, args.template)
    rendered = json.dumps(spec, indent=2, sort_keys=False) if args.format == "json" else dump_yaml(spec)
    if args.output:
        args.output.write_text(rendered if rendered.endswith("\n") else rendered + "\n", encoding="utf-8")
        print(f"Strategy spec written to {args.output}")
    else:
        print(rendered, end="" if rendered.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
