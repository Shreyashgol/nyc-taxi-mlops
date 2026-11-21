# 002: Image tag scheme

Stage: S0 · Date: 2026-11-21 · Author: student · Drafted by agent: yes

## Choice

Tag container images with the short Git commit SHA (`sha-${GITHUB_SHA::7}`) corresponding to the exact commit built on `main`.

## Rejected alternative

Using mutable tags exclusively (e.g., `latest`) or manually incremented semantic versions (e.g., `v1.0.0`).

## Why

Git commit SHAs guarantee strict immutability and complete end-to-end traceability between any deployed container image in GHCR and the source code in git. This aligns with other services in the repo (`platform.yaml` and `serving.yaml`). Rollbacks become deterministic and safe, as rolling back simply means pointing the deployment configuration to the commit SHA of the previous known healthy release.

## What would show this was wrong

If external non-technical stakeholders require human-ordered semantic release numbers (SemVer) directly on container registry tags without referencing git commit history.
