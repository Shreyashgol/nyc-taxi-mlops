# 009: Training window and holdout split

Stage: S2 · Date: 2026-11-21 · Author: Shreyash Golhani · Drafted by agent: yes

## Choice

The training window spans months `2024-01..2024-03` (three months), and evaluation is performed on `2024-04` (one month) as a chronological holdout dataset.

## Rejected alternative

A random k-fold or percentage-based split randomly sampling trips across the entire 2024-01..04 period.

## Why

Taxi demand, weather, and traffic patterns exhibit strong temporal autocorrelation and seasonality. A random split allows future trip conditions to leak into past training samples, artificially inflating test metrics. A forward chronological holdout mirrors true production inference: training on historical observations to forecast future unseen periods.

## What would show this was wrong

If abrupt macroeconomic or seasonal shifts (e.g., severe weather anomalies or policy changes in April) render earlier historical months poor estimators, suggesting a shorter moving training window or dynamic weighting would be required.
