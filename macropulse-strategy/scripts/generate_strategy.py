#!/usr/bin/env python3
"""Generate a backtestable crypto strategy specification."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only when dependency is missing.
    yaml = None

from extract_news_signals import extract_signals_from_items, normalize_news_items


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_NEWS_INPUT = SKILL_DIR / "examples" / "sample-news-input.json"
DEFAULT_CMC_SNAPSHOT = SKILL_DIR / "examples" / "sample-cmc-snapshot.json"
DEFAULT_OHLCV = SKILL_DIR / "examples" / "sample-bnb-ohlcv.csv"

TEMPLATE_ALIASES = {
    "fear-rebound-dca": "Fear Rebound DCA",
    "risk-off-rotation": "Risk-Off Rotation",
    "narrative-momentum": "Narrative Momentum",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def dump_yaml(data: dict[str, Any]) -> str:
    if yaml is None:
        raise SystemExit("PyYAML is required for YAML output. Install dependencies with: pip install -r requirements.txt")
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


def quote_for(cmc: dict[str, Any], symbol: str) -> dict[str, Any]:
    return dict(cmc.get("quotes", {}).get(symbol, {}))


def fear_value(cmc: dict[str, Any]) -> float:
    value = cmc.get("fear_greed", {}).get("value", 50)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 50.0


def global_metric(cmc: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = cmc.get("global_metrics", {}).get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def quote_metric(cmc: dict[str, Any], symbol: str, key: str, default: float = 0.0) -> float:
    value = quote_for(cmc, symbol).get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def strongest_narrative(cmc: dict[str, Any]) -> dict[str, Any]:
    narratives = [item for item in cmc.get("narratives", []) if isinstance(item, dict)]
    if not narratives:
        return {}
    return max(narratives, key=lambda item: float(item.get("strength_score", 0.0)))


def classify_market_regime(cmc: dict[str, Any], news_signals: dict[str, Any]) -> dict[str, Any]:
    fear = fear_value(cmc)
    bnb_rsi = quote_metric(cmc, "BNB", "rsi_14", 50.0)
    btc_dominance_change = global_metric(cmc, "btc_dominance_7d_change_pct", 0.0)
    market_cap_change = global_metric(cmc, "total_market_cap_7d_change_pct", 0.0)
    macro_sentiment = float(news_signals.get("macro_sentiment", 0.0))
    risk_event_score = float(news_signals.get("risk_event_score", 0.0))
    narrative = strongest_narrative(cmc)
    narrative_strength = float(narrative.get("strength_score", 0.0) or 0.0)

    if risk_event_score >= 0.68 and btc_dominance_change >= 0.4:
        label = "risk_off_macro_pressure"
        template = "risk-off-rotation"
        confidence = min(0.92, 0.55 + risk_event_score * 0.35 + btc_dominance_change * 0.03)
    elif fear <= 30 and bnb_rsi <= 42 and macro_sentiment >= -0.45:
        label = "extreme_fear_rebound"
        template = "fear-rebound-dca"
        confidence = min(0.91, 0.52 + (30 - fear) * 0.008 + (42 - bnb_rsi) * 0.006 + max(0.0, macro_sentiment + 0.45) * 0.18)
    elif narrative_strength >= 0.76 and risk_event_score < 0.65:
        label = "narrative_momentum"
        template = "narrative-momentum"
        confidence = min(0.9, 0.50 + narrative_strength * 0.32 + max(0.0, macro_sentiment) * 0.12)
    elif market_cap_change < -4.0 or fear < 40:
        label = "defensive_recovery_watch"
        template = "fear-rebound-dca"
        confidence = 0.62
    else:
        label = "selective_momentum"
        template = "narrative-momentum"
        confidence = 0.60

    return {
        "label": label,
        "confidence": round(confidence, 3),
        "selected_template": template,
        "inputs": {
            "fear_greed_index": fear,
            "bnb_rsi_14": bnb_rsi,
            "btc_dominance_7d_change_pct": btc_dominance_change,
            "total_market_cap_7d_change_pct": market_cap_change,
            "macro_sentiment": macro_sentiment,
            "risk_event_score": risk_event_score,
            "strongest_narrative": narrative.get("tag"),
            "strongest_narrative_score": narrative_strength,
        },
        "rules_fired": build_rules_fired(fear, bnb_rsi, btc_dominance_change, macro_sentiment, risk_event_score, narrative_strength),
    }


def build_rules_fired(
    fear: float,
    bnb_rsi: float,
    btc_dominance_change: float,
    macro_sentiment: float,
    risk_event_score: float,
    narrative_strength: float,
) -> list[str]:
    rules: list[str] = []
    if fear <= 30:
        rules.append("fear_greed_lte_30")
    if bnb_rsi <= 42:
        rules.append("bnb_rsi_lte_42")
    if macro_sentiment >= -0.45:
        rules.append("news_sentiment_not_extreme_negative")
    if risk_event_score >= 0.68:
        rules.append("macro_risk_event_elevated")
    if btc_dominance_change >= 0.4:
        rules.append("btc_dominance_rising")
    if narrative_strength >= 0.76:
        rules.append("cmc_narrative_strength_gte_0_76")
    return rules


def build_evidence(cmc: dict[str, Any], news_signals: dict[str, Any], regime: dict[str, Any]) -> list[dict[str, Any]]:
    bnb = quote_for(cmc, "BNB")
    btc = quote_for(cmc, "BTC")
    eth = quote_for(cmc, "ETH")
    narrative = strongest_narrative(cmc)
    return [
        {
            "source": "CoinMarketCap Agent Hub routing plan",
            "type": "agent_hub",
            "data": cmc.get("agent_hub", {}),
            "interpretation": "Agent Hub/MCP/REST/x402 surfaces define how live data should be routed into this strategy workflow.",
        },
        {
            "source": "CoinMarketCap fear and greed",
            "type": "sentiment",
            "data": {
                "value": cmc.get("fear_greed", {}).get("value"),
                "classification": cmc.get("fear_greed", {}).get("value_classification"),
            },
            "interpretation": "Market sentiment is used as a regime input, not as a standalone trade signal.",
        },
        {
            "source": "CoinMarketCap global metrics",
            "type": "market_health",
            "data": {
                "total_market_cap_7d_change_pct": cmc.get("global_metrics", {}).get("total_market_cap_7d_change_pct"),
                "btc_dominance_pct": cmc.get("global_metrics", {}).get("btc_dominance_pct"),
                "btc_dominance_7d_change_pct": cmc.get("global_metrics", {}).get("btc_dominance_7d_change_pct"),
            },
            "interpretation": "Global market trend and BTC dominance affect risk appetite and template selection.",
        },
        {
            "source": "CoinMarketCap quotes and technical indicators",
            "type": "asset_technicals",
            "data": {
                "BNB": {
                    "price_usd": bnb.get("price_usd"),
                    "percent_change_7d": bnb.get("percent_change_7d"),
                    "rsi_14": bnb.get("rsi_14"),
                    "ema_trend": bnb.get("ema_trend"),
                },
                "BTC": {"price_usd": btc.get("price_usd"), "percent_change_7d": btc.get("percent_change_7d")},
                "ETH": {"price_usd": eth.get("price_usd"), "percent_change_7d": eth.get("percent_change_7d")},
            },
            "interpretation": "Large-cap crypto quotes and BNB technicals define entry filters and replay assumptions.",
        },
        {
            "source": "Macro news signal extractor",
            "type": "news",
            "data": {
                "macro_sentiment": news_signals.get("macro_sentiment"),
                "risk_event_score": news_signals.get("risk_event_score"),
                "dominant_topics": news_signals.get("dominant_topics", [])[:5],
                "asset_mentions": news_signals.get("asset_mentions", [])[:5],
                "narrative_tags": news_signals.get("narrative_tags", [])[:5],
            },
            "interpretation": news_signals.get("summary", "News signals were normalized for strategy generation."),
        },
        {
            "source": "CoinMarketCap narratives",
            "type": "narrative",
            "data": narrative,
            "interpretation": "Narrative strength is used only when liquidity and risk filters are present.",
        },
        {
            "source": "CoinMarketCap derivatives and on-chain risk",
            "type": "risk_context",
            "data": {
                "derivatives": cmc.get("derivatives", {}),
                "on_chain": cmc.get("on_chain", {}),
                "dex_security_liquidity": cmc.get("dex_security_liquidity", {}),
            },
            "interpretation": "Derivatives, on-chain, and DEX security context are used as risk gates and future MCP enrichment targets.",
        },
        {
            "source": "Rule-based regime classifier",
            "type": "classification",
            "data": copy.deepcopy(regime),
            "interpretation": "Template selection is deterministic and should be validated before final use.",
        },
    ]


def base_strategy(cmc: dict[str, Any], news_signals: dict[str, Any], regime: dict[str, Any], template_key: str) -> dict[str, Any]:
    bnb = quote_for(cmc, "BNB")
    return {
        "strategy": {
            "name": "",
            "version": "1.0.0",
            "template": TEMPLATE_ALIASES[template_key],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "objective": "Create a backtestable crypto strategy specification for research and agent review.",
        },
        "asset_universe": {
            "primary": ["BNB", "BTC", "ETH"],
            "quote_asset": "USDC",
            "filters": {
                "min_market_cap_usd": 1_000_000_000,
                "min_24h_volume_usd": 50_000_000,
                "require_cmc_rank_lte": 50,
                "exclude_assets_with_unresolved_security_events": True,
            },
        },
        "market_regime": regime,
        "evidence": build_evidence(cmc, news_signals, regime),
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
            "reference_price_usd": bnb.get("price_usd"),
        },
        "exit": {},
        "risk": {},
        "backtest": {
            "engine": "macropulse-strategy/scripts/backtest_strategy.py",
            "default_ohlcv": str(DEFAULT_OHLCV.relative_to(SKILL_DIR.parent)),
            "window_days": 45,
            "interval": "1d",
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
            "No trades, swaps, transfers, approvals, or wallet actions are executed by this skill.",
            "Human review is required before any real-world use outside this repository.",
        ],
    }


def build_fear_rebound_strategy(cmc: dict[str, Any], news_signals: dict[str, Any], regime: dict[str, Any]) -> dict[str, Any]:
    spec = base_strategy(cmc, news_signals, regime, "fear-rebound-dca")
    spec["strategy"]["name"] = "fear_rebound_bnb_dca"
    spec["entry"] = {
        "all": [
            {"cmc_fear_greed_lte": 30},
            {"bnb_rsi_14_lte": 40},
            {"bnb_7d_change_lte_pct": -4},
            {"news_macro_sentiment_gte": -0.35},
        ],
        "confirmation": [
            "Use DCA only after daily close is above the prior 3-day low.",
            "Skip new entries when a fresh exchange, bridge, or chain security event is unresolved.",
        ],
    }
    spec["execution"].update(
        {
            "type": "dca",
            "interval": "1d",
            "max_entries": 5,
            "allocation_per_entry_pct": 4,
            "max_position_pct": 20,
            "preferred_quote_asset": "USDC",
        }
    )
    spec["position_sizing"].update(
        {
            "method": "dca_equal_slices",
            "allocation_per_entry_pct": 4,
            "max_entries": 5,
            "max_position_pct": 20,
        }
    )
    spec["exit"] = {
        "any": [
            {"cmc_fear_greed_gte": 55},
            {"take_profit_pct": 12},
            {"stop_loss_pct": 5},
            {"bnb_rsi_14_gte": 68},
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
        "risk_notes": [
            "Fear rebound strategies can fail if macro stress accelerates.",
            "DCA entries stop immediately after the stop-loss or drawdown limit is hit.",
        ],
    }
    return spec


def build_risk_off_strategy(cmc: dict[str, Any], news_signals: dict[str, Any], regime: dict[str, Any]) -> dict[str, Any]:
    spec = base_strategy(cmc, news_signals, regime, "risk-off-rotation")
    spec["strategy"]["name"] = "risk_off_large_cap_rotation"
    spec["asset_universe"]["primary"] = ["BTC", "ETH", "BNB", "USDC"]
    spec["asset_universe"]["defensive_assets"] = ["USDC"]
    spec["entry"] = {
        "all": [
            {"news_risk_event_score_gte": 0.45},
            {"btc_dominance_7d_change_gte_pct": 0.3},
            {"new_altcoin_entries_allowed": False},
        ],
        "rotation_targets": {"USDC": 60, "BTC": 25, "ETH": 10, "BNB": 5},
    }
    spec["execution"].update(
        {
            "type": "rotation",
            "rebalance_interval": "1d",
            "max_entries": 3,
            "allocation_per_entry_pct": 3,
            "max_position_pct": 10,
            "preferred_quote_asset": "USDC",
        }
    )
    spec["position_sizing"].update(
        {
            "method": "defensive_rotation_targets",
            "target_allocations_pct": {"USDC": 60, "BTC": 25, "ETH": 10, "BNB": 5},
            "max_position_pct": 10,
        }
    )
    spec["exit"] = {
        "any": [
            {"news_risk_event_score_lte": 0.40},
            {"cmc_fear_greed_gte": 45},
            {"stop_loss_pct": 4.5},
            {"max_holding_days": 10},
        ],
        "risk_on_reentry_requires": ["btc_dominance_stabilizes", "news_sentiment_above_-0.15"],
    }
    spec["risk"] = {
        "max_position_pct": 10,
        "stop_loss_pct": 4.5,
        "max_drawdown_pct": 5,
        "max_daily_loss_pct": 1.5,
        "fee_bps": 10,
        "slippage_bps": 6,
        "risk_score": "low_medium",
        "risk_notes": [
            "This template prioritizes capital preservation over return seeking.",
            "It blocks new illiquid altcoin exposure while macro event risk is elevated.",
        ],
    }
    return spec


def build_narrative_momentum_strategy(cmc: dict[str, Any], news_signals: dict[str, Any], regime: dict[str, Any]) -> dict[str, Any]:
    spec = base_strategy(cmc, news_signals, regime, "narrative-momentum")
    narrative = strongest_narrative(cmc)
    related_assets = [asset for asset in narrative.get("related_assets", []) if isinstance(asset, str)] or ["BNB", "ETH", "BTC"]
    primary = []
    for asset in ["BNB", *related_assets, "BTC", "ETH"]:
        if asset not in primary:
            primary.append(asset)
    spec["strategy"]["name"] = "narrative_momentum_cmc_news"
    spec["asset_universe"]["primary"] = primary[:6]
    spec["asset_universe"]["narrative"] = narrative.get("tag", "unknown")
    spec["entry"] = {
        "all": [
            {"cmc_narrative_strength_gte": 0.75},
            {"news_narrative_mentions_gte": 2},
            {"asset_24h_volume_change_gte_pct": 12},
            {"macro_risk_event_score_lte": 0.65},
        ],
        "confirmation": [
            "Require daily close above 5-day moving average.",
            "Require liquidity and security filters before including non-large-cap assets.",
        ],
    }
    spec["execution"].update(
        {
            "type": "momentum",
            "rebalance_interval": "1d",
            "max_entries": 4,
            "allocation_per_entry_pct": 3,
            "max_position_pct": 12,
            "preferred_quote_asset": "USDC",
        }
    )
    spec["position_sizing"].update(
        {
            "method": "narrative_momentum_slices",
            "allocation_per_entry_pct": 3,
            "max_entries": 4,
            "max_position_pct": 12,
        }
    )
    spec["exit"] = {
        "any": [
            {"cmc_narrative_strength_lte": 0.55},
            {"take_profit_pct": 15},
            {"stop_loss_pct": 6},
            {"volume_change_lte_pct": -10},
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
        "risk_notes": [
            "Narrative momentum can reverse quickly when attention shifts.",
            "Non-large-cap assets require extra liquidity and security review.",
        ],
    }
    return spec


def generate_strategy(news_path: Path, cmc_path: Path, template: str) -> dict[str, Any]:
    news_payload = load_json(news_path)
    cmc_payload = load_json(cmc_path)
    news_items = normalize_news_items(news_payload)
    news_signals = extract_signals_from_items(news_items)
    regime = classify_market_regime(cmc_payload, news_signals)
    selected_template = regime["selected_template"] if template == "auto" else template
    if template != "auto":
        regime = copy.deepcopy(regime)
        regime["selected_template"] = template
        regime["template_selection_mode"] = "forced_by_cli"
        if template == "risk-off-rotation":
            regime["label"] = "risk_off_rotation_overlay"
            regime["rules_fired"] = sorted(set(regime.get("rules_fired", []) + ["template_forced_risk_off_rotation"]))
        elif template == "narrative-momentum":
            regime["label"] = "narrative_momentum_overlay"
            regime["rules_fired"] = sorted(set(regime.get("rules_fired", []) + ["template_forced_narrative_momentum"]))
        elif template == "fear-rebound-dca":
            regime["rules_fired"] = sorted(set(regime.get("rules_fired", []) + ["template_forced_fear_rebound_dca"]))

    selected_template = regime["selected_template"]
    if selected_template == "fear-rebound-dca":
        spec = build_fear_rebound_strategy(cmc_payload, news_signals, regime)
    elif selected_template == "risk-off-rotation":
        spec = build_risk_off_strategy(cmc_payload, news_signals, regime)
    elif selected_template == "narrative-momentum":
        spec = build_narrative_momentum_strategy(cmc_payload, news_signals, regime)
    else:
        raise SystemExit(f"Unsupported strategy template: {selected_template}")

    spec["market_regime"]["selected_template"] = selected_template
    spec["generation_inputs"] = {
        "news_input": display_path(news_path),
        "cmc_snapshot": display_path(cmc_path),
        "demo_mode_compatible": True,
        "news_item_count": len(news_items),
        "cmc_source_mode": cmc_payload.get("source_mode", "unknown"),
    }
    return spec


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(SKILL_DIR.parent))
    except ValueError:
        return str(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a YAML or JSON crypto strategy spec from news and CoinMarketCap sample/live snapshots.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--demo", action="store_true", help="Use bundled sample inputs. This mode does not require API keys.")
    parser.add_argument("--input", type=Path, default=DEFAULT_NEWS_INPUT, help="Path to normalized news input JSON.")
    parser.add_argument("--cmc-snapshot", type=Path, default=DEFAULT_CMC_SNAPSHOT, help="Path to CoinMarketCap snapshot JSON.")
    parser.add_argument(
        "--template",
        choices=["auto", "fear-rebound-dca", "risk-off-rotation", "narrative-momentum"],
        default="auto",
        help="Strategy template to force, or auto for deterministic regime-based selection.",
    )
    parser.add_argument("--format", choices=["yaml", "json"], default="yaml", help="Output serialization format.")
    parser.add_argument("--output", type=Path, help="Write the generated strategy to this file instead of stdout.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    news_path = DEFAULT_NEWS_INPUT if args.demo else args.input
    cmc_path = DEFAULT_CMC_SNAPSHOT if args.demo else args.cmc_snapshot
    spec = generate_strategy(news_path, cmc_path, args.template)

    if args.format == "json":
        rendered = json.dumps(spec, indent=2, sort_keys=False)
    else:
        rendered = dump_yaml(spec)

    if args.output:
        args.output.write_text(rendered if rendered.endswith("\n") else rendered + "\n", encoding="utf-8")
        print(f"Strategy spec written to {args.output}")
    else:
        print(rendered, end="" if rendered.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
