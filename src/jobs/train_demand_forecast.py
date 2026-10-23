"""Train the store x product daily demand forecaster, compare it with the heuristics the
preparation plan used before, log everything to MLflow and register it in Unity Catalog.

The model only gets the @champion alias if it beats the same-weekday baseline on the
last 14 days held out. Run: python src/jobs/train_demand_forecast.py
"""
import os
import sys

# Job tasks exec the file without __file__; the code object still knows its path.
HERE = os.path.dirname(os.path.abspath(sys._getframe().f_code.co_filename))
sys.path.insert(0, HERE)

import mlflow
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn.ensemble import HistGradientBoostingRegressor

from common import FQ
from demand_features import CATEGORICAL, FEATURES, build_frame, load_history

MODEL_NAME = f"{FQ}.demand_forecaster"
EXPERIMENT = os.environ.get("KAAPI_FORECAST_EXPERIMENT", "/Shared/kaapi_bricks_demand_forecast")
HOLDOUT_DAYS = 14


def metrics(y, yhat, prefix):
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    return {f"{prefix}_mae": float(np.mean(np.abs(y - yhat))),
            f"{prefix}_wape": float(np.sum(np.abs(y - yhat)) / max(np.sum(y), 1e-9))}


def main():
    mlflow.set_tracking_uri("databricks")
    mlflow.set_registry_uri("databricks-uc")
    mlflow.set_experiment(EXPERIMENT)

    hist, grid = load_history()
    frame = build_frame(hist, grid).dropna(subset=["mean_28", "same_dow_mean_4", "lag_7"])
    cutoff = frame["order_date"].max() - pd.Timedelta(days=HOLDOUT_DAYS)
    train, test = frame[frame["order_date"] <= cutoff], frame[frame["order_date"] > cutoff]
    print(f"history {hist['order_date'].min().date()} → {hist['order_date'].max().date()}, "
          f"train rows {len(train):,}, holdout rows {len(test):,} (last {HOLDOUT_DAYS} days)")

    params = {"loss": "poisson", "max_iter": 300, "learning_rate": 0.05, "max_leaf_nodes": 31,
              "min_samples_leaf": 40, "l2_regularization": 1.0, "random_state": 42}
    with mlflow.start_run(run_name="demand-forecaster") as run:
        model = HistGradientBoostingRegressor(categorical_features=CATEGORICAL, **params)
        model.fit(train[FEATURES], train["units"])
        pred = np.clip(model.predict(test[FEATURES]), 0, None)

        results = {**metrics(test["units"], pred, "model"),
                   **metrics(test["units"], test["same_dow_mean_4"], "baseline_same_weekday"),
                   **metrics(test["units"], test["mean_28"], "baseline_28d_mean")}
        results["mae_improvement_vs_same_weekday_pct"] = 100 * (
            1 - results["model_mae"] / results["baseline_same_weekday_mae"])
        mlflow.log_params({**params, "features": ",".join(FEATURES), "holdout_days": HOLDOUT_DAYS,
                           "train_rows": len(train), "holdout_rows": len(test)})
        mlflow.log_metrics(results)

        # Error by day type: where does the model beat the heuristic?
        seg = test.assign(pred=pred, err_model=np.abs(test["units"] - pred),
                          err_base=np.abs(test["units"] - test["same_dow_mean_4"]))
        seg["day_type"] = np.where(seg["is_holiday"] == 1, "holiday",
                                   np.where(seg["is_weekend"] == 1, "weekend", "weekday"))
        by_type = seg.groupby("day_type")[["err_model", "err_base"]].mean().round(3)
        mlflow.log_table(by_type.reset_index(), "mae_by_day_type.json")

        signature = infer_signature(test[FEATURES].head(50), pred[:50])
        info = mlflow.sklearn.log_model(model, name="model", signature=signature,
                                        input_example=test[FEATURES].head(5),
                                        registered_model_name=MODEL_NAME)
        version = info.registered_model_version

        beats = results["model_mae"] < results["baseline_same_weekday_mae"]
        if beats:
            MlflowClient().set_registered_model_alias(MODEL_NAME, "champion", version)

    print(f"\nMLflow run: {run.info.run_id}")
    print(f"Registered: {MODEL_NAME} v{version}  champion={'yes' if beats else 'no (baseline kept)'}")
    print("\nHoldout accuracy (lower is better):")
    for k in ("model", "baseline_same_weekday", "baseline_28d_mean"):
        print(f"  {k:<24} MAE {results[k + '_mae']:.3f}   WAPE {results[k + '_wape']:.3f}")
    print(f"  MAE improvement vs same-weekday baseline: {results['mae_improvement_vs_same_weekday_pct']:.1f}%")
    print("\nMAE by day type (model vs same-weekday baseline):")
    print(by_type.rename(columns={"err_model": "model_mae", "err_base": "baseline_mae"}).to_string())
    return {"run_id": run.info.run_id, "version": version, "champion": beats, **results}


if __name__ == "__main__":
    main()
