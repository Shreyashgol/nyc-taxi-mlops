# 006: Blocking vs warning data quality gates

Stage: S1 · Date: 2026-11-21 · Author: student · Drafted by agent: yes

## Choice

Enforce `schema_contract` on `trip_files` and zero-row / null-timestamp checks on `stg_trips` as blocking gates; treat duration, distance, and zone range outliers as warnings.

## Rejected alternative

Configuring every data quality validation rule as a blocking error that halts the entire monthly pipeline run.

## Why

Parquet schema alterations (column additions, deletions, or type changes) and completely empty files cause positional `COPY` failures and catastrophic errors in downstream transformations, so they must strictly block. Conversely, real-world TLC taxi trip data regularly contains anomalous records (e.g. meter calibration errors with negative durations or extreme distance outliers). Blocking on minor record-level noise would prevent entire valid months from materializing; emitting asset check warnings preserves observability while downstream feature engineering filters out the bad rows.

## What would show this was wrong

If dirty or out-of-range records leak into `marts.zone_hour_stats` and distort downstream assistant metric quotes or ML training targets beyond acceptable error tolerances.
