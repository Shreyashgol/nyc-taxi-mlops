"""S2: training_set, trained_model, eval_report, the challenger gate and the challenger asset.

- training_set: UNLOAD a window of staging.trip_features (and the holdout month) to the artifact bucket.
  The zone-pair distance lookup (contracts/features.yaml, est_distance_miles) comes from the window only.
- trained_model: fit tripmodel.LightGBMModel (the given v2), log it to MLflow as a pyfunc with
  tripmodel.model_signature() and the tripmodel package bundled, register a version of the model named
  in contracts/mlflow.yaml, and tag it as that contract says.
- eval_report: tripmodel.evaluate the new version and the champion (or the v1 baseline before there is
  one) on the same holdout; log the metrics.
- A blocking check that guards a `challenger` asset, which sets the alias. The pipeline never moves
  `champion`.
"""

import os
from pathlib import Path

import dagster as dg
import mlflow
import mlflow.pyfunc
import tripmodel
from tripmodel import BaselineModel, LightGBMModel, evaluate, model_signature

from ..contracts import features_contract, mlflow_contract
from ..resources import ArtifactBucket, MlflowTracking, RedshiftData
from .features import trip_features

TRAINING_WINDOW = "2024-01..2024-03"
TRAINING_MONTHS = ["2024-01", "2024-02", "2024-03"]
HOLDOUT_MONTH = "2024-04"


@dg.asset(
    deps=[trip_features],
    group_name="model",
    kinds={"redshift", "s3"},
    pool="redshift",
)
def training_set(
    redshift: RedshiftData, artifacts: ArtifactBucket
) -> dg.MaterializeResult:
    """UNLOAD staging.trip_features for the training window and holdout to the artifact bucket."""
    unload_months = ", ".join(f"''{m}''" for m in TRAINING_MONTHS)
    query_months = ", ".join(f"'{m}'" for m in TRAINING_MONTHS)

    # UNLOAD training window
    redshift.execute(
        f"unload ('select pickup_zone_id, dropoff_zone_id, pickup_hour, pickup_dow, duration_min "
        f"from staging.trip_features where trip_month in ({unload_months})') "
        f"to '{artifacts.uri('datasets/train/')}' "
        "iam_role default format as parquet cleanpath"
    )

    # UNLOAD holdout
    redshift.execute(
        f"unload ('select pickup_zone_id, dropoff_zone_id, pickup_hour, pickup_dow, duration_min "
        f"from staging.trip_features where trip_month = ''{HOLDOUT_MONTH}''') "
        f"to '{artifacts.uri('datasets/holdout/')}' "
        "iam_role default format as parquet cleanpath"
    )

    # UNLOAD distance lookup (from training window of staging.stg_trips only)
    redshift.execute(
        f"unload ('select pickup_zone_id, dropoff_zone_id, "
        f"percentile_cont(0.5) within group (order by trip_distance) as est_distance_miles "
        f"from staging.stg_trips where trip_month in ({unload_months}) "
        f"and trip_distance > 0 and trip_distance < 100 "
        f"and pickup_zone_id between 1 and 263 and dropoff_zone_id between 1 and 263 "
        f"group by pickup_zone_id, dropoff_zone_id') "
        f"to '{artifacts.uri('datasets/distances/')}' "
        "iam_role default format as parquet cleanpath"
    )

    train_rows = redshift.scalar(
        f"select count(*) from staging.trip_features where trip_month in ({query_months})"
    )
    holdout_rows = redshift.scalar(
        f"select count(*) from staging.trip_features where trip_month = '{HOLDOUT_MONTH}'"
    )

    artifacts.write_json(
        "datasets/meta.json",
        {
            "training_window": TRAINING_WINDOW,
            "holdout_month": HOLDOUT_MONTH,
            "train_rows": int(train_rows or 0),
            "holdout_rows": int(holdout_rows or 0),
        },
    )

    return dg.MaterializeResult(
        metadata={
            "training_window": TRAINING_WINDOW,
            "holdout_month": HOLDOUT_MONTH,
            "train_rows": dg.MetadataValue.int(int(train_rows or 0)),
            "holdout_rows": dg.MetadataValue.int(int(holdout_rows or 0)),
        }
    )


