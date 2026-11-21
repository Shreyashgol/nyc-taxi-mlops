"""S1: the S3 sensor (and the job it starts).

Watch trips/ in the data bucket (DataBucket.trip_files). When a month's file appears or changes, add
the month to the trip_months partitions and request a run that goes from trip_files to zone_hour_stats.
"""

import json

import dagster as dg

from ..partitions import trip_months
from ..resources import DataBucket
from .marts import zone_hour_stats
from .raw_trips import raw_trips
from .staging import stg_trips
from .trip_files import trip_files

ingest_month = dg.define_asset_job(
    "ingest_month",
    selection=dg.AssetSelection.assets(trip_files, raw_trips, stg_trips, zone_hour_stats),
)


@dg.sensor(job=ingest_month, minimum_interval_seconds=60)
def trips_sensor(context: dg.SensorEvaluationContext, data_bucket: DataBucket):
    seen = set(json.loads(context.cursor or "[]"))
    found = {f.month: f for f in data_bucket.trip_files()}
    new_or_changed = sorted(m for m, f in found.items() if f"{m}:{f.etag}" not in seen)
    if not new_or_changed:
        return dg.SkipReason("No new or modified trip files")

    run_requests = [
        dg.RunRequest(partition_key=m, run_key=f"{m}:{found[m].etag}")
        for m in new_or_changed
    ]
    cursor_set = seen | {f"{m}:{found[m].etag}" for m in new_or_changed}
    return dg.SensorResult(
        run_requests=run_requests,
        dynamic_partitions_requests=[trip_months.build_add_request(new_or_changed)],
        cursor=json.dumps(sorted(cursor_set)),
    )
