# 007: What stays in the notebook vs. what moves to the pipeline

Stage: S2 · Date: 2026-11-21 · Author: Shreyash Golhani · Drafted by agent: yes

## Choice

Exploratory data analysis, diagnostic plots, feature distribution inspections, and ad-hoc hyperparameter searches stay in the SageMaker JupyterLab notebook (`notebooks/explore.ipynb`). Production feature extraction, schema and contract validations, reproducible model training, evaluation on holdout data, and MLflow model registration live entirely in the automated Dagster pipeline (`pipelines/`).

## Rejected alternative

Training and registering candidate models directly from the interactive notebook environment.

## Why

Notebooks are mutable and prone to out-of-order execution, hidden state, and uncommitted local code dependencies, making reproducible auditing impossible. Automated pipeline execution guarantees deterministic environments, enforces blocking quality gates before artifacts reach storage, and provides traceable lineage linking model versions directly to Git commit SHAs and data partition cursors.

## What would show this was wrong

If rapid experimental iteration and feedback loops become prohibitively bottlenecked by pipeline scheduling overhead, requiring interactive training sessions for debugging complex architectures.
