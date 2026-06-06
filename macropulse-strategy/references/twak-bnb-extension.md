# Trust Wallet and BNB Agent SDK Extension

MacroPulse is a Track 2 Strategy Skill, so it must not execute live trades. The Trust Wallet and BNB integrations are therefore structured as safe extension artifacts.

## Trust Wallet Agent SDK

The Trust Wallet Agent SDK exposes wallet infrastructure through CLI and MCP/REST surfaces. MacroPulse uses this only for quote-only planning:

```bash
python macropulse-strategy/scripts/twak_quote_plan.py --strategy /tmp/fear-rebound.yaml
```

The output includes:

- Runtime check command: `npx @trustwallet/cli --version`
- Quote-only swap intent: `twak swap 100 USDC BNB --quote-only`
- Alert intents for take-profit and stop-loss prices
- Human approval checklist

MacroPulse never loads wallet credentials, never signs transactions, and never calls a swap API.

## BNB Agent SDK

BNB Agent SDK supports:

- ERC-8004 agent identity metadata
- ERC-8183 agentic commerce deliverables

MacroPulse emits a manifest for these concepts without private keys or on-chain transactions:

```bash
python macropulse-strategy/scripts/bnb_agent_manifest.py \
  --strategy /tmp/fear-rebound.yaml \
  --output /tmp/bnb-agent-manifest.json
```

The manifest contains:

- ERC-8004 profile metadata for MacroPulse Strategy Skill
- Supported deliverables: strategy YAML, validation report, replay metrics, CMC Agent Hub plan, TWAK quote plan
- ERC-8183-style acceptance criteria for a strategy deliverable
- SHA-256 hash of the strategy spec

## Safety Boundary

These integrations are designed to increase real-world adoption while preserving Track 2 scope:

- No private keys
- No signing
- No on-chain registration by default
- No escrow funding
- No transaction execution
- Human/operator review before any external runtime action
