"""S1: the schema_contract check on trip_files.

Compare the landed file's Parquet footer (the DataBucket resource reads it) with
contracts/trips.schema.yaml, before raw_trips copies anything. contracts/platform.yaml says this check
is blocking.
"""

import dagster as dg

from ..contracts import trips_schema
from ..partitions import trip_months
from ..resources import DataBucket
from .trip_files import trip_files


@dg.asset_check(
    asset=trip_files,
    partitions_def=trip_months,
    blocking=True,
    description="Parquet footer matches contracts/trips.schema.yaml before COPY.",
)
def schema_contract(context: dg.AssetCheckExecutionContext, data_bucket: DataBucket) -> dg.AssetCheckResult:
    month = context.partition_key
    footer = data_bucket.footer(month)
    expected = trips_schema()

    errors: list[str] = []
    if len(footer.columns) != len(expected):
        errors.append(f"column count mismatch: expected {len(expected)}, got {len(footer.columns)}")
    else:
        for i, (act, exp) in enumerate(zip(footer.columns, expected, strict=True)):
            if act.name.lower() != exp.name.lower():
                errors.append(f"column {i} name mismatch: expected {exp.name}, got {act.name}")
            if act.type != exp.type:
                errors.append(f"column {i} ({act.name}) type mismatch: expected {exp.type}, got {act.type}")

    passed = len(errors) == 0
    return dg.AssetCheckResult(
        passed=passed,
        severity=dg.AssetCheckSeverity.ERROR,
        description="Schema matches contract" if passed else "; ".join(errors[:3]),
        metadata={
            "num_columns": dg.MetadataValue.int(len(footer.columns)),
            "errors": dg.MetadataValue.json(errors),
        },
    )
