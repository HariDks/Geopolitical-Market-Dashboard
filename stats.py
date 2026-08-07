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
    load_data, CONFLICT_START,
    MARKET_FACTOR, PLACEBOS, EXPOSURE_SCORES, PHASES, EPISODES,
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


def dose_response_curve(rets, mkt, models, names, windows_cal, event=CONFLICT_START):
    """Rank-correlation of the dose-response at increasing window lengths — shows the signal
    spike then fade. Returns list of (window_days, spearman)."""
    out = []
    for d in windows_cal:
        end = event + timedelta(days=d)
        cars = car_table(rets, mkt, models, event, end, names)
        dr = dose_response(cars)
        if dr is not None:
            out.append((d, dr["spearman"]))
    return out


# =====================================================================
# Trading-day-aligned event study
#
# Calendar windows are NOT comparable across shocks: Feb 28 2026 fell on a
# Saturday (first tradeable day Mar 2) while Jul 7 was a Tuesday. A 7-calendar-day
# window therefore buys 5 trading days for Round 1 and 6 for Round 2. Every
# cross-episode comparison below counts trading days from the first session at or
# after the shock, so both rounds get the same number of observations.
# =====================================================================

def trading_days_from(index, event, ntd=None):
    """Sessions at or after `event`, capped at `ntd` (all of them if ntd is None)."""
    post = index[index >= pd.Timestamp(event)]
    return post[:ntd] if ntd is not None else post


def abnormal_series(rets, mkt, model, name, days):
    """Daily abnormal returns (fraction, not %) for `name` over the given DatetimeIndex."""
    if model is None or mkt is None or name not in rets.columns:
        return None
    alpha, beta, _ = model
    days = days.intersection(rets.index)
    if not len(days):
        return None
    return (rets[name].loc[days] - (alpha + beta * mkt.loc[days])).dropna()


def car_td(rets, mkt, models, name, event, ntd):
    """CAR over the first `ntd` TRADING days from `event`. Returns (car_pct, t, n) or None.

    Unlike car(), returns None if fewer than `ntd` sessions exist, so a partially
    elapsed episode never gets compared against a fully elapsed one.
    """
    if name not in models:
        return None
    days = trading_days_from(rets.index, event, ntd)
    if len(days) < ntd:
        return None
    ar = abnormal_series(rets, mkt, models[name], name, days)
    resid_std = models[name][2]
    if ar is None or not len(ar) or resid_std == 0:
        return None
    return ar.sum() * 100, ar.sum() / (resid_std * np.sqrt(len(ar))), len(ar)


def car_table_td(rets, mkt, models, names, event, ntd):
    """car_td for each named asset. Returns {name: (car_pct, t, n)}."""
    out = {}
    for name in names:
        r = car_td(rets, mkt, models, name, event, ntd)
        if r is not None:
            out[name] = r
    return out


def staircase_curve_td(rets, mkt, models, names, event, tds):
    """Dose-response rank correlation at increasing TRADING-day windows.

    Returns list of (trading_days, spearman, slope, slope_t).
    """
    out = []
    for td in tds:
        cars = car_table_td(rets, mkt, models, names, event, td)
        dr = dose_response(cars)
        if dr is not None:
            out.append((td, dr["spearman"], dr["slope"], dr["slope_t"]))
    return out


def abnormal_path_td(rets, mkt, models, name, event, ntd=None, until=None):
    """Cumulative abnormal return (%) as a daily path, trading-day aligned.

    `until` truncates the path just before a date — use the episode's de-escalation
    so decay isn't confounded with the market repricing a peace headline.
    """
    if name not in models:
        return None
    days = trading_days_from(rets.index, event, ntd)
    if until is not None:
        days = days[days < pd.Timestamp(until)]
    ar = abnormal_series(rets, mkt, models[name], name, days)
    if ar is None or not len(ar):
        return None
    return ar.cumsum() * 100


def episode_profile(rets, mkt, models, name, episode, ntd=None):
    """Shape of one asset's abnormal move within one episode.

    Measured on the CLEAN window (shock -> day before de-escalation), so 'decay' means
    the market unwinding on its own rather than reacting to peace news.

    Returns dict: peak %, trading day of peak, days to 50%/90% of peak, level at the
    end of the clean window, share of peak retained there, and the latest level
    including any post-de-escalation sessions.
    """
    clean = abnormal_path_td(rets, mkt, models, name, episode["shock"], ntd,
                             until=episode["deescalation"])
    if clean is None or not len(clean):
        return None
    vals = clean.values
    pk_i = int(np.argmax(np.abs(vals)))
    peak = vals[pk_i]
    sgn = np.sign(peak) or 1.0

    def _first_at(frac):
        hits = np.where(sgn * vals >= frac * abs(peak))[0]
        return int(hits[0] + 1) if len(hits) else None

    full = abnormal_path_td(rets, mkt, models, name, episode["shock"], ntd)
    return {
        "asset": name,
        "episode": episode["key"],
        "peak": peak,
        "peak_td": pk_i + 1,
        "peak_date": clean.index[pk_i],
        "td_to_50": _first_at(0.5),
        "td_to_90": _first_at(0.9),
        "clean_end": vals[-1],
        "clean_td": len(vals),
        "retained_pct": vals[-1] / peak * 100 if peak else None,
        "latest": full.values[-1] if full is not None and len(full) else None,
        "latest_td": len(full) if full is not None else None,
        "path": clean,
    }


