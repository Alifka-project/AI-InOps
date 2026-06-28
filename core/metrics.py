"""
Forecast accuracy metrics.

All formulas follow the standard management-science definitions
(Taylor, Introduction to Management Science) so that hand-worked
examples reproduce these values exactly.
"""
from __future__ import annotations
import numpy as np


def _clean(actual, forecast):
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    mask = ~np.isnan(actual) & ~np.isnan(forecast)
    return actual[mask], forecast[mask]


def mad(actual, forecast) -> float:
    """Mean Absolute Deviation = sum(|D_t - F_t|) / n."""
    a, f = _clean(actual, forecast)
    if len(a) == 0:
        return float("nan")
    return float(np.mean(np.abs(a - f)))


def mse(actual, forecast) -> float:
    """Mean Squared Error = sum((D_t - F_t)^2) / n."""
    a, f = _clean(actual, forecast)
    if len(a) == 0:
        return float("nan")
    return float(np.mean((a - f) ** 2))


def mape(actual, forecast) -> float:
    """Mean Absolute Percentage Error (%) = mean(|D_t - F_t| / D_t) * 100."""
    a, f = _clean(actual, forecast)
    nz = a != 0
    if nz.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((a[nz] - f[nz]) / a[nz])) * 100)


def bias(actual, forecast) -> float:
    """Cumulative error E = sum(D_t - F_t). Positive = under-forecasting."""
    a, f = _clean(actual, forecast)
    return float(np.sum(a - f))


def summary(actual, forecast) -> dict:
    """All metrics in one dict, rounded for reporting."""
    return {
        "MAD": round(mad(actual, forecast), 4),
        "MSE": round(mse(actual, forecast), 4),
        "MAPE": round(mape(actual, forecast), 4),
        "Bias": round(bias(actual, forecast), 4),
    }
