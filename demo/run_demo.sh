#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
OUT_DIR="${1:-/tmp/macropulse-demo}"

mkdir -p "$OUT_DIR"

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  . "$ROOT_DIR/.env"
  set +a
fi

echo "MacroPulse demo output directory: $OUT_DIR"
echo "Using Python: $("$PYTHON_BIN" --version)"
if [ -n "${CMC_MCP_API_KEY:-}${CMC_API_KEY:-}" ]; then
  echo "CMC MCP key present: yes"
else
  echo "CMC MCP key present: no"
fi

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/cmc_agent_hub_plan.py" \
  --check-live \
  --output "$OUT_DIR/cmc-agent-hub-plan.json"

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/collect_cmc_data.py" \
  --assets BNB,BTC,ETH \
  --primary BNB \
  --output "$OUT_DIR/cmc-snapshot.json"

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/generate_strategy.py" \
  --cmc-snapshot "$OUT_DIR/cmc-snapshot.json" \
  --output "$OUT_DIR/fear-rebound.yaml"

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/validate_strategy.py" \
  --strategy "$OUT_DIR/fear-rebound.yaml" \
  > "$OUT_DIR/validation.txt"

"$PYTHON_BIN" "$ROOT_DIR/macropulse-strategy/scripts/backtest_strategy.py" \
  --strategy "$OUT_DIR/fear-rebound.yaml" \
  --cmc-snapshot "$OUT_DIR/cmc-snapshot.json" \
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
