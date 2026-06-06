#!/usr/bin/env python3
"""Convert a strategy spec into a Trust Wallet Agent Kit quote-only plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only when dependency is missing.
    yaml = None


def load_strategy(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SystemExit(f"Strategy file not found: {path}") from exc
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
    else:
        if yaml is None:
            raise SystemExit("PyYAML is required to read YAML strategies. Install dependencies with: pip install -r requirements.txt")
        data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise SystemExit(f"Strategy file must contain a top-level object: {path}")
    return data


def first_trade_asset(strategy: dict[str, Any]) -> str:
    universe = strategy.get("asset_universe", {})
    primary = universe.get("primary", []) if isinstance(universe, dict) else []
    for asset in primary:
        symbol = str(asset).upper()
        if symbol not in {"USDC", "USDT", "DAI"}:
            return symbol
    return "BNB"


def reference_price(strategy: dict[str, Any]) -> float | None:
    execution = strategy.get("execution", {})
    if isinstance(execution, dict):
        value = execution.get("reference_price_usd")
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            pass
    for evidence in strategy.get("evidence", []):
        if not isinstance(evidence, dict):
            continue
        data = evidence.get("data")
        if isinstance(data, dict):
            bnb = data.get("BNB")
            if isinstance(bnb, dict) and bnb.get("price_usd") is not None:
                try:
                    return float(bnb["price_usd"])
                except (TypeError, ValueError):
                    return None
    return None


def exit_pct(strategy: dict[str, Any], key: str) -> float | None:
    exit_section = strategy.get("exit", {})
    if not isinstance(exit_section, dict):
        return None
    for group in ["any", "all"]:
        values = exit_section.get(group, [])
        if not isinstance(values, list):
            continue
        for item in values:
            if isinstance(item, dict) and key in item:
                try:
                    return float(item[key])
                except (TypeError, ValueError):
                    return None
    return None


def build_plan(strategy: dict[str, Any], notional_usdc: float) -> str:
    name = strategy.get("strategy", {}).get("name", "unnamed_strategy")
    template = strategy.get("strategy", {}).get("template", "unknown")
    asset = first_trade_asset(strategy)
    price = reference_price(strategy)
    take_profit = exit_pct(strategy, "take_profit_pct")
    stop_loss = exit_pct(strategy, "stop_loss_pct") or strategy.get("risk", {}).get("stop_loss_pct")

    lines = [
        f"Trust Wallet Agent Kit quote-only plan for {name}",
        f"Template: {template}",
        "",
        "Safety model:",
        "- This script does not execute swaps, transfers, approvals, or wallet actions.",
        "- Every command below is quote-only or alert-only.",
        "- A human must review the strategy, quote, route, fees, slippage, wallet state, and risk limits before any separate execution workflow.",
        "- User approval must happen outside this skill and after validation/backtest review.",
        "",
        "Suggested TWAK commands:",
        f"twak price {asset}",
        f"twak swap {notional_usdc:g} USDC {asset} --quote-only",
    ]

    if price and take_profit:
        lines.append(f"twak alert create --token {asset} --above {price * (1 + take_profit / 100):.4f}")
    else:
        lines.append(f"twak alert create --token {asset} --above <take_profit_price>")

    try:
        stop_loss_float = float(stop_loss) if stop_loss is not None else None
    except (TypeError, ValueError):
        stop_loss_float = None

    if price and stop_loss_float:
        lines.append(f"twak alert create --token {asset} --below {price * (1 - stop_loss_float / 100):.4f}")
    else:
        lines.append(f"twak alert create --token {asset} --below <stop_loss_price>")

    lines.extend(
        [
            "",
            "Approval checklist:",
            "- Confirm the strategy validator passed.",
            "- Confirm replay metrics are acceptable for the intended research window.",
            "- Confirm max_position_pct, stop_loss_pct, and max_drawdown_pct are understood.",
            "- Confirm the quote-only route does not imply permission to execute.",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print a Trust Wallet Agent Kit quote-only plan from a MacroPulse strategy spec.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--strategy", type=Path, required=True, help="Path to a YAML or JSON strategy spec.")
    parser.add_argument("--notional-usdc", type=float, default=100.0, help="Illustrative quote notional for TWAK quote-only commands.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    strategy = load_strategy(args.strategy)
    print(build_plan(strategy, args.notional_usdc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
