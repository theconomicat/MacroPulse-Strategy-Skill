---
name: macropulse-strategy
description: Generates backtestable crypto strategy spec outputs for AI agents from CoinMarketCap data, fear and greed index, macro news, technical indicators, and narrative signals. Use this Agent Skill when an AI agent needs market regime classification, YAML/JSON strategy spec generation, validation, replay/backtest, evidence, and a final strategy report without executing trades.
license: MIT
compatibility: Requires Python 3.10+. Demo mode runs without API keys. Live CoinMarketCap collection uses CMC_API_KEY. Trust Wallet Agent Kit and BNB Agent SDK integrations are quote-only or extension points.
---

# MacroPulse Strategy Skill

Use this skill to help an AI agent turn macroeconomic news, CoinMarketCap market data, fear and greed signals, technical indicators, and crypto narrative signals into auditable, backtestable crypto strategy specifications.

This skill produces strategy specs for research, simulation, and review. It does not provide financial advice and it must not execute trades.

## Workflow

Before running scripts, resolve the skill directory. When installed as an Agent Skill, this is the folder that contains this `SKILL.md`.

```bash
export MACROPULSE_SKILL_DIR="/path/to/macropulse-strategy"
```

1. Data collection
   - Build or review the CMC Agent Hub routing plan with `scripts/cmc_agent_hub_plan.py`.
   - Collect macro news signals with `scripts/extract_news_signals.py`.
   - Collect CoinMarketCap market context with `scripts/collect_cmc_data.py`.
   - Use demo/sample files when live credentials are unavailable.
2. Market regime classification
   - Classify the market using fear/greed, global market metrics, BTC dominance, technical indicators, macro risk, and narratives.
   - Use `references/market-regime-rules.md` for rules.
3. Strategy template selection
   - Select one of the supported templates: Fear Rebound DCA, Risk-Off Rotation, or Narrative Momentum.
   - Prefer BNB, BTC, ETH, and high-liquidity assets unless the user explicitly asks for narrative assets.
4. Strategy spec generation
   - Generate YAML or JSON using `scripts/generate_strategy.py`.
   - Follow `references/strategy-schema.md`.
5. Validation
   - Run `scripts/validate_strategy.py` before returning any final strategy.
   - Reject or revise strategies that fail schema, evidence, or risk checks.
6. Replay/backtest
   - Run `scripts/backtest_strategy.py` when OHLCV data is available.
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
- Always include evidence from at least two sources or signal categories.
- Validate before returning final output.
- Label all outputs as backtestable strategy specifications, not buy/sell recommendations.
- Use quote-only Trust Wallet Agent Kit examples unless a human explicitly approves a separate execution workflow outside this skill.
- Do not hardcode API keys, private keys, seed phrases, or secrets.

## Useful Commands

Installed skill path form:

```bash
python "$MACROPULSE_SKILL_DIR/scripts/generate_strategy.py" --demo --output /tmp/fear-rebound.yaml
python "$MACROPULSE_SKILL_DIR/scripts/validate_strategy.py" --strategy /tmp/fear-rebound.yaml
python "$MACROPULSE_SKILL_DIR/scripts/backtest_strategy.py" --strategy /tmp/fear-rebound.yaml --demo
python "$MACROPULSE_SKILL_DIR/scripts/twak_quote_plan.py" --strategy /tmp/fear-rebound.yaml
python "$MACROPULSE_SKILL_DIR/scripts/cmc_agent_hub_plan.py" --output /tmp/cmc-agent-hub-plan.json
python "$MACROPULSE_SKILL_DIR/scripts/x402_data_plan.py" --strategy /tmp/fear-rebound.yaml
python "$MACROPULSE_SKILL_DIR/scripts/bnb_agent_manifest.py" --strategy /tmp/fear-rebound.yaml
```

Repository root form:

```bash
python macropulse-strategy/scripts/generate_strategy.py --demo --output /tmp/fear-rebound.yaml
python macropulse-strategy/scripts/validate_strategy.py --strategy /tmp/fear-rebound.yaml
python macropulse-strategy/scripts/backtest_strategy.py --strategy /tmp/fear-rebound.yaml --demo
python macropulse-strategy/scripts/twak_quote_plan.py --strategy /tmp/fear-rebound.yaml
python macropulse-strategy/scripts/cmc_agent_hub_plan.py --output /tmp/cmc-agent-hub-plan.json
python macropulse-strategy/scripts/x402_data_plan.py --strategy /tmp/fear-rebound.yaml
python macropulse-strategy/scripts/bnb_agent_manifest.py --strategy /tmp/fear-rebound.yaml
```

## References

- `references/strategy-schema.md` describes the YAML/JSON strategy contract.
- `references/market-regime-rules.md` describes regime classification rules.
- `references/cmc-data-sources.md` describes CoinMarketCap data sources and live/demo behavior.
- `references/cmc-agent-hub-integration.md` describes CMC MCP, Skills Marketplace, and x402 routing.
- `references/risk-model.md` describes sizing, stop loss, drawdown, fee, and slippage assumptions.
- `references/twak-bnb-extension.md` describes quote-only TWAK and manifest-only BNB Agent SDK extensions.
- `references/demo-prompts.md` contains judge-friendly prompts.
