#!/usr/bin/env bash
# S0: register a lab host as a self-hosted GitHub Actions runner (label: lab-<role>, from
# contracts/runtime.yaml), so the CD workflow can deploy with the host's instance profile.
set -euo pipefail
export AWS_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 AWS_PAGER=""

role="${1:-app}"
label="lab-${role}"
root="$(cd "$(dirname "$0")/.." && pwd)"

iid=$(terraform -chdir="$root/infra/live" output -raw "${role}_instance_id")
repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)

echo "Registering $iid as runner with label $label for $repo..."

token=$(gh api --method POST -H "Accept: application/vnd.github+json" "/repos/$repo/actions/runners/registration-token" --jq .token)

RUNNER_VERSION="2.338.2"

cmd=$(cat <<EOF
set -eux
rm -rf /opt/actions-runner/*
cd /opt/actions-runner
curl -fsSL -o actions-runner-linux-arm64-${RUNNER_VERSION}.tar.gz "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-arm64-${RUNNER_VERSION}.tar.gz"
tar xzf ./actions-runner-linux-arm64-${RUNNER_VERSION}.tar.gz
chown -R runner:runner /opt/actions-runner
sudo -u runner ./config.sh --url "https://github.com/${repo}" --token "${token}" --labels "${label}" --unattended --replace
./svc.sh install runner || true
./svc.sh start || true
EOF
)

params=$(jq -cn --arg c "$cmd" '{commands: [$c]}')
id=$(aws ssm send-command --instance-ids "$iid" --document-name AWS-RunShellScript --parameters "$params" \
  --comment "register runner $label" --query Command.CommandId --output text)

echo "Sent SSM command $id to $iid; waiting for completion..."
status=Pending
tries=0
while [[ "$status" =~ ^(Pending|InProgress|Delayed)$ ]]; do
  ((++tries <= 60)) || { echo "timeout waiting for runner registration SSM command" >&2; exit 1; }
  sleep 3
  status=$(aws ssm get-command-invocation --command-id "$id" --instance-id "$iid" --query Status --output text 2>/dev/null || echo Pending)
done

if [[ "$status" != "Success" ]]; then
  echo "SSM command failed with status: $status" >&2
  aws ssm get-command-invocation --command-id "$id" --instance-id "$iid" --query StandardErrorContent --output text >&2
  exit 1
fi

echo "Runner registered and started successfully on $iid ($label)."