@dg.asset(
    deps=[training_set],
    group_name="model",
    kinds={"mlflow", "python"},
)
def trained_model(
    artifacts: ArtifactBucket, tracking: MlflowTracking
) -> dg.MaterializeResult:
    """Fit LightGBMModel on training window, log to MLflow, and register version."""
    client = tracking.client()
    contract = mlflow_contract()

    train_df = artifacts.read_parquet("datasets/train")
    dist_df = artifacts.read_parquet("datasets/distances")

    model = LightGBMModel().fit(train_df, dist_df)

    git_sha = os.environ.get("GIT_SHA", "unknown")
    features_ver = str(features_contract().get("version", 1))

    with mlflow.start_run(run_name="train_lightgbm") as run:
        run_id = run.info.run_id
        info = mlflow.pyfunc.log_model(
            name="model",
            python_model=model,
            signature=model_signature(),
            code_paths=[str(Path(tripmodel.__file__).parent)],
            registered_model_name=contract["registered_model"],
        )

    version = str(info.registered_model_version)

    # Set version tags required by contracts/mlflow.yaml
    client.set_model_version_tag(
        contract["registered_model"], version, "training_window", TRAINING_WINDOW
    )
    client.set_model_version_tag(
        contract["registered_model"], version, "holdout_month", HOLDOUT_MONTH
    )
    client.set_model_version_tag(
        contract["registered_model"], version, "features_version", features_ver
    )
    client.set_model_version_tag(
        contract["registered_model"], version, "git_sha", git_sha
    )

    artifacts.write_json(
        "models/latest_training.json",
        {
            "run_id": run_id,
            "version": version,
            "training_window": TRAINING_WINDOW,
            "holdout_month": HOLDOUT_MONTH,
            "git_sha": git_sha,
        },
    )

    return dg.MaterializeResult(
        metadata={
            "run_id": run_id,
            "version": version,
            "registered_model": contract["registered_model"],
        }
    )


