# 005: Distribution and sort keys for trip tables

Stage: S1 · Date: 2026-11-21 · Author: student · Drafted by agent: yes

## Choice

Use `DISTSTYLE AUTO` and compound `SORTKEY (source_file, tpep_pickup_datetime)` on `ingest.raw_trips`, with `SORTKEY (pickup_at)` on `staging.stg_trips`.

## Rejected alternative

Distributing by pickup zone ID (`DISTKEY (pulocationid)`) or using `DISTSTYLE EVEN`.

## Why

Our pipeline queries and materializes data partitioned by month and time range. Sorting on `tpep_pickup_datetime` allows Redshift's Zone Map metadata to prune unneeded blocks during partition materialization and range scans. On a single-node `ra3.large` cluster, distribution keys across slices provide minimal parallel join benefits compared to the risk of data skew if a few zones (like JFK/LaGuardia) hold disproportionate traffic. `DISTSTYLE AUTO` allows Redshift to manage slice distribution optimally.

## What would show this was wrong

If multi-node clustering is introduced and joins between `stg_trips` and `taxi_zones` become network-bound due to broad broadcast reshuffling.
