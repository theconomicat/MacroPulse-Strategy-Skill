#!/usr/bin/env python3
"""Build a BNB Agent SDK service manifest for strategy deliverables.

This script does not register anything on-chain. It emits the metadata an
operator can review before using BNBAgent SDK ERC-8004 identity registration or
ERC-8183 deliverable workflows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def load_strategy(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
    else:
        if yaml is None:
            raise SystemExit("PyYAML is required to read YAML strategies. Install dependencies with: pip install -r requirements.txt")
        data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise SystemExit(f"Strategy file must contain a top-level object: {path}")
    return data, raw


def build_manifest(strategy: dict[str, Any], raw_strategy: str, repo_url: str) -> dict[str, Any]:
    strategy_hash = hashlib.sha256(raw_strategy.encode("utf-8")).hexdigest()
    name = strategy.get("strategy", {}).get("name", "macropulse_strategy")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "manifest_only_no_onchain_registration",
        "bnb_agent_sdk": {
            "uses": [
                "ERC-8004 Agent Identity profile metadata",
                "ERC-8183 strategy deliverable packaging",
            ],
            "not_performed_by_this_script": [
                "private key loading",
                "wallet signing",
                "on-chain registration",
                "escrow funding",
                "payment settlement",
            ],
        },
        "erc8004_profile": {
            "name": "MacroPulse Strategy Skill",
            "description": "Produces validated, backtestable crypto strategy specs from CMC Agent Hub data, macro news, and risk rules.",
            "service_url": repo_url,
            "protocols": ["agent-skill", "strategy-spec", "backtest-report"],
            "supported_outputs": ["YAML strategy spec", "JSON validation report", "JSON replay metrics", "TWAK quote-only plan"],
            "metadata": {
                "track": "BNB Hack Track 2 Strategy Skills",
                "primary_assets": strategy.get("asset_universe", {}).get("primary", []),
                "no_trade_execution": True,
            },
        },
        "erc8183_deliverable": {
            "job_type": "strategy_spec_generation",
            "strategy_name": name,
            "deliverable_hash_sha256": strategy_hash,
            "expected_artifacts": [
                "strategy.yaml",
                "validation.txt",
                "backtest.json",
                "cmc-agent-hub-plan.json",
                "twak-quote-plan.txt",
            ],
            "acceptance_criteria": [
                "strategy validates successfully",
                "entry, exit, risk, and position_sizing are non-empty",
                "risk.max_position_pct, risk.stop_loss_pct, and risk.max_drawdown_pct are present",
                "evidence includes CMC and news signals",
                "no trade execution code is included",
            ],
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a BNB Agent SDK ERC-8004/ERC-8183 manifest for MacroPulse deliverables.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--strategy", type=Path, required=True, help="Path to a YAML or JSON strategy spec.")
    parser.add_argument(
        "--repo-url",
        default="https://github.com/theconomicat/MacroPulse-Strategy-Skill",
        help="Public repository or service URL for the agent profile.",
    )
    parser.add_argument("--output", type=Path, help="Write manifest JSON to this file instead of stdout.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    strategy, raw_strategy = load_strategy(args.strategy)
    manifest = build_manifest(strategy, raw_strategy, args.repo_url)
    rendered = json.dumps(manifest, indent=2, sort_keys=False)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"BNB Agent SDK manifest written to {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
