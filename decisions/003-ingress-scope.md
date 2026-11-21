# 003: Ingress scope

Stage: S0 · Date: 2026-11-21 · Author: student · Drafted by agent: yes

## Choice

Permit inbound HTTP traffic to the app host (Traefik, port 80) from anywhere on the internet (`0.0.0.0/0`).

## Rejected alternative

Restricting inbound port 80 traffic to a fixed set of developer/student IP addresses (`<ip>/32`).

## Why

In a learner and testing environment, client IP addresses frequently change due to dynamic ISP allocations, VPN usage, and campus Wi-Fi shifts. Furthermore, automated grading scripts and health monitoring systems access the application from varying external IPs. Restricting CIDRs would lead to connectivity failures and false-negative grading runs without providing meaningful additional security in an ephemeral lab sandbox.

## What would show this was wrong

If unauthenticated external traffic results in resource exhaustion or denial of service on the EC2 host, or if course security policies mandate strict IP allowlisting.
