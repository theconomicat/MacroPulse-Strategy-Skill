#!/usr/bin/env python3
"""Run a lightweight OHLCV replay for a MacroPulse strategy spec."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only when dependency is missing.
    yaml = None


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_OHLCV = SKILL_DIR / "examples" / "sample-bnb-ohlcv.csv"


def load_strategy(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SystemExit(f"Strategy file not found: {path}") from exc

    if path.suffix.lower() == ".json":
        return json.loads(raw)
    if yaml is None:
        raise SystemExit("PyYAML is required to read YAML strategies. Install dependencies with: pip install -r requirements.txt")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise SystemExit(f"Strategy file must contain a top-level object: {path}")
    return data


def load_ohlcv(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except FileNotFoundError as exc:
        raise SystemExit(f"OHLCV file not found: {path}") from exc

    normalized: list[dict[str, Any]] = []
    required = {"date", "open", "high", "low", "close", "volume"}
    for index, row in enumerate(rows, start=2):
        if not required.issubset(row):
            raise SystemExit(f"OHLCV row {index} is missing one of: {', '.join(sorted(required))}")
        try:
            normalized.append(
                {
                    "date": row["date"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
            )
        except ValueError as exc:
            raise SystemExit(f"OHLCV row {index} contains a non-numeric price or volume.") from exc
    if len(normalized) < 10:
        raise SystemExit("OHLCV replay requires at least 10 rows.")
    return normalized


def moving_average(values: list[float], index: int, period: int) -> float | None:
    if index + 1 < period:
        return None
    window = values[index + 1 - period : index + 1]
    return sum(window) / period


def relative_strength_index(values: list[float], index: int, period: int = 5) -> float | None:
    if index < period:
        return None
    gains = 0.0
    losses = 0.0
    for cursor in range(index - period + 1, index + 1):
        change = values[cursor] - values[cursor - 1]
        if change >= 0:
            gains += change
        else:
            losses += abs(change)
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100 - (100 / (1 + rs))


def extract_exit_pct(strategy: dict[str, Any], key: str, default: float) -> float:
    exit_section = strategy.get("exit", {})
    candidates = []
    if isinstance(exit_section, dict):
        for group in ["any", "all"]:
            values = exit_section.get(group, [])
            if isinstance(values, list):
                candidates.extend(values)
    for candidate in candidates:
        if isinstance(candidate, dict) and key in candidate:
            try:
                return float(candidate[key])
            except (TypeError, ValueError):
                return default
    return default


def template_key(strategy: dict[str, Any]) -> str:
    strategy_meta = strategy.get("strategy", {})
    raw = f"{strategy_meta.get('name', '')} {strategy_meta.get('template', '')}".lower()
    if "risk_off" in raw or "risk-off" in raw:
        return "risk_off"
    if "narrative" in raw or "momentum" in raw:
        return "narrative"
    return "fear_rebound"


def should_enter(template: str, index: int, closes: list[float], volumes: list[float], strategy: dict[str, Any]) -> bool:
    close = closes[index]
    rsi = relative_strength_index(closes, index)
    sma5 = moving_average(closes, index, 5)
    sma10 = moving_average(closes, index, 10)
    recent_high = max(closes[max(0, index - 7) : index + 1])
    drawdown_from_high_pct = (recent_high - close) / recent_high * 100 if recent_high else 0.0

    if template == "fear_rebound":
        threshold = 42.0
        entry = strategy.get("entry", {})
        for item in entry.get("all", []) if isinstance(entry, dict) else []:
            if isinstance(item, dict) and "bnb_rsi_14_lte" in item:
                threshold = float(item["bnb_rsi_14_lte"])
        return bool(rsi is not None and rsi <= threshold and drawdown_from_high_pct >= 3.0)

    if template == "risk_off":
        return bool(sma10 is not None and close > sma10 and index % 6 == 0)

    average_volume = moving_average(volumes, index, 5)
    previous_sma5 = moving_average(closes, index - 1, 5) if index > 0 else None
    previous_close = closes[index - 1] if index > 0 else close
    return bool(
        sma5 is not None
        and previous_sma5 is not None
        and average_volume is not None
        and close > sma5
        and previous_close <= previous_sma5
        and volumes[index] > average_volume * 1.03
    )


def should_exit(
    close: float,
    avg_cost: float,
    holding_days: int,
    rsi: float | None,
    strategy: dict[str, Any],
) -> tuple[bool, str]:
    take_profit_pct = extract_exit_pct(strategy, "take_profit_pct", 12.0)
    stop_loss_pct = float(strategy.get("risk", {}).get("stop_loss_pct", extract_exit_pct(strategy, "stop_loss_pct", 5.0)))
    time_stop_days = strategy.get("exit", {}).get("time_stop_days") if isinstance(strategy.get("exit"), dict) else None

    if avg_cost <= 0:
        return False, ""
    if close >= avg_cost * (1 + take_profit_pct / 100):
        return True, "take_profit"
    if close <= avg_cost * (1 - stop_loss_pct / 100):
        return True, "stop_loss"
    if rsi is not None and rsi >= 72:
        return True, "rsi_overheated"
    if isinstance(time_stop_days, int) and holding_days >= time_stop_days:
        return True, "time_stop"
    return False, ""


def run_replay(strategy: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    risk = strategy.get("risk", {})
    execution = strategy.get("execution", {})
    fee_bps = float(risk.get("fee_bps", 10))
    slippage_bps = float(risk.get("slippage_bps", 8))
    max_position_pct = float(risk.get("max_position_pct", execution.get("max_position_pct", 20)))
    allocation_per_entry_pct = float(execution.get("allocation_per_entry_pct", min(4.0, max_position_pct)))
    max_entries = int(execution.get("max_entries", 5))
    template = template_key(strategy)

    closes = [row["close"] for row in rows]
    volumes = [row["volume"] for row in rows]
    cash = 1.0
    units = 0.0
    avg_cost = 0.0
    open_trade_cost = 0.0
    entry_count = 0
    holding_days = 0
    fees_paid = 0.0
    transaction_count = 0
    round_trip_count = 0
    wins = 0
    trade_log: list[dict[str, Any]] = []
    equity_curve: list[float] = []

    for index, row in enumerate(rows):
        close = row["close"]
        equity = cash + units * close
        equity_curve.append(equity)
        rsi = relative_strength_index(closes, index)

        if units > 0:
            holding_days += 1
            exit_now, reason = should_exit(close, avg_cost, holding_days, rsi, strategy)
            if exit_now:
                effective_price = close * (1 - slippage_bps / 10000)
                gross_proceeds = units * effective_price
                fee = gross_proceeds * fee_bps / 10000
                net_proceeds = gross_proceeds - fee
                pnl = net_proceeds - open_trade_cost
                cash += net_proceeds
                fees_paid += fee
                transaction_count += 1
                round_trip_count += 1
                if pnl > 0:
                    wins += 1
                trade_log.append(
                    {
                        "date": row["date"],
                        "side": "sell",
                        "reason": reason,
                        "price": round(effective_price, 4),
                        "pnl_pct": round(pnl / open_trade_cost * 100, 4) if open_trade_cost else 0.0,
                    }
                )
                units = 0.0
                avg_cost = 0.0
                open_trade_cost = 0.0
                entry_count = 0
                holding_days = 0
                equity_curve[-1] = cash
                continue

        if entry_count < max_entries and should_enter(template, index, closes, volumes, strategy):
            equity = cash + units * close
            current_position_value = units * close
            max_position_value = equity * max_position_pct / 100
            allowed_position = max(0.0, max_position_value - current_position_value)
            desired_notional = equity * allocation_per_entry_pct / 100
            notional = min(cash, desired_notional, allowed_position)
            if notional > 0.001:
                effective_price = close * (1 + slippage_bps / 10000)
                fee = notional * fee_bps / 10000
                acquired_units = (notional - fee) / effective_price
                previous_cost_basis = avg_cost * units
                units += acquired_units
                avg_cost = (previous_cost_basis + acquired_units * effective_price) / units
                cash -= notional
                open_trade_cost += notional
                fees_paid += fee
                transaction_count += 1
                entry_count += 1
                holding_days = 0
                trade_log.append(
                    {
                        "date": row["date"],
                        "side": "buy",
                        "reason": template,
                        "price": round(effective_price, 4),
                        "notional_pct": round(notional * 100, 4),
                    }
                )

    if units > 0:
        close = closes[-1]
        effective_price = close * (1 - slippage_bps / 10000)
        gross_proceeds = units * effective_price
        fee = gross_proceeds * fee_bps / 10000
        net_proceeds = gross_proceeds - fee
        pnl = net_proceeds - open_trade_cost
        cash += net_proceeds
        fees_paid += fee
        transaction_count += 1
        round_trip_count += 1
        if pnl > 0:
            wins += 1
        trade_log.append(
            {
                "date": rows[-1]["date"],
                "side": "sell",
                "reason": "end_of_window",
                "price": round(effective_price, 4),
                "pnl_pct": round(pnl / open_trade_cost * 100, 4) if open_trade_cost else 0.0,
            }
        )
        units = 0.0
        open_trade_cost = 0.0
        equity_curve.append(cash)

    final_equity = cash + units * closes[-1]
    total_return_pct = (final_equity - 1.0) * 100
    max_drawdown_pct = calculate_max_drawdown(equity_curve)
    win_rate = wins / round_trip_count if round_trip_count else 0.0

    return {
        "strategy_name": strategy.get("strategy", {}).get("name", "unknown"),
        "template": strategy.get("strategy", {}).get("template", "unknown"),
        "data_points": len(rows),
        "total_return_pct": round(total_return_pct, 4),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "win_rate": round(win_rate, 4),
        "trade_count": round_trip_count,
        "transaction_count": transaction_count,
        "fees_paid_pct": round(fees_paid * 100, 4),
        "slippage_assumption_bps": slippage_bps,
        "fee_assumption_bps": fee_bps,
        "trade_log": trade_log,
        "notes": [
            "This is a lightweight daily OHLCV replay for hackathon validation, not a production quant engine.",
            "Fees and slippage are deducted from simulated cash flows.",
            "No live orders or wallet actions are performed.",
        ],
    }


def calculate_max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = -math.inf
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            drawdown = (peak - equity) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a lightweight replay/backtest on daily OHLCV data for a MacroPulse strategy spec.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--strategy", type=Path, required=True, help="Path to a YAML or JSON strategy spec.")
    parser.add_argument("--ohlcv", type=Path, default=DEFAULT_OHLCV, help="CSV file with date,open,high,low,close,volume columns.")
    parser.add_argument("--demo", action="store_true", help="Use the bundled sample BNB OHLCV CSV.")
    parser.add_argument("--output", type=Path, help="Write replay metrics JSON to this file instead of stdout.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    strategy = load_strategy(args.strategy)
    ohlcv_path = DEFAULT_OHLCV if args.demo else args.ohlcv
    rows = load_ohlcv(ohlcv_path)
    result = run_replay(strategy, rows)
    rendered = json.dumps(result, indent=2, sort_keys=False)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Backtest metrics written to {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
