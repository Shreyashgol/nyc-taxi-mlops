# 011: Automatic blue-green switch after smoke test plus predict validation

Stage: S3 · Date: 2026-11-22 · Author: Shreyash · Drafted by agent: yes

## Choice

The CD workflow deploys to the idle colour, runs `deploy/web.sh smoke <colour>` (which checks `/version` returns the expected git SHA and `/predict` returns a valid response), and — if both pass — automatically switches traffic with `deploy/web.sh switch <colour>`. No human approval gate on deploy.

## Rejected alternative

**Manual approval (GitHub environment with required reviewers):** the CD deploys the idle colour and waits for a human to approve the switch. This is safer for high-risk changes but slows every deploy. With a solo developer and a one-host lab, the delay isn't worth the protection — especially since the old colour keeps running and `deploy/web.sh switch <other>` rolls back in under 2 seconds.

Also considered automatic with only the basic smoke test (no predict validation), but adding the extra `/predict` check costs one curl call and catches model-integration regressions before they reach riders.

## Why

Blue-green already provides instant rollback: the old colour is still running. The richer smoke test (version SHA match + valid `/predict` response) catches both deployment errors and app-serving integration issues. If anything fails, the switch doesn't happen and the live colour is unaffected. This gives fast, safe deploys without human bottlenecks.

## What would show this was wrong

If a bad deploy passes the smoke test but causes issues in production (e.g., a subtle bug that the basic predict call doesn't catch), we would add a soak period or manual approval gate.
