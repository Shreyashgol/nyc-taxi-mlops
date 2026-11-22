#!/usr/bin/env bash
# Restore the lab's managed services after a session break (S4).
# Docker containers come back on their own (restart: unless-stopped).
# This script handles RDS and Redshift, which don't auto-start.
#
#   scripts/restore.sh
#
# Prerequisites: valid AWS credentials in the environment.
# What it does NOT do (manual steps, see runbooks/restore.md):
#   - Refresh AWS credentials (Learner Lab console)
#   - Update GitHub secrets (gh secret set)
#   - Update laptop IP in terraform.tfvars (if network changed)
set -euo pipefail
export AWS_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 AWS_PAGER=""

echo "=== Lab restore: $(date -u +%FT%TZ) ==="

# --- RDS ---
rds=$(aws rds describe-db-instances --db-instance-identifier lab \
  --query 'DBInstances[0].DBInstanceStatus' --output text 2>/dev/null || echo absent)
if [[ "$rds" == "available" ]]; then
  echo "✓ RDS already available"
elif [[ "$rds" == "stopped" ]]; then
  echo "→ Starting RDS (takes ~7 min)..."
  aws rds start-db-instance --db-instance-identifier lab > /dev/null
else
  echo "⚠ RDS status: $rds (not stopped; skipping)"
fi

# --- Redshift ---
rs=$(aws redshift describe-clusters --cluster-identifier lab \
  --query 'Clusters[0].ClusterStatus' --output text 2>/dev/null || echo absent)
if [[ "$rs" == "available" ]]; then
  echo "✓ Redshift already available"
elif [[ "$rs" == "paused" ]]; then
  echo "→ Resuming Redshift (takes ~3 min)..."
  aws redshift resume-cluster --cluster-identifier lab > /dev/null
else
  echo "⚠ Redshift status: $rs (not paused; skipping)"
fi

# --- Wait for both ---
need_wait=false
if [[ "$rds" == "stopped" || "$rs" == "paused" ]]; then
  need_wait=true
fi

if $need_wait; then
  echo ""
  echo "Waiting for services to become available..."
  if [[ "$rds" == "stopped" ]]; then
    echo -n "  RDS: "
    while true; do
      s=$(aws rds describe-db-instances --db-instance-identifier lab \
        --query 'DBInstances[0].DBInstanceStatus' --output text 2>/dev/null)
      if [[ "$s" == "available" ]]; then echo "available ✓"; break; fi
      echo -n "."
      sleep 15
    done
  fi
  if [[ "$rs" == "paused" ]]; then
    echo -n "  Redshift: "
    while true; do
      s=$(aws redshift describe-clusters --cluster-identifier lab \
        --query 'Clusters[0].ClusterStatus' --output text 2>/dev/null)
      if [[ "$s" == "available" ]]; then echo "available ✓"; break; fi
      echo -n "."
      sleep 10
    done
  fi
fi

echo ""
echo "=== Automated restore done ==="
echo ""
echo "Manual steps remaining:"
echo "  1. Update GitHub secrets if credentials changed:"
echo "     gh secret set AWS_ACCESS_KEY_ID --body \"\$AWS_ACCESS_KEY_ID\""
echo "     gh secret set AWS_SECRET_ACCESS_KEY --body \"\$AWS_SECRET_ACCESS_KEY\""
echo "     gh secret set AWS_SESSION_TOKEN --body \"\$AWS_SESSION_TOKEN\""
echo "  2. If your IP changed, update infra/live/terraform.tfvars and terraform apply"
echo "  3. Run: scripts/health.sh"
