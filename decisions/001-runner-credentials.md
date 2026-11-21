# 001: Runner credentials

Stage: S0 · Date: 2026-11-21 · Author: student · Drafted by agent: yes

## Choice

Authenticate the self-hosted GitHub Actions runner on the app EC2 host using the host's attached EC2 instance profile (`LabInstanceProfile`).

## Rejected alternative

Injecting temporary AWS Academy session credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`) into GitHub repository secrets.

## Why

AWS Academy Learner Lab sessions expire every 4 hours, which invalidates static session tokens. Relying on GitHub secrets would require manually updating repository secrets after every session refresh. The attached EC2 `LabInstanceProfile` provides temporary credentials directly via the Instance Metadata Service (IMDSv2) automatically, keeping the runner fully functional across session restarts with zero secrets stored in GitHub.

## What would show this was wrong

If a runner workflow requires AWS IAM permissions that `LabRole` does not possess, or if runner jobs need to execute under isolated credentials distinct from the host EC2 instance.
