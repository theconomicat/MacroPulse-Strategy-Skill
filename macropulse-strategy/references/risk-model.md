# Risk Model

MacroPulse strategies are research specifications. Risk limits are mandatory because the output is intended for validation and replay, not discretionary advice.

## Required Limits

| Field | Meaning |
|---|---|
| `max_position_pct` | Maximum simulated portfolio allocation allowed for the strategy or asset. |
| `stop_loss_pct` | Price-based loss threshold used by the strategy spec and replay. |
| `max_drawdown_pct` | Maximum tolerated strategy drawdown before the spec should be rejected or revised. |

The validator fails if any required risk field is missing or non-positive.

## Position Sizing

Fear Rebound DCA:

- Uses small repeated entries.
- Typical setting: 4% per entry, 20% maximum position.
- Stops adding after max entries, stop-loss, or drawdown breach.

Risk-Off Rotation:

- Caps volatile asset exposure.
- Keeps defensive stablecoin allocation in the spec.
- Blocks new illiquid altcoin entries during elevated risk.

Narrative Momentum:

- Uses smaller entries than the DCA template.
- Requires liquidity and security filters for non-large-cap assets.
- Uses higher slippage assumptions because narrative assets can be less liquid.

## Fee and Slippage Assumptions

Replay includes:

- `fee_bps`: charged on simulated entry and exit.
- `slippage_bps`: applied to the effective entry and exit prices.

Example:

```yaml
risk:
  fee_bps: 10
  slippage_bps: 8
```

These are assumptions for lightweight validation. Production analysis should use venue-specific quotes, route depth, spread, and execution logs.

## CMC MCP Replay

`scripts/backtest_strategy.py` uses CMC MCP quote performance horizons from `get_crypto_quotes_latest`.

The replay:

- Applies the strategy's maximum position percentage.
- Deducts round-trip fee and slippage assumptions.
- Reports total return, max drawdown, win rate, trade count, fees paid, and slippage assumption.
- Does not place orders or simulate exchange order-book depth.

## Drawdown

The replay derives drawdown from the worst net weighted horizon return:

```text
max_drawdown_pct = abs(min(net_strategy_return_pct))
```

The strategy should be revised if replay drawdown exceeds `risk.max_drawdown_pct`.

## No Trade Execution

This risk model does not authorize execution. Trust Wallet Agent Kit output is quote-only. Any real-world execution requires a separate human approval process and security review outside this skill.
