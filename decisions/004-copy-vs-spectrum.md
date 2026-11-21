# 004: COPY vs Redshift Spectrum for monthly ingestion

Stage: S1 · Date: 2026-11-21 · Author: student · Drafted by agent: yes

## Choice

Load monthly TLC Parquet files from S3 into Redshift managed local storage (`ingest.raw_trips`) using the Redshift `COPY` command.

## Rejected alternative

Querying the monthly landed Parquet files directly in S3 using Redshift Spectrum external tables.

## Why

`COPY` loads the Parquet data directly into Redshift's columnar format, enabling automatic compression, local sort keys, and fast repeated analytical queries when transforming data into `staging.stg_trips` and aggregating `marts.zone_hour_stats`. Spectrum avoids local storage consumption, but incurs remote per-query S3 scan latencies and Data API overhead on downstream transformations. Given our Learner Lab single-node `ra3.large` with 20 GB allocation, storing 4 months of compressed trip data is well within storage limits while providing superior query throughput.

## What would show this was wrong

If monthly data volumes grow to the point of exhausting the 100 GB EBS storage quota of the Learner Lab, or if ingest times become a bottleneck compared to ad-hoc external querying.
