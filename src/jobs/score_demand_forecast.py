"""Score the @champion demand forecaster for the next 7 days, every store x product,
into the Delta table ml_demand_forecast (synced to Lakebase lb_demand_forecast).

Run: python src/jobs/score_demand_forecast.py
"""
import os
import sys

# Job tasks exec the file without __file__; the code object still knows its path.
HERE = os.path.dirname(os.path.abspath(sys._getframe().f_code.co_filename))
sys.path.insert(0, HERE)

from datetime import datetime, timezone

import mlflow
import numpy as np
from mlflow import MlflowClient

from common import FQ, insert_rows, sql
from demand_features import FEATURES, build_frame, load_history, next_days

MODEL_NAME = f"{FQ}.demand_forecaster"


def main():
    mlflow.set_registry_uri("databricks-uc")
    version = MlflowClient().get_model_version_by_alias(MODEL_NAME, "champion").version
    model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")

    hist, grid = load_history()
    horizon = next_days(7)
    frame = build_frame(hist, grid, horizon=horizon)
    frame["forecast_units"] = np.round(np.clip(model.predict(frame[FEATURES].fillna(0)), 0, None), 2)

    sql(f"""CREATE TABLE IF NOT EXISTS {FQ}.ml_demand_forecast (
              store_id STRING, product_id STRING, product_name STRING, forecast_date DATE,
              forecast_units DOUBLE, baseline_same_weekday DOUBLE, is_weekend INT, is_holiday INT,
              model_version STRING, scored_at TIMESTAMP)
            COMMENT 'Next-7-day demand per store x product from the UC model demand_forecaster@champion.'""")
    sql(f"DELETE FROM {FQ}.ml_demand_forecast")
    scored_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    frame = frame.merge(grid[["store_id", "product_id", "product_name"]].drop_duplicates(),
                        on=["store_id", "product_id"])
    rows = [(r.store_id, r.product_id, r.product_name, r.order_date.strftime("%Y-%m-%d"),
             float(r.forecast_units), None if np.isnan(r.same_dow_mean_4) else round(float(r.same_dow_mean_4), 2),
             int(r.is_weekend), int(r.is_holiday), str(version), scored_at)
            for r in frame.itertuples()]
    n = insert_rows("ml_demand_forecast",
                    ["store_id", "product_id", "product_name", "forecast_date", "forecast_units",
                     "baseline_same_weekday", "is_weekend", "is_holiday", "model_version", "scored_at"], rows)
    print(f"Scored {n:,} rows ({len(grid)} store x product × {len(horizon)} days, "
          f"{horizon[0]} → {horizon[-1]}) with {MODEL_NAME} v{version}")
    return n


if __name__ == "__main__":
    main()
