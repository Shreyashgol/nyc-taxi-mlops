# 003: Ingress scope

Stage: S0 · Date: 2026-11-21 · Author: student · Drafted by agent: yes

## Choice

Restrict inbound HTTP traffic to the app host (Traefik, port 80) exclusively to the student's personal public IP address (`115.244.141.202/32`).

## Rejected alternative

Opening port 80 to the entire public internet (`0.0.0.0/0`).

## Why

Following the principle of least privilege and network defense-in-depth, services under development should not be exposed to arbitrary external probes, scanners, or denial-of-service traffic from the public internet. Restricting ingress strictly to the student's current public IP prevents unauthorized access while allowing the student full capability to test and interact with the service.

## What would show this was wrong

If changes in network location (e.g., roaming to mobile data, campus Wi-Fi, or VPN) or automated external grading runners from unpredictable IP pools fail to reach the app host due to blocked traffic.
