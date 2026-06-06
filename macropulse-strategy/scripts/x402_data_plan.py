#!/usr/bin/env python3
"""Create an x402 pay-per-request data access plan without making payments."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def load_strategy(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
    else:
        if yaml is None:
            raise SystemExit("PyYAML is required to read YAML strategies. Install dependencies with: pip install -r requirements.txt")
        data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise SystemExit(f"Strategy file must contain a top-level object: {path}")
    return data


def build_x402_plan(strategy: dict[str, Any], max_budget_usdc: float) -> dict[str, Any]:
    primary_assets = strategy.get("asset_universe", {}).get("primary", ["BNB", "BTC", "ETH"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy_name": strategy.get("strategy", {}).get("name", "unknown"),
        "mode": "plan_only_no_payment",
        "x402_context": {
            "purpose": "Use CMC x402 pay-per-request data access when an agent has USDC on Base and no CMC API key.",
            "settlement_asset": "USDC",
            "chain": "Base",
            "chain_id": 8453,
            "max_demo_budget_usdc": max_budget_usdc,
        },
        "candidate_requests": [
            {
                "name": "latest_quotes",
                "reason": "Refresh large-cap anchor prices before strategy generation.",
                "assets": primary_assets[:4],
                "max_price_usdc": 0.01,
            },
            {
                "name": "fear_and_greed",
                "reason": "Refresh market sentiment regime input.",
                "max_price_usdc": 0.01,
            },
            {
                "name": "technical_analysis",
                "reason": "Refresh RSI, MACD, EMA, and ATR pre-computed indicators.",
                "assets": primary_assets[:4],
                "max_price_usdc": 0.02,
            },
            {
                "name": "trending_narratives",
                "reason": "Refresh narrative momentum and related assets.",
                "max_price_usdc": 0.02,
            },
            {
                "name": "dex_security_liquidity",
                "reason": "Screen BNB Chain narrative assets before inclusion.",
                "assets": [asset for asset in primary_assets if asset not in {"BTC", "ETH", "BNB"}],
                "max_price_usdc": 0.02,
            },
        ],
        "guardrails": [
            "This script does not connect a wallet.",
            "This script does not sign x402 payments.",
            "A user or agent runtime must enforce the max budget before any paid request.",
            "Paid data must still pass strategy validation and risk checks.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print a no-payment x402 data access plan for a MacroPulse strategy.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--strategy", type=Path, required=True, help="Path to a YAML or JSON strategy spec.")
    parser.add_argument("--max-budget-usdc", type=float, default=0.08, help="Illustrative maximum x402 data budget.")
    parser.add_argument("--output", type=Path, help="Write JSON plan to this file instead of stdout.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    strategy = load_strategy(args.strategy)
    plan = build_x402_plan(strategy, args.max_budget_usdc)
    rendered = json.dumps(plan, indent=2, sort_keys=False)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"x402 data plan written to {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
