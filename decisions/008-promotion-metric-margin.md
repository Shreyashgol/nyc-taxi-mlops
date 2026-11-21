# 008: Promotion metric and margin

Stage: S2 · Date: 2026-11-21 · Author: Shreyash Golhani · Drafted by agent: yes

## Choice

A newly trained model version is promoted to the `challenger` alias if its holdout Mean Absolute Error (`mae_min`) beats the incumbent model (the current `champion`, or the v1 baseline when no champion exists) by at least 0.05 minutes, while satisfying a strict p95 single-row inference latency constraint of $\le 20\text{ ms}$.

## Rejected alternative

Promoting on Root Mean Squared Error (RMSE) without latency gating or threshold margins.

## Why

Mean Absolute Error penalizes duration prediction errors linearly, reflecting passengers' practical sensitivity to delay without disproportionately skewing weights toward extreme multi-hour traffic outliers. The latency constraint ensures that gains in prediction accuracy do not compromise real-time serving SLAs.

## What would show this was wrong

If passenger satisfaction or downstream operations suffer due to large errors on specific slices (such as airport trips or peak night hours) that were masked by modest improvements in average overall MAE, or if online serving latency spikes under production concurrency.
