"""S2: the feature_contract check on trip_features.

contracts/features.yaml lists the model's inputs, label and the post-trip columns that must never be
inputs; contracts/mlflow.yaml says this check blocks.
"""

import dagster as dg

from ..contracts import features_contract
from ..partitions import trip_months
from ..resources import RedshiftData
from .features import trip_features


@dg.asset_check(
    asset=trip_features,
    partitions_def=trip_months,
    blocking=True,
    description="Verify columns, forbidden fields, and value ranges against contracts/features.yaml.",
)
def feature_contract(
    context: dg.AssetCheckExecutionContext, redshift: RedshiftData
) -> dg.AssetCheckResult:
    month = context.partition_key
    contract = features_contract()

    # 1. Verify schema column names and ensure no forbidden columns are present
    col_rows = redshift.query(
        "select column_name from information_schema.columns "
        "where table_schema = 'staging' and table_name = 'trip_features'"
    )
    actual_cols = {r["column_name"].lower() for r in col_rows}

    forbidden = {c.lower() for c in contract.get("forbidden", [])}
    forbidden_present = actual_cols & forbidden
    if forbidden_present:
        return dg.AssetCheckResult(
            passed=False,
            severity=dg.AssetCheckSeverity.ERROR,
            description=f"Forbidden post-trip columns present in staging.trip_features: {sorted(forbidden_present)}",
            metadata={"forbidden_columns": dg.MetadataValue.json(sorted(forbidden_present))},
        )

    expected_inputs = {c["name"].lower() for c in contract.get("inputs", [])}
    expected_keys = {c["name"].lower() for c in contract.get("keys", [])}
    label = contract["label"]["name"].lower()
    expected_all = expected_inputs | expected_keys | {label}
    missing_cols = expected_all - actual_cols
    if missing_cols:
        return dg.AssetCheckResult(
            passed=False,
            severity=dg.AssetCheckSeverity.ERROR,
            description=f"Missing expected columns in staging.trip_features: {sorted(missing_cols)}",
            metadata={"missing_columns": dg.MetadataValue.json(sorted(missing_cols))},
        )

    # 2. Verify value ranges for the given partition month
    bad_rows = redshift.scalar(
        f"select count(*) from staging.trip_features where trip_month = '{month}' and ("
        "pickup_zone_id not between 1 and 263 "
        "or dropoff_zone_id not between 1 and 263 "
        "or pickup_hour not between 0 and 23 "
        "or pickup_dow not between 0 and 6 "
        "or duration_min <= 0 or duration_min > 180)"
    )

    total_rows = redshift.scalar(
        f"select count(*) from staging.trip_features where trip_month = '{month}'"
    )

    passed = int(bad_rows or 0) == 0 and int(total_rows or 0) > 0
    return dg.AssetCheckResult(
        passed=passed,
        severity=dg.AssetCheckSeverity.ERROR,
        description=f"{total_rows} rows checked; {bad_rows} out-of-range rows found",
        metadata={
            "total_rows": dg.MetadataValue.int(int(total_rows or 0)),
            "bad_rows": dg.MetadataValue.int(int(bad_rows or 0)),
        },
    )
