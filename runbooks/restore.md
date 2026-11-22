# Runbook: Restore Lab After Session Break

Owner: Shreyash · Last run: 2026-11-22 · Time to restore last run: ~5 min

## When to use it

After a Learner Lab session ends (the 4-hour mark) or after clicking "End Lab" / "Start Lab": hosts were stopped, credentials expired, RDS/Redshift may be stopped or paused.

## Before you start

- Go to AWS Academy Learner Lab → click **Start Lab** (or refresh if already running)
- Export the new AWS credentials (paste into terminal or update `~/.aws/credentials`)
- Verify: `aws sts get-caller-identity` should succeed

## Steps

One row per thing that was broken. Write the row while you fix it, not afterwards.

| # | Check (command) | Healthy looks like | If not: fix (command) | Took | Automated? |
| --- | --- | --- | --- | --- | --- |
| 1 | `aws sts get-caller-identity` | Returns account/ARN | Export fresh creds from Learner Lab console | 1 min | no — Learner Lab manual only |
| 2 | `scripts/health.sh` → laptop-ip | `OK laptop-ip <ip> is in ingress_cidrs` | Update `infra/live/terraform.tfvars` ingress_cidrs, `terraform apply` | 2 min | no — IP changes unpredictably |
| 3 | `scripts/health.sh` → app, platform, llm | `running, runner online` | Hosts restart themselves on Start Lab; runners are `restart: unless-stopped` in Docker, so they come back automatically | 0 min | yes — `restart: unless-stopped` |
| 4 | `scripts/health.sh` → rds | `available` | `aws rds start-db-instance --db-instance-identifier lab` (~7 min) | 7 min | yes — restore script |
| 5 | `scripts/health.sh` → redshift | `available` | `aws redshift resume-cluster --cluster-identifier lab` (~3 min) | 3 min | yes — restore script |
| 6 | Docker containers (app, serving, Dagster, MLflow) | Running and healthy | Containers have `restart: unless-stopped`, so they come back when Docker starts on host boot | 0 min | yes — Docker restart policy |
| 7 | Serving-champion loads model | `/predict` returns `alias: champion` | Model loads from MLflow once RDS is up (~30s after MLflow starts). `load_until_available` retries. | 0 min | yes — serving retry loop |
| 8 | `scripts/health.sh` → status | `Dagster answered` | `gh workflow run status.yaml` | 2 min | no — but scheduled in CI |
| 9 | GitHub secrets (AWS creds for workflows) | Workflows succeed | `gh secret set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY/AWS_SESSION_TOKEN` | 1 min | no — Learner Lab manual only |

## Done when

- `scripts/health.sh` exits 0
- `curl -X POST http://<app_public_ip>/predict ...` returns `"alias": "champion"`
- Status workflow is green

## What we automated, and what we left as a step

See decision record 012. Summary:
- **Automated**: RDS start + Redshift resume (restore script), Docker containers (restart policy)
- **Manual**: AWS credential refresh (Learner Lab limitation), laptop IP update (unpredictable), GitHub secrets update (depends on credential refresh)
