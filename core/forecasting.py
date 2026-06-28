"""
Time-series forecasting techniques for demand forecasting.

Implements, with textbook-exact recursions (Taylor, Introduction to
Management Science):
  1. Exponential Smoothing
  2. Adjusted (Trend-Adjusted) Exponential Smoothing
  3. Linear Trend Line (least squares)
  4. Seasonal Adjustment (seasonal indices)

Each function returns the in-sample fitted values AND a forward forecast,
so the same arrays can drive both accuracy validation and the dashboard.
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np


# --------------------------------------------------------------------------
# 1. Exponential smoothing
# --------------------------------------------------------------------------
def exponential_smoothing(demand, alpha: float = 0.5):
    """
    F_{t+1} = alpha * D_t + (1 - alpha) * F_t,  with F_1 = D_1.

    Returns
    -------
    forecasts : list of length n+1
        forecasts[t] is the forecast made FOR period t (1-indexed by position;
        forecasts[0] corresponds to period 1). The final element is the
        one-step-ahead forecast for the period after the data ends.
    """
    d = np.asarray(demand, dtype=float)
    n = len(d)
    f = np.zeros(n + 1)
    f[0] = d[0]  # F_1 = D_1
    for t in range(n):
        f[t + 1] = alpha * d[t] + (1 - alpha) * f[t]
    return f.tolist()


# --------------------------------------------------------------------------
# 2. Adjusted (trend-adjusted) exponential smoothing
# --------------------------------------------------------------------------
@dataclass
class AdjustedESResult:
    forecast: list  # simple exp-smoothing forecasts F_t
    trend: list  # smoothed trend T_t
    adjusted: list  # AF_t = F_t + T_t
    next_forecast: float  # AF for the first out-of-sample period


def adjusted_exponential_smoothing(demand, alpha: float = 0.5, beta: float = 0.3):
    """
    Trend-adjusted exponential smoothing.

        F_{t+1}  = alpha * D_t + (1 - alpha) * F_t
        T_{t+1}  = beta * (F_{t+1} - F_t) + (1 - beta) * T_t
        AF_{t+1} = F_{t+1} + T_{t+1}

    Initial conditions: F_1 = D_1, T_1 = 0.
    """
    d = np.asarray(demand, dtype=float)
    n = len(d)
    F = np.zeros(n + 1)
    T = np.zeros(n + 1)
    AF = np.zeros(n + 1)
    F[0] = d[0]
    T[0] = 0.0
    AF[0] = F[0] + T[0]
    for t in range(n):
        F[t + 1] = alpha * d[t] + (1 - alpha) * F[t]
        T[t + 1] = beta * (F[t + 1] - F[t]) + (1 - beta) * T[t]
        AF[t + 1] = F[t + 1] + T[t + 1]
    return AdjustedESResult(
        forecast=F.tolist(),
        trend=T.tolist(),
        adjusted=AF.tolist(),
        next_forecast=float(AF[-1]),
    )


# --------------------------------------------------------------------------
# 3. Linear trend line (least squares regression on time)
# --------------------------------------------------------------------------
@dataclass
class LinearTrendResult:
    intercept: float  # a
    slope: float  # b
    fitted: list  # a + b*x for x = 1..n

    def predict(self, periods_ahead: int = 1):
        n = len(self.fitted)
        return [
            self.intercept + self.slope * (n + k) for k in range(1, periods_ahead + 1)
        ]


def linear_trend(demand):
    """
    Fit y = a + b*x by least squares, with x = 1, 2, ..., n.

        b = (sum(xy) - n * xbar * ybar) / (sum(x^2) - n * xbar^2)
        a = ybar - b * xbar
    """
    y = np.asarray(demand, dtype=float)
    n = len(y)
    x = np.arange(1, n + 1, dtype=float)
    xbar, ybar = x.mean(), y.mean()
    b = (np.sum(x * y) - n * xbar * ybar) / (np.sum(x**2) - n * xbar**2)
    a = ybar - b * xbar
    fitted = (a + b * x).tolist()
    return LinearTrendResult(intercept=float(a), slope=float(b), fitted=fitted)


# --------------------------------------------------------------------------
# 4. Seasonal adjustment (multiplicative seasonal indices)
# --------------------------------------------------------------------------
@dataclass
class SeasonalResult:
    seasonal_factors: list  # one factor per season position
    deseasonalized: list  # demand / factor
    base_forecast: list  # trend forecast on deseasonalized series
    seasonal_forecast: list  # base_forecast * factor (re-seasonalized)


def seasonal_adjustment(demand, season_length: int):
    """
    Multiplicative seasonal indices.

      1. Group the series by season position (e.g. month-of-year).
      2. Seasonal factor S_i = mean(demand in season i) / overall mean.
      3. Deseasonalize, fit a linear trend, then re-apply the factors.

    season_length : number of periods in one full cycle (e.g. 12 for monthly).
    """
    d = np.asarray(demand, dtype=float)
    n = len(d)
    overall_mean = d.mean()

    # seasonal factor per position 0..season_length-1
    factors = np.zeros(season_length)
    for s in range(season_length):
        vals = d[s::season_length]
        factors[s] = vals.mean() / overall_mean if len(vals) else 1.0

    full_factors = np.array([factors[i % season_length] for i in range(n)])
    deseason = d / full_factors

    trend = linear_trend(deseason)
    base = np.asarray(trend.fitted)
    seasonal_fc = base * full_factors

    return SeasonalResult(
        seasonal_factors=factors.tolist(),
        deseasonalized=deseason.tolist(),
        base_forecast=base.tolist(),
        seasonal_forecast=seasonal_fc.tolist(),
    )


# --------------------------------------------------------------------------
# 5. Parameter tuning + validation (back-testing on historical data)
# --------------------------------------------------------------------------
def _mad(actual, forecast) -> float:
    a = np.asarray(actual, dtype=float)
    f = np.asarray(forecast, dtype=float)
    return float(np.mean(np.abs(a - f))) if len(a) else float("nan")


@dataclass
class TuningResult:
    alpha: float
    beta: float
    train_mad: float
    validation_mad: float
    holdout: int
    grid_size: int


def autotune_adjusted_es(
    demand,
    alpha_grid=None,
    beta_grid=None,
    holdout: int | None = None,
):
    """Select (alpha, beta) for trend-adjusted ES by minimising error on a
    held-out tail of the series (back-testing on historical data).

    Falls back to in-sample fit when the series is too short to hold out.
    Returns a :class:`TuningResult`.
    """
    d = np.asarray(demand, dtype=float)
    n = len(d)
    if alpha_grid is None:
        alpha_grid = [round(0.05 * k, 2) for k in range(1, 20)]  # 0.05 .. 0.95
    if beta_grid is None:
        beta_grid = [round(0.05 * k, 2) for k in range(0, 19)]  # 0.00 .. 0.90

    if holdout is None:
        holdout = max(1, min(6, n // 4))
    use_holdout = n - holdout >= 3

    best = None
    for a in alpha_grid:
        for b in beta_grid:
            if use_holdout:
                train = d[:-holdout]
                res = adjusted_exponential_smoothing(train, alpha=a, beta=b)
                last_F, last_T = res.forecast[-1], res.trend[-1]
                preds = [last_F + last_T * k for k in range(1, holdout + 1)]
                val = _mad(d[-holdout:], preds)
                tr = _mad(train, res.adjusted[: len(train)])
            else:
                res = adjusted_exponential_smoothing(d, alpha=a, beta=b)
                val = tr = _mad(d, res.adjusted[:n])
            if best is None or val < best[2] - 1e-9:
                best = (a, b, val, tr)

    a, b, val, tr = best
    return TuningResult(
        alpha=a,
        beta=b,
        train_mad=round(tr, 4),
        validation_mad=round(val, 4),
        holdout=holdout if use_holdout else 0,
        grid_size=len(alpha_grid) * len(beta_grid),
    )


@dataclass
class BacktestResult:
    holdout: int
    train_size: int
    predictions: list
    actuals: list
    mad: float
    mape: float


def backtest_adjusted_es(demand, alpha: float, beta: float, holdout: int | None = None):
    """Hold out the last ``holdout`` points, fit on the rest, and report
    out-of-sample accuracy — the validation step from the brief."""
    d = np.asarray(demand, dtype=float)
    n = len(d)
    if holdout is None:
        holdout = max(1, min(6, n // 4))
    holdout = max(1, min(holdout, n - 2))
    train = d[:-holdout]
    res = adjusted_exponential_smoothing(train, alpha=alpha, beta=beta)
    last_F, last_T = res.forecast[-1], res.trend[-1]
    preds = [last_F + last_T * k for k in range(1, holdout + 1)]
    actuals = d[-holdout:]
    mad = _mad(actuals, preds)
    nz = actuals != 0
    mape = (
        float(np.mean(np.abs((actuals[nz] - np.array(preds)[nz]) / actuals[nz])) * 100)
        if nz.any()
        else float("nan")
    )
    return BacktestResult(
        holdout=holdout,
        train_size=len(train),
        predictions=[round(float(p), 2) for p in preds],
        actuals=[round(float(x), 2) for x in actuals],
        mad=round(mad, 4),
        mape=round(mape, 4),
    )
