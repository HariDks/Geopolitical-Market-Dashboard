"""
Event-study econometrics for the Statistical Verdict page.

Pipeline: market-model (asset vs ACWI, fit on the pre-conflict window only) ->
abnormal returns -> CAR with significance -> dose-response regression,
placebo guardrail, RDiT jump test, and 3-phase reversion.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import streamlit as st
from datetime import timedelta

from config import (
    load_data, CONFLICT_START, CEASEFIRE_DATE, RELAPSE_DATE,
    MARKET_FACTOR, PLACEBOS, EXPOSURE_SCORES,
    EPICENTER, REGIONS, SECTORS, COMPANIES, SAFETY,
)

# Estimation window starts ~6 months before the war for a stable market model.
EST_START = CONFLICT_START - timedelta(days=200)

ALL_ASSETS = {**EPICENTER, **REGIONS, **SECTORS, **COMPANIES, **SAFETY}


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_prices(today):
    """Fixed analysis window (independent of the sidebar): all assets + market + placebos."""
    universe = {**ALL_ASSETS, MARKET_FACTOR[0]: MARKET_FACTOR[1], **PLACEBOS}
    return load_data(universe, EST_START, today)


def prepare(today):
    """Returns (daily_returns_df, market_return_series, models_dict)."""
    prices = _fetch_prices(today)
    # Defensive: yfinance can return a duplicate timestamp (partial bar for "today")
    # or duplicate columns, which breaks downstream index alignment.
    prices = prices.loc[~prices.index.duplicated(keep="last")]
    prices = prices.loc[:, ~prices.columns.duplicated()]
    rets = prices.pct_change(fill_method=None)
    mkt = rets.get(MARKET_FACTOR[0])
    models = {}
    if mkt is not None:
        for name in list(ALL_ASSETS) + list(PLACEBOS):
            if name in rets.columns and name != MARKET_FACTOR[0]:
                m = _fit_market_model(rets[name], mkt)
                if m is not None:
                    models[name] = m
    return rets, mkt, models


def _fit_market_model(asset_ret, mkt_ret):
    """OLS alpha/beta fit on the PRE-conflict estimation window. Returns (alpha, beta, resid_std)."""
    est = asset_ret.index < pd.Timestamp(CONFLICT_START)
    d = pd.concat([asset_ret[est], mkt_ret[est]], axis=1).dropna()
    if len(d) < 30:
        return None
    X = sm.add_constant(d.iloc[:, 1])
    res = sm.OLS(d.iloc[:, 0], X).fit()
    return res.params.iloc[0], res.params.iloc[1], res.resid.std()


def car(asset_ret, mkt, model, win_start, win_end):
    """Cumulative abnormal return over [win_start, win_end] with a classic event-study t-stat.

    asset_ret: the single asset's daily return Series. Returns (car_pct, t_stat, n_days) or None.
    """
    if model is None or mkt is None:
        return None
    alpha, beta, resid_std = model
    mask = (asset_ret.index >= pd.Timestamp(win_start)) & (asset_ret.index <= pd.Timestamp(win_end))
    actual = asset_ret[mask]
    pred = alpha + beta * mkt[mask]
    ar = (actual - pred).dropna()
    if len(ar) == 0 or resid_std == 0:
        return None
    n = len(ar)
    car_val = ar.sum()
    t = car_val / (resid_std * np.sqrt(n))
    return car_val * 100, t, n


def car_table(rets, mkt, models, win_start, win_end, names):
    """CAR for each named asset over a window. Returns {name: (car_pct, t, n)}."""
    out = {}
    for name in names:
        if name in models and name in rets.columns:
            r = car(rets[name], mkt, models[name], win_start, win_end)
            if r is not None:
                out[name] = r
    return out


def dose_response(cars):
    """Regress CAR on ex-ante exposure score (HC3 robust SE).

    cars: {name: (car_pct, t, n)}. Returns dict with points + fit, or None.
    """
    pts = [(EXPOSURE_SCORES[n], v[0], n) for n, v in cars.items() if n in EXPOSURE_SCORES]
    if len(pts) < 5:
        return None
    x = np.array([p[0] for p in pts], dtype=float)
    y = np.array([p[1] for p in pts], dtype=float)
    res = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HC3")
    xs = np.linspace(x.min(), x.max(), 50)
    # Exposure is an ordinal score, so Spearman rank correlation is the proper fit measure
    # (and is robust to oil being a huge linear outlier). R² is kept as a secondary linear gauge.
    spearman = pd.Series(y).corr(pd.Series(x), method="spearman")
    return {
        "points": [(p[2], p[0], p[1]) for p in pts],   # (name, score, car)
        "slope": res.params[1], "slope_t": res.tvalues[1],
        "r2": res.rsquared, "spearman": spearman, "intercept": res.params[0],
        "fit_x": xs, "fit_y": res.params[0] + res.params[1] * xs,
    }


def dose_response_curve(rets, mkt, models, names, windows_cal):
    """Rank-correlation of the dose-response at increasing window lengths — shows the signal
    spike then fade. Returns list of (window_days, spearman)."""
    out = []
    for d in windows_cal:
        end = CONFLICT_START + timedelta(days=d)
        cars = car_table(rets, mkt, models, CONFLICT_START, end, names)
        dr = dose_response(cars)
        if dr is not None:
            out.append((d, dr["spearman"]))
    return out


def baseline_volatility(rets, name):
    """Annualized % volatility of an asset over the PRE-war estimation window."""
    if name not in rets.columns:
        return None
    s = rets[name][rets.index < pd.Timestamp(CONFLICT_START)].dropna()
    if len(s) < 5:
        return None
    return float(s.std() * np.sqrt(252) * 100)


def cumulative_abnormal_path(asset_ret, mkt, model, win_start, win_end):
    """Cumulative abnormal return (%) as a daily path over a window — for the oil spotlight chart.

    asset_ret: the single asset's daily return Series.
    """
    if model is None or mkt is None:
        return None
    alpha, beta, _ = model
    mask = (asset_ret.index >= pd.Timestamp(win_start)) & (asset_ret.index <= pd.Timestamp(win_end))
    ar = (asset_ret[mask] - (alpha + beta * mkt[mask])).dropna()
    return (ar.cumsum() * 100) if len(ar) else None


def rdit_jump(ret, cutoff, bw=10):
    """Regression-discontinuity-in-time: local-linear jump in daily return at the cutoff.

    Returns (jump_pct, t_stat) or None.
    """
    s = ret.dropna()
    days = np.array([(d - pd.Timestamp(cutoff)).days for d in s.index])
    sel = np.abs(days) <= bw
    if sel.sum() < 8:
        return None
    d = days[sel].astype(float)
    y = s.values[sel]
    post = (d >= 0).astype(float)
    X = sm.add_constant(np.column_stack([post, d, d * post]))
    try:
        res = sm.OLS(y, X).fit(cov_type="HC3")
    except Exception:
        return None
    return res.params[1] * 100, res.tvalues[1]


def reversion_table(rets, mkt, models, names):
    """3-phase abnormal moves per asset: war (onset->ceasefire), peace (ceasefire->relapse),
    relapse (relapse->end). Plus % of the war move reversed during peace and a half-life.
    """
    today = rets.index.max()
    rows = []
    for name in names:
        if name not in models or name not in rets.columns:
            continue
        ar_series = rets[name]
        war = car(ar_series, mkt, models[name], CONFLICT_START, CEASEFIRE_DATE)
        peace = car(ar_series, mkt, models[name], CEASEFIRE_DATE, RELAPSE_DATE)
        relapse = car(ar_series, mkt, models[name], RELAPSE_DATE, today)
        if war is None:
            continue
        war_c = war[0]
        peace_c = peace[0] if peace else None
        pct_reversed = (-peace_c / war_c * 100) if (peace_c is not None and war_c != 0) else None
        rows.append({
            "asset": name,
            "war": war_c,
            "peace": peace_c,
            "relapse": relapse[0] if relapse else None,
            "pct_reversed": pct_reversed,
            "half_life": _half_life(ar_series, mkt, models[name], war_c),
        })
    return rows


def _half_life(asset_ret, mkt, model, war_c):
    """Trading days after the ceasefire for the abnormal level to revert halfway to baseline."""
    if war_c == 0:
        return None
    alpha, beta, _ = model
    mask = (asset_ret.index >= pd.Timestamp(CEASEFIRE_DATE)) & (asset_ret.index <= pd.Timestamp(RELAPSE_DATE))
    ar = (asset_ret[mask] - (alpha + beta * mkt[mask])).dropna()
    if len(ar) == 0:
        return None
    cum = ar.cumsum() * 100            # cumulative abnormal level during peace
    target = -0.5 * war_c              # halfway back toward zero
    crossed = (cum <= target) if war_c > 0 else (cum >= target)
    hits = np.where(crossed.values)[0]
    return int(hits[0] + 1) if len(hits) else None
