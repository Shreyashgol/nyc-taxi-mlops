# 012: Automate RDS and Redshift restore; leave credentials and IP manual

Stage: S4 · Date: 2026-11-22 · Author: Shreyash · Drafted by agent: yes

## Choice

A restore script (`scripts/restore.sh`) starts RDS and resumes Redshift automatically, then waits for both to become available. Docker containers already come back via `restart: unless-stopped`, and serving retries model loading until MLflow (backed by RDS) is up. AWS credential refresh, GitHub secrets update, and laptop IP changes remain documented manual steps in the runbook.

## Rejected alternative

Automate everything including credential refresh by embedding a boot-time Lambda or SSM Run Command. This would add IAM complexity (we can't create IAM resources in Learner Lab) and wouldn't solve the fundamental problem: Learner Lab credentials require a human to click "Start Lab" and copy the new keys. Automating around that would be fragile and misleading.

## Why

The split follows a simple rule: automate what's deterministic and safe; document what requires human judgment or external interaction.

- **RDS start / Redshift resume**: deterministic, idempotent, no data risk. The script checks current status before acting, so running it twice is safe.
- **Docker restart policies**: already in place from S0/S3 compose files. Zero work, zero risk.
- **Credential refresh**: requires Learner Lab UI interaction — can't be scripted. Attempting it would create a false sense of automation.
- **Laptop IP**: changes unpredictably between networks. Requires `terraform apply`, which the AGENTS.md rules require student confirmation for.

## What would show this was wrong

If the restore takes more than 10 minutes of human time (not counting wait time for RDS/Redshift), or if a step we left manual causes a repeated incident, we should automate more. If a future stage needs credentials rotated automatically, we'd need a different architecture (e.g., instance profiles for GitHub runners).
