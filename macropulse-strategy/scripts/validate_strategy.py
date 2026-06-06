#!/usr/bin/env python3
"""Validate a MacroPulse strategy YAML/JSON spec."""

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


REQUIRED_TOP_LEVEL = [
    "strategy",
    "asset_universe",
    "market_regime",
    "evidence",
    "entry",
    "position_sizing",
    "execution",
    "exit",
    "risk",
    "backtest",
    "disclaimers",
]
REQUIRED_RISK_FIELDS = ["max_position_pct", "stop_loss_pct", "max_drawdown_pct"]


def load_strategy(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SystemExit(f"Strategy file not found: {path}") from exc

    if path.suffix.lower() == ".json":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON strategy file {path}: {exc}") from exc
    else:
        if yaml is None:
            raise SystemExit("PyYAML is required to validate YAML. Install dependencies with: pip install -r requirements.txt")
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise SystemExit(f"Invalid YAML strategy file {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit(f"Strategy file must contain a top-level object: {path}")
    return data


def is_non_empty_mapping(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)


def validate_strategy(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for field in REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append(f"Missing required top-level field: {field}")

    strategy = data.get("strategy")
    if not isinstance(strategy, dict):
        errors.append("Field 'strategy' must be an object.")
    else:
        if not strategy.get("name"):
            errors.append("Missing required field: strategy.name")
        if not strategy.get("version"):
            errors.append("Missing required field: strategy.version")

    for section in ["entry", "exit", "risk"]:
        if not is_non_empty_mapping(data.get(section)):
            errors.append(f"Field '{section}' must be a non-empty object.")

    risk = data.get("risk", {})
    if isinstance(risk, dict):
        for field in REQUIRED_RISK_FIELDS:
            if field not in risk:
                errors.append(f"Missing required risk field: risk.{field}")
            else:
                try:
                    numeric_value = float(risk[field])
                    if numeric_value <= 0:
                        errors.append(f"Risk field risk.{field} must be greater than zero.")
                except (TypeError, ValueError):
                    errors.append(f"Risk field risk.{field} must be numeric.")

    evidence = data.get("evidence")
    if not isinstance(evidence, list):
        errors.append("Field 'evidence' must be a list.")
    elif len(evidence) < 2:
        errors.append("Field 'evidence' must contain at least two evidence items.")
    else:
        for index, item in enumerate(evidence, start=1):
            if not isinstance(item, dict):
                errors.append(f"Evidence item {index} must be an object.")
                continue
            if not item.get("source"):
                errors.append(f"Evidence item {index} is missing 'source'.")
            if not item.get("interpretation"):
                warnings.append(f"Evidence item {index} has no interpretation text.")

    execution = data.get("execution", {})
    if isinstance(execution, dict) and execution.get("trade_execution") not in {"disabled", False, None}:
        errors.append("Trade execution must be disabled. This skill only emits strategy specs.")

    disclaimers = data.get("disclaimers", [])
    disclaimer_text = " ".join(str(item).lower() for item in disclaimers) if isinstance(disclaimers, list) else ""
    if "not financial advice" not in disclaimer_text:
        warnings.append("Disclaimers should explicitly state that the output is not financial advice.")
    if "no trades" not in disclaimer_text and "not execute" not in disclaimer_text:
        warnings.append("Disclaimers should explicitly state that no trades are executed.")

    return errors, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate required schema, evidence, and risk controls for a MacroPulse strategy spec.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--strategy", type=Path, required=True, help="Path to a YAML or JSON strategy spec.")
    parser.add_argument("--quiet", action="store_true", help="Only print failures.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data = load_strategy(args.strategy)
    errors, warnings = validate_strategy(data)

    if errors:
        print("Validation failed.")
        for error in errors:
            print(f"ERROR: {error}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        return 1

    if not args.quiet:
        strategy = data.get("strategy", {})
        print(f"Validation passed for {strategy.get('name', 'unnamed')} version {strategy.get('version', 'unknown')}.")
        print("Required sections are present: entry, exit, risk, evidence, execution, and backtest.")
        print("Required risk fields are present: max_position_pct, stop_loss_pct, max_drawdown_pct.")
        print(f"Evidence items: {len(data.get('evidence', []))}")
        for warning in warnings:
            print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
