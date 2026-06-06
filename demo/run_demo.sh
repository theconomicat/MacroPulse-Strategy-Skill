#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
OUT_DIR="${1:-/tmp/macropulse-demo}"

mkdir -p "$OUT_DIR"

echo "MacroPulse demo output directory: $OUT_DIR"
echo "Using Python: $("$PYTHON_BIN" --version)"

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/cmc_agent_hub_plan.py" \
  --output "$OUT_DIR/cmc-agent-hub-plan.json"

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/collect_cmc_data.py" \
  --demo \
  --output "$OUT_DIR/cmc-snapshot.json"

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/extract_news_signals.py" \
  --source sample \
  --output "$OUT_DIR/news-signals.json"

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/generate_strategy.py" \
  --input "$ROOT_DIR/macropulse-strategy/examples/sample-news-input.json" \
  --cmc-snapshot "$OUT_DIR/cmc-snapshot.json" \
  --output "$OUT_DIR/fear-rebound.yaml"

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/validate_strategy.py" \
  --strategy "$OUT_DIR/fear-rebound.yaml" \
  > "$OUT_DIR/validation.txt"

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/backtest_strategy.py" \
  --strategy "$OUT_DIR/fear-rebound.yaml" \
  --demo \
  --output "$OUT_DIR/backtest.json"

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/twak_quote_plan.py" \
  --strategy "$OUT_DIR/fear-rebound.yaml" \
  > "$OUT_DIR/twak-quote-plan.txt"

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/x402_data_plan.py" \
  --strategy "$OUT_DIR/fear-rebound.yaml" \
  --output "$OUT_DIR/x402-data-plan.json"

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/bnb_agent_manifest.py" \
  --strategy "$OUT_DIR/fear-rebound.yaml" \
  --output "$OUT_DIR/bnb-agent-manifest.json"

echo "Demo complete. Artifacts:"
find "$OUT_DIR" -maxdepth 1 -type f | sort
