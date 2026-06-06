#!/usr/bin/env python3
"""Replay a strategy against live CMC MCP quote performance horizons."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


HORIZONS = [
    ("1h", "percent_change_1h"),
    ("24h", "percent_change_24h"),
    ("7d", "percent_change_7d"),
    ("30d", "percent_change_30d"),
    ("60d", "percent_change_60d"),
    ("90d", "percent_change_90d"),
]


def load_object(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
    else:
        if yaml is None:
            raise SystemExit("PyYAML is required to read YAML. Install dependencies with: pip install -r requirements.txt")
        data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise SystemExit(f"File must contain a top-level object: {path}")
    return data


def parse_number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text.endswith("%"):
        text = text[:-1]
    try:
        return float(text)
    except ValueError:
        return default


def focus_symbol(strategy: dict[str, Any], snapshot: dict[str, Any]) -> str:
    universe = strategy.get("asset_universe", {})
    focus = universe.get("focus_asset") if isinstance(universe, dict) else None
    if focus:
        return str(focus).upper()
    return str(snapshot.get("primary_asset", "BNB")).upper()


def run_cmc_performance_replay(strategy: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    if snapshot.get("source_mode") != "live_cmc_mcp":
        raise SystemExit("Backtest now requires a live CMC MCP snapshot from collect_cmc_data.py.")
    symbol = focus_symbol(strategy, snapshot)
    quote = snapshot.get("quotes", {}).get(symbol)
    if not isinstance(quote, dict):
        raise SystemExit(f"Snapshot does not contain quote data for focus asset: {symbol}")

    risk = strategy.get("risk", {})
    position_pct = parse_number(risk.get("max_position_pct"), 10.0)
    fee_bps = parse_number(risk.get("fee_bps"), 10.0)
    slippage_bps = parse_number(risk.get("slippage_bps"), 8.0)
    cost_pct = (fee_bps * 2 + slippage_bps * 2) / 100

    horizon_results: list[dict[str, Any]] = []
    wins = 0
    losses = 0
    worst_return = 0.0
    best_weighted = None
    for horizon, field in HORIZONS:
        raw_return = parse_number(quote.get(field), 0.0)
        weighted_return = raw_return * position_pct / 100 - cost_pct
        if weighted_return > 0:
            wins += 1
        else:
            losses += 1
        worst_return = min(worst_return, weighted_return)
        if best_weighted is None or weighted_return > best_weighted:
            best_weighted = weighted_return
        horizon_results.append(
            {
                "horizon": horizon,
                "cmc_field": field,
                "asset_return_pct": round(raw_return, 4),
                "position_weight_pct": position_pct,
                "net_strategy_return_pct": round(weighted_return, 4),
            }
        )

    total_return_pct = best_weighted if best_weighted is not None else 0.0
    max_drawdown_pct = abs(worst_return)
    trade_count = len(horizon_results)
    win_rate = wins / trade_count if trade_count else 0.0
    fees_paid_pct = fee_bps * 2 / 100

    return {
        "strategy_name": strategy.get("strategy", {}).get("name", "unknown"),
        "mode": "cmc_mcp_performance_replay",
        "snapshot_time": snapshot.get("snapshot_time"),
        "focus_asset": symbol,
        "total_return_pct": round(total_return_pct, 4),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "win_rate": round(win_rate, 4),
        "trade_count": trade_count,
        "fees_paid_pct": round(fees_paid_pct, 4),
        "slippage_assumption_bps": slippage_bps,
        "fee_assumption_bps": fee_bps,
        "horizon_results": horizon_results,
        "notes": [
            "This replay uses live CMC MCP quote performance horizons.",
            "It is a lightweight validation replay for strategy specs, not a production quant engine.",
            "No live orders, wallet actions, signing, or transaction execution are performed.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay a strategy against live CMC MCP quote performance horizons.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--strategy", type=Path, required=True, help="Path to a YAML or JSON strategy spec.")
    parser.add_argument("--cmc-snapshot", type=Path, required=True, help="Path to a live CMC MCP snapshot JSON.")
    parser.add_argument("--output", type=Path, help="Write replay metrics JSON to this file instead of stdout.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    strategy = load_object(args.strategy)
    snapshot = load_object(args.cmc_snapshot)
    result = run_cmc_performance_replay(strategy, snapshot)
    rendered = json.dumps(result, indent=2, sort_keys=False)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Backtest metrics written to {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
