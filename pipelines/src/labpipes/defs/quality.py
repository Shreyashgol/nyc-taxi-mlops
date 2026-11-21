"""S1: data-quality checks on stg_trips (nulls, ranges, duplicates, row counts)."""

import dagster as dg

from ..partitions import trip_months
from ..resources import RedshiftData
from .staging import stg_trips


@dg.asset_check(
    asset=stg_trips,
    partitions_def=trip_months,
    blocking=True,
    description="Month has records and no null pickup timestamps.",
)
def stg_trips_sanity(context: dg.AssetCheckExecutionContext, redshift: RedshiftData) -> dg.AssetCheckResult:
    month = context.partition_key
    total = redshift.scalar(f"select count(*) from staging.stg_trips where trip_month = '{month}'")
    null_pickups = redshift.scalar(
        f"select count(*) from staging.stg_trips where trip_month = '{month}' and pickup_at is null"
    )
    passed = int(total or 0) > 0 and int(null_pickups or 0) == 0
    return dg.AssetCheckResult(
        passed=passed,
        severity=dg.AssetCheckSeverity.ERROR,
        description=f"{total} rows, {null_pickups} null pickup_at",
        metadata={
            "total_rows": dg.MetadataValue.int(int(total or 0)),
            "null_pickups": dg.MetadataValue.int(int(null_pickups or 0)),
        },
    )


@dg.asset_check(
    asset=stg_trips,
    partitions_def=trip_months,
    blocking=False,
    description="Trip duration and distance are plausible (>0 and reasonable max).",
)
def stg_trips_plausible_values(context: dg.AssetCheckExecutionContext, redshift: RedshiftData) -> dg.AssetCheckResult:
    month = context.partition_key
    bad_duration = redshift.scalar(
        f"select count(*) from staging.stg_trips where trip_month = '{month}' and (duration_min <= 0 or duration_min > 1440)"
    )
    bad_distance = redshift.scalar(
        f"select count(*) from staging.stg_trips where trip_month = '{month}' and (trip_distance < 0 or trip_distance > 500)"
    )
    total_bad = int(bad_duration or 0) + int(bad_distance or 0)
    passed = total_bad == 0
    return dg.AssetCheckResult(
        passed=passed,
        severity=dg.AssetCheckSeverity.WARN,
        description=f"{bad_duration} bad duration, {bad_distance} bad distance rows",
        metadata={
            "bad_duration_rows": dg.MetadataValue.int(int(bad_duration or 0)),
            "bad_distance_rows": dg.MetadataValue.int(int(bad_distance or 0)),
        },
    )