def episode_trading_days(rets, episode):
    """(sessions elapsed since the shock, sessions in the clean pre-de-escalation window)."""
    total = len(trading_days_from(rets.index, episode["shock"]))
    days = trading_days_from(rets.index, episode["shock"])
    clean = len(days[days < pd.Timestamp(episode["deescalation"])])
    return total, clean


def comparable_horizon(rets, episodes=None):
    """Longest trading-day horizon every episode can support in its clean window.

    Guards the side-by-side comparison: Round 2 has far less history than Round 1, so
    both must be truncated to the shorter one before any 'faster or slower' claim.
    """
    eps = episodes or EPISODES
    return min(episode_trading_days(rets, e)[1] for e in eps)


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


def phase_segments(today):
    """PHASES turned into consecutive (label, start, end, type) windows, last one open to today."""
    out = []
    for i, (label, dt, kind) in enumerate(PHASES):
        end = PHASES[i + 1][1] if i + 1 < len(PHASES) else today
        out.append((label, dt, end, kind))
    return out


def phase_table(rets, mkt, models, names, today=None):
    """Abnormal move per asset within every phase of the war.

    Replaces the old fixed war/peace/relapse split, which lumped everything after
    May 7 into one bucket and so blended the June peace MoU with the July restart.
    """
    today = today if today is not None else rets.index.max()
    segs = phase_segments(today)
    rows = []
    for name in names:
        if name not in models or name not in rets.columns:
            continue
        row = {"asset": name}
        for label, start, end, _ in segs:
            r = car(rets[name], mkt, models[name], start, end)
            row[label] = r[0] if r else None
        rows.append(row)
    return rows, [s[0] for s in segs]


def reversion_table(rets, mkt, models, names, episode=None):
    """Per-asset shock -> resolution reversion for one episode.

    `war` is the abnormal move from the shock to its de-escalation; `peace` is what
    happened after that until the next shock (or today); `pct_reversed` is how much of
    the war move the resolution undid. Defaults to Round 1 for backward compatibility.
    """
    ep = episode or EPISODES[0]
    today = rets.index.max()
    shock, deesc = ep["shock"], ep["deescalation"]
    # Peace runs until the next shock in the chronology, else to today.
    later_shocks = [d for _, d, k in PHASES if k == "shock" and d > deesc]
    peace_end = min(later_shocks) if later_shocks else today

    rows = []
    for name in names:
        if name not in models or name not in rets.columns:
            continue
        ar_series = rets[name]
        war = car(ar_series, mkt, models[name], shock, deesc)
        peace = car(ar_series, mkt, models[name], deesc, peace_end)
        if war is None:
            continue
        war_c = war[0]
        peace_c = peace[0] if peace else None
        pct_reversed = (-peace_c / war_c * 100) if (peace_c is not None and war_c != 0) else None
        rows.append({
            "asset": name,
            "episode": ep["key"],
            "war": war_c,
            "peace": peace_c,
            "pct_reversed": pct_reversed,
            "half_life": _half_life(ar_series, mkt, models[name], war_c, deesc, peace_end),
        })
    return rows


def _half_life(asset_ret, mkt, model, war_c, deesc, peace_end):
    """Trading days after the de-escalation for the abnormal level to revert halfway to baseline."""
    if war_c == 0:
        return None
    alpha, beta, _ = model
    mask = (asset_ret.index >= pd.Timestamp(deesc)) & (asset_ret.index <= pd.Timestamp(peace_end))
    ar = (asset_ret[mask] - (alpha + beta * mkt[mask])).dropna()
    if len(ar) == 0:
        return None
    cum = ar.cumsum() * 100            # cumulative abnormal level during peace
    target = -0.5 * war_c              # halfway back toward zero
    crossed = (cum <= target) if war_c > 0 else (cum >= target)
    hits = np.where(crossed.values)[0]
    return int(hits[0] + 1) if len(hits) else None
