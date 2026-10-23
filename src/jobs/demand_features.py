"""Feature engineering for the store x product daily demand forecaster.

Input is gold_product_demand (completed orders). The grid is densified so a day with
no sales of a product counts as 0 units. Every lag feature looks strictly backwards,
so a forecast never sees the day it predicts.
"""
from datetime import date, timedelta

import holidays
import numpy as np
import pandas as pd

from common import FQ, sql

CITY_COUNTRY = {"Dubai": "AE", "Singapore": "SG", "London": "GB", "San Francisco": "US",
                "Kuala Lumpur": "MY", "Sydney": "AU", "Toronto": "CA"}
FEATURES = ["store_idx", "product_idx", "dow", "is_weekend", "is_holiday",
            "lag_7", "mean_28", "same_dow_mean_4"]
CATEGORICAL = [0, 1]  # store_idx, product_idx


def load_history() -> tuple[pd.DataFrame, pd.DataFrame]:
    hist = pd.DataFrame(sql(f"""
        SELECT store_id, product_id, CAST(order_date AS STRING) AS order_date, units
        FROM {FQ}.gold_product_demand"""))
    hist["order_date"] = pd.to_datetime(hist["order_date"])
    hist["units"] = hist["units"].astype(float)
    stores = pd.DataFrame(sql(f"SELECT store_id, name, city FROM {FQ}.stores"))
    products = pd.DataFrame(sql(f"SELECT product_id, name AS product_name FROM {FQ}.products"))
    stores["country"] = stores["city"].map(CITY_COUNTRY).fillna("IN")
    return hist, stores.merge(products, how="cross")


def _holiday_flags(dates: pd.Series, countries: pd.Series) -> np.ndarray:
    years = sorted({d.year for d in dates})
    cal = {c: holidays.country_holidays(c, years=years) for c in countries.unique()}
    return np.array([d.date() in cal[c] for d, c in zip(dates, countries)], dtype=int)


def build_frame(hist: pd.DataFrame, grid: pd.DataFrame, horizon: list[date] | None = None) -> pd.DataFrame:
    """Dense store x product x day frame with features.

    horizon=None: training rows over the history window, features from prior days.
    horizon=[dates]: scoring rows for future dates; lag features come from the last
    days of history (in production, history runs up to yesterday).
    """
    days = pd.date_range(hist["order_date"].min(), hist["order_date"].max(), freq="D")
    dense = (grid[["store_id", "product_id", "country"]].merge(pd.DataFrame({"order_date": days}), how="cross")
             .merge(hist, on=["store_id", "product_id", "order_date"], how="left"))
    dense["units"] = dense["units"].fillna(0.0)
    dense = dense.sort_values(["store_id", "product_id", "order_date"]).reset_index(drop=True)
    g = dense.groupby(["store_id", "product_id"])["units"]
    dense["lag_7"] = g.shift(7)
    dense["mean_28"] = g.transform(lambda s: s.shift(1).rolling(28, min_periods=14).mean())
    dense["dow"] = dense["order_date"].dt.dayofweek
    dense["same_dow_mean_4"] = (dense.groupby(["store_id", "product_id", "dow"])["units"]
                                .transform(lambda s: s.shift(1).rolling(4, min_periods=2).mean()))

    if horizon is not None:
        last = dense["order_date"].max()
        tail = dense[dense["order_date"] > last - pd.Timedelta(days=28)]
        stats = tail.groupby(["store_id", "product_id"])["units"].mean().rename("mean_28").reset_index()
        dow_stats = (tail.assign(dow=tail["order_date"].dt.dayofweek)
                     .groupby(["store_id", "product_id", "dow"])["units"].mean()
                     .rename("same_dow_mean_4").reset_index())
        last_week = tail[tail["order_date"] > last - pd.Timedelta(days=7)].assign(
            dow=lambda d: d["order_date"].dt.dayofweek)[["store_id", "product_id", "dow", "units"]]
        future = grid[["store_id", "product_id", "country"]].merge(
            pd.DataFrame({"order_date": pd.to_datetime(horizon)}), how="cross")
        future["dow"] = future["order_date"].dt.dayofweek
        dense = (future.merge(stats, on=["store_id", "product_id"], how="left")
                 .merge(dow_stats, on=["store_id", "product_id", "dow"], how="left")
                 .merge(last_week.rename(columns={"units": "lag_7"}), on=["store_id", "product_id", "dow"], how="left"))

    dense["is_weekend"] = (dense["order_date"].dt.dayofweek >= 5).astype(int)
    dense["is_holiday"] = _holiday_flags(dense["order_date"], dense["country"])
    store_codes = {s: i for i, s in enumerate(sorted(grid["store_id"].unique()))}
    product_codes = {p: i for i, p in enumerate(sorted(grid["product_id"].unique()))}
    dense["store_idx"] = dense["store_id"].map(store_codes)
    dense["product_idx"] = dense["product_id"].map(product_codes)
    return dense


def next_days(n: int = 7, start: date | None = None) -> list[date]:
    start = start or date.today()
    return [start + timedelta(days=i) for i in range(n)]