@dg.asset(
    deps=[trained_model],
    group_name="model",
    kinds={"mlflow", "python"},
)
def eval_report(
    artifacts: ArtifactBucket, tracking: MlflowTracking, redshift: RedshiftData
) -> dg.MaterializeResult:
    """Evaluate candidate model on holdout, compare against champion (or baseline), and log metrics."""
    client = tracking.client()
    contract = mlflow_contract()
    latest = artifacts.read_json("models/latest_training.json")
    version = str(latest["version"])
    run_id = latest["run_id"]

    holdout_df = artifacts.read_parquet("datasets/holdout")
    train_df = artifacts.read_parquet("datasets/train")
    dist_df = artifacts.read_parquet("datasets/distances")

    # Borough lookup
    zone_rows = redshift.query("select location_id, borough from ingest.taxi_zones")
    boroughs = {int(r["location_id"]): str(r["borough"] or "Unknown") for r in zone_rows}

    # Evaluate candidate
    candidate = mlflow.pyfunc.load_model(f"models:/{contract['registered_model']}/{version}")
    candidate_metrics = evaluate(candidate.predict, holdout_df, boroughs)

    # Evaluate champion (or baseline if no champion exists)
    champion_mae = None
    try:
        champion = mlflow.pyfunc.load_model(f"models:/{contract['registered_model']}@champion")
        champ_metrics = evaluate(champion.predict, holdout_df, boroughs)
        champion_mae = champ_metrics["mae_min"]
    except Exception:
        # No champion yet: fallback to BaselineModel
        v1 = BaselineModel().fit(train_df, dist_df)
        base_metrics = evaluate(lambda df: v1.predict(None, df), holdout_df, boroughs)
        champion_mae = base_metrics["mae_min"]

    # Metrics required by contracts/mlflow.yaml
    metrics = {
        "mae_min": candidate_metrics["mae_min"],
        "p95_latency_ms": candidate_metrics["p95_latency_ms"],
        "champion_mae_min": float(champion_mae),
        "mae_min.airport": candidate_metrics.get("mae_min.airport", 0.0),
        "mae_min.manhattan": candidate_metrics.get("mae_min.manhattan", 0.0),
        "mae_min.outer": candidate_metrics.get("mae_min.outer", 0.0),
        "mae_min.night": candidate_metrics.get("mae_min.night", 0.0),
    }

    # Log metrics to MLflow run
    with mlflow.start_run(run_id=run_id):
        for k, v in metrics.items():
            mlflow.log_metric(k, v)

    # Set metrics tags on model version
    client.set_model_version_tag(
        contract["registered_model"], version, "mae_min", f"{metrics['mae_min']:.4f}"
    )
    client.set_model_version_tag(
        contract["registered_model"],
        version,
        "p95_latency_ms",
        f"{metrics['p95_latency_ms']:.2f}",
    )
    client.set_model_version_tag(
        contract["registered_model"], version, "champion_mae_min", f"{champion_mae:.4f}"
    )

    # Decision rule: beats champion/baseline by at least 0.05 min and p95 latency <= 20 ms
    beats = metrics["mae_min"] <= champion_mae - 0.05
    latency_ok = metrics["p95_latency_ms"] <= 20.0
    passed = beats and latency_ok

    report = {
        "version": version,
        "run_id": run_id,
        "candidate_mae": metrics["mae_min"],
        "champion_mae": champion_mae,
        "p95_latency_ms": metrics["p95_latency_ms"],
        "beats": beats,
        "latency_ok": latency_ok,
        "passed": passed,
    }
    artifacts.write_json("reports/latest_eval.json", report)

    return dg.MaterializeResult(
        metadata={
            "version": version,
            "candidate_mae": dg.MetadataValue.float(metrics["mae_min"]),
            "champion_mae": dg.MetadataValue.float(champion_mae),
            "p95_latency_ms": dg.MetadataValue.float(metrics["p95_latency_ms"]),
            "passed": dg.MetadataValue.bool(passed),
        }
    )


@dg.asset_check(
    asset=eval_report,
    blocking=True,
    description="Model beats champion/baseline MAE within the latency budget.",
)
def beats_champion(artifacts: ArtifactBucket) -> dg.AssetCheckResult:
    report = artifacts.read_json("reports/latest_eval.json")
    passed = bool(report.get("passed", False))
    return dg.AssetCheckResult(
        passed=passed,
        severity=dg.AssetCheckSeverity.ERROR,
        description=(
            f"Candidate MAE {report.get('candidate_mae', 0):.4f} vs "
            f"Champion MAE {report.get('champion_mae', 0):.4f}, "
            f"p95 latency {report.get('p95_latency_ms', 0):.2f} ms"
        ),
        metadata={
            "candidate_mae": dg.MetadataValue.float(report.get("candidate_mae", 0.0)),
            "champion_mae": dg.MetadataValue.float(report.get("champion_mae", 0.0)),
            "p95_latency_ms": dg.MetadataValue.float(report.get("p95_latency_ms", 0.0)),
        },
    )


@dg.asset(
    deps=[eval_report],
    group_name="model",
    kinds={"mlflow"},
)
def challenger(
    artifacts: ArtifactBucket, tracking: MlflowTracking
) -> dg.MaterializeResult:
    """Set the challenger alias in MLflow for the newly evaluated model version."""
    client = tracking.client()
    contract = mlflow_contract()
    report = artifacts.read_json("reports/latest_eval.json")
    version = str(report["version"])

    client.set_registered_model_alias(contract["registered_model"], "challenger", version)
    return dg.MaterializeResult(
        metadata={
            "registered_model": contract["registered_model"],
            "alias": "challenger",
            "version": version,
        }
    )


train_model = dg.define_asset_job(
    "train_model",
    selection=dg.AssetSelection.assets(
        training_set, trained_model, eval_report, challenger
    ),
)
