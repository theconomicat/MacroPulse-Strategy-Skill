---
name: macropulse-strategy
description: Generates backtestable crypto strategy spec outputs for AI agents from live CoinMarketCap MCP tools, fear and greed, macro events, CMC latest news, technical indicators, derivatives, narratives, validation, and replay/backtest evidence. Use this Agent Skill when an AI agent needs market regime classification, YAML/JSON strategy spec generation, Trust Wallet quote-only planning, BNB Agent SDK manifest output, and a final strategy report without executing trades.
license: MIT
compatibility: Requires Python 3.9+ and CMC_MCP_API_KEY or CMC_API_KEY for live CoinMarketCap MCP collection. Trust Wallet Agent Kit and BNB Agent SDK integrations are quote-only or manifest-only extension points.
---

# MacroPulse Strategy Skill

Use this skill to help an AI agent turn live CoinMarketCap MCP market data into auditable, backtestable crypto strategy specifications.

This skill produces strategy specs for research, simulation, and review. It does not provide financial advice and it must not execute trades.

## Workflow

Before running scripts, resolve the skill directory. When installed as an Agent Skill, this is the folder that contains this `SKILL.md`.

```bash
export MACROPULSE_SKILL_DIR="/path/to/macropulse-strategy"
```

1. Data collection
   - Require `CMC_MCP_API_KEY` or `CMC_API_KEY` in the environment.
   - Build or review the CMC Agent Hub routing plan with `scripts/cmc_agent_hub_plan.py --check-live`.
   - Collect live CoinMarketCap MCP market context with `scripts/collect_cmc_data.py`.
   - Confirm the snapshot reports `source_mode: live_cmc_mcp` and includes the 12 expected CMC MCP tools.
2. Market regime classification
   - Classify the market using CMC fear/greed, global market metrics, BTC dominance, derivatives, technical indicators, macro events, latest CMC news, and narratives.
   - Use `references/market-regime-rules.md` for rules.
3. Strategy template selection
   - Select one of the supported templates: Fear Rebound DCA, Risk-Off Rotation, or Narrative Momentum.
   - Prefer BNB, BTC, ETH, and high-liquidity assets unless the user explicitly asks for narrative assets.
4. Strategy spec generation
   - Generate YAML or JSON using `scripts/generate_strategy.py`.
   - Follow `references/strategy-schema.md`.
5. Validation
   - Run `scripts/validate_strategy.py` before returning any final strategy.
   - Reject or revise strategies that fail schema, evidence, risk, or execution-safety checks.
6. Replay/backtest
   - Run `scripts/backtest_strategy.py` against the live CMC MCP snapshot.
   - Include fees and slippage assumptions.
7. Final report
   - Return the strategy spec, evidence summary, validation result, replay metrics, risk limits, assumptions, and caveats.
   - Optionally produce a Trust Wallet Agent Kit quote-only plan with `scripts/twak_quote_plan.py`.
   - Optionally produce an x402 data access plan with `scripts/x402_data_plan.py`.
   - Optionally produce a BNB Agent SDK service manifest with `scripts/bnb_agent_manifest.py`.

## Skill Rules

- Do not provide financial advice.
- Do not execute trades, swaps, transfers, approvals, or wallet actions.
- Always include risk limits: `max_position_pct`, `stop_loss_pct`, and `max_drawdown_pct`.
- Always include evidence from at least two CMC MCP signal categories.
- Validate before returning final output.
- Label all outputs as backtestable strategy specifications, not buy/sell recommendations.
- Use quote-only Trust Wallet Agent Kit examples unless a human explicitly approves a separate execution workflow outside this skill.
- Do not hardcode API keys, private keys, seed phrases, or secrets.

## Useful Commands

Installed skill path form:

```bash
python3 "$MACROPULSE_SKILL_DIR/scripts/collect_cmc_data.py" --assets BNB,BTC,ETH --primary BNB --output /tmp/live-cmc.json
python3 "$MACROPULSE_SKILL_DIR/scripts/generate_strategy.py" --cmc-snapshot /tmp/live-cmc.json --output /tmp/live-strategy.yaml
python3 "$MACROPULSE_SKILL_DIR/scripts/validate_strategy.py" --strategy /tmp/live-strategy.yaml
python3 "$MACROPULSE_SKILL_DIR/scripts/backtest_strategy.py" --strategy /tmp/live-strategy.yaml --cmc-snapshot /tmp/live-cmc.json
python3 "$MACROPULSE_SKILL_DIR/scripts/twak_quote_plan.py" --strategy /tmp/live-strategy.yaml
python3 "$MACROPULSE_SKILL_DIR/scripts/cmc_agent_hub_plan.py" --check-live --output /tmp/cmc-agent-hub-plan.json
python3 "$MACROPULSE_SKILL_DIR/scripts/x402_data_plan.py" --strategy /tmp/live-strategy.yaml
python3 "$MACROPULSE_SKILL_DIR/scripts/bnb_agent_manifest.py" --strategy /tmp/live-strategy.yaml
```

Repository root form:

```bash
python3 macropulse-strategy/scripts/collect_cmc_data.py --assets BNB,BTC,ETH --primary BNB --output /tmp/live-cmc.json
python3 macropulse-strategy/scripts/generate_strategy.py --cmc-snapshot /tmp/live-cmc.json --output /tmp/live-strategy.yaml
python3 macropulse-strategy/scripts/validate_strategy.py --strategy /tmp/live-strategy.yaml
python3 macropulse-strategy/scripts/backtest_strategy.py --strategy /tmp/live-strategy.yaml --cmc-snapshot /tmp/live-cmc.json
python3 macropulse-strategy/scripts/twak_quote_plan.py --strategy /tmp/live-strategy.yaml
python3 macropulse-strategy/scripts/cmc_agent_hub_plan.py --check-live --output /tmp/cmc-agent-hub-plan.json
python3 macropulse-strategy/scripts/x402_data_plan.py --strategy /tmp/live-strategy.yaml
python3 macropulse-strategy/scripts/bnb_agent_manifest.py --strategy /tmp/live-strategy.yaml
```

## References

- `references/strategy-schema.md` describes the YAML/JSON strategy contract.
- `references/market-regime-rules.md` describes regime classification rules.
- `references/cmc-data-sources.md` describes live CoinMarketCap MCP data sources.
- `references/cmc-agent-hub-integration.md` describes CMC MCP, Skills Marketplace, and x402 routing.
- `references/risk-model.md` describes sizing, stop loss, drawdown, fee, and slippage assumptions.
- `references/twak-bnb-extension.md` describes quote-only TWAK and manifest-only BNB Agent SDK extensions.
- `references/demo-prompts.md` contains judge-friendly prompts.
