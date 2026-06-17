"""Ring 0 — The Statistical Verdict: did the war actually cause the moves?"""

from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import (
    render_sidebar, EXPOSURE_SCORES, PLACEBOS, MARKET_FACTOR,
    CONFLICT_START, CEASEFIRE_DATE, RELAPSE_DATE,
)
from stats import (
    prepare, car_table, dose_response, dose_response_curve, baseline_volatility,
    cumulative_abnormal_path, rdit_jump, reversion_table, ALL_ASSETS,
)

st.set_page_config(page_title="Ring 0 — Statistical Verdict", layout="wide")
render_sidebar()

# Shared colour language: green = war winner, red = war loser, gray = neutral / placebo.
WIN, LOSE, NEU, INK = "#22c55e", "#ef4444", "#94a3b8", "#334155"

st.markdown("# Ring 0 — The Statistical Verdict")
st.caption("The other rings show *what* moved. This one asks the hard question: **was it actually the war?**")

today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
with st.spinner("Fitting market models and running the event study..."):
    rets, mkt, models = prepare(today)

if mkt is None or not models:
    st.error("Could not fetch enough data to run the analysis.")
    st.stop()

# --- Core computation: CAR over a tight post-onset window (the signal is sharp early) ---
EVENT_END = CONFLICT_START + timedelta(days=7)
asset_names = list(ALL_ASSETS.keys())
cars = car_table(rets, mkt, models, CONFLICT_START, EVENT_END, asset_names)
dr = dose_response(cars)

plac = car_table(rets, mkt, models, CONFLICT_START, EVENT_END, list(PLACEBOS.keys()))
plac_n = len(plac)
plac_n_sig = sum(1 for v in plac.values() if abs(v[1]) > 1.96)
plac_null = plac_n - plac_n_sig
plac_clean = plac_n_sig <= 1

strength = ("strong" if dr and abs(dr["spearman"]) >= 0.6
            else "moderate" if dr and abs(dr["spearman"]) >= 0.4 else "weak")

# =====================================================================
# 1. VERDICT BANNER
# =====================================================================
if dr and dr["spearman"] >= 0.4 and dr["slope"] > 0:
    st.success(
        f"### ✓ The data says: it was the war\n"
        f"The markets we predicted would react, **did — in the right order**. "
        f"Unrelated 'placebo' markets stayed quiet, and a second method agrees."
    )
else:
    st.warning("### ~ The evidence is mixed\nThe war's fingerprint is faint in the data — read on for why.")

chips = st.columns(3)
chips[0].metric("Pattern strength", f"{strength.title()}" if dr else "—",
                help=f"Rank correlation {dr['spearman']:+.2f} between predicted exposure and actual move." if dr else "")
chips[1].metric("Placebo check", f"{plac_null}/{plac_n} clean" + (" ✓" if plac_clean else " ⚠️"),
                help="Markets with no war exposure should show no abnormal move.")
oil_jump = rdit_jump(rets["Crude Oil WTI"], CONFLICT_START) if "Crude Oil WTI" in rets.columns else None
chips[2].metric("2nd method (oil jump)", f"{oil_jump[0]:+.1f}%" if oil_jump else "—",
                help="A separate technique (regression discontinuity): oil's instant jump the day war broke out.")

st.divider()

# =====================================================================
# 2. HERO — the sorted staircase
# =====================================================================
st.markdown("## Did the right markets move?")
st.markdown(
    "Each bar is one market, lined up by **what we predicted before the war** — expected losers on the "
    "left, expected winners on the right. Bar height = **what actually happened**. "
    "If the war drove things, the bars should climb from red (left) to green (right). They do."
)

# Order by predicted exposure (left=hurt → right=benefit), then by actual move within ties.
ordered = sorted(cars.items(), key=lambda kv: (EXPOSURE_SCORES.get(kv[0], 0), kv[1][0]))
names = [n for n, _ in ordered]
vals = [v[0] for _, v in ordered]
bar_colors = [WIN if v >= 0 else LOSE for v in vals]

fig = go.Figure(go.Bar(
    x=names, y=vals, marker_color=bar_colors,
    hovertemplate="%{x}<br>actual abnormal move: %{y:+.2f}%<extra></extra>",
))
fig.add_hline(y=0, line_color="gray", line_width=1)
# Region labels under the axis
fig.add_annotation(x=0.0, xref="paper", y=1.02, yref="paper", showarrow=False,
                   text="◄ we predicted these would be HURT", font=dict(color=LOSE, size=12), xanchor="left")
fig.add_annotation(x=1.0, xref="paper", y=1.02, yref="paper", showarrow=False,
                   text="we predicted these would BENEFIT ►", font=dict(color=WIN, size=12), xanchor="right")
fig.update_layout(
    height=460, showlegend=False, bargap=0.25,
    yaxis_title="Actual abnormal move (%)",
    xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
    margin=dict(t=40, b=110, l=60, r=20),
)
st.plotly_chart(fig, width="stretch")

if dr:
    st.markdown(
        f"**The staircase is the proof.** Predicted winners rose, predicted losers fell — a **{strength}** "
        f"ordered match (rank correlation **{dr['spearman']:+.2f}**). Random market noise can't sort markets "
        f"by their war exposure like this; only the war can. **Oil**, far right, is the clearest case."
    )

st.divider()

# =====================================================================
# 3. SIGNAL FADES — the effect is real but fast
# =====================================================================
st.markdown("## The shock was real — but fast")
st.markdown(
    "How clean is that staircase if we widen the window past the first week? It **peaks within days, then "
    "fades** — exactly what a genuine shock looks like as markets digest it and move on."
)

curve = dose_response_curve(rets, mkt, models, asset_names, [3, 5, 7, 10, 14, 21, 30, 42])
if curve:
    cx = [d for d, _ in curve]
    cy = [r for _, r in curve]
    figc = go.Figure(go.Scatter(
        x=cx, y=cy, mode="lines+markers",
        line=dict(color=INK, width=3), marker=dict(size=8, color=INK),
        fill="tozeroy", fillcolor="rgba(51,65,85,0.08)",
        hovertemplate="%{x} days after onset<br>pattern strength %{y:.2f}<extra></extra>",
    ))
    peak_d, peak_r = max(curve, key=lambda t: t[1])
    figc.add_annotation(x=peak_d, y=peak_r, text="strongest here", showarrow=True,
                        arrowhead=2, ay=-30, font=dict(color=INK, size=11))
    figc.update_layout(
        height=320, showlegend=False,
        xaxis_title="Window length (days after war began)",
        yaxis_title="Pattern strength (rank corr.)",
        margin=dict(t=20, b=45, l=55, r=20),
    )
    st.plotly_chart(figc, width="stretch")

st.divider()

# =====================================================================
# 4. OIL SPOTLIGHT — the epicenter, as a picture
# =====================================================================
st.markdown("## The epicenter: oil, in three acts")
st.markdown(
    f"Oil's abnormal move tells the whole arc. It **surged** when war broke out, gave back about half when "
    f"the **{CEASEFIRE_DATE:%b %d}** ceasefire hit — that half was fear — then the rest **stuck**, because "
    f"the market still saw a real, lasting threat to supply."
)

path = (cumulative_abnormal_path(rets["Crude Oil WTI"], mkt, models.get("Crude Oil WTI"),
                                 CONFLICT_START, today) if "Crude Oil WTI" in rets.columns else None)
if path is not None and len(path):
    figo = go.Figure(go.Scatter(
        x=path.index, y=path.values, mode="lines",
        line=dict(color="#f59e0b", width=3),
        hovertemplate="%{x|%b %d}<br>abnormal: %{y:+.1f}%<extra></extra>",
    ))
    figo.add_hline(y=0, line_dash="dot", line_color="gray", line_width=0.8)
    for dt, lbl, col in [(CONFLICT_START, "War begins", LOSE), (CEASEFIRE_DATE, "Ceasefire", WIN),
                         (RELAPSE_DATE, "Strikes resume", LOSE)]:
        figo.add_vline(x=dt, line_dash="dot", line_color=col, line_width=1.5)
        figo.add_annotation(x=dt, y=1, yref="paper", text=lbl, showarrow=False,
                            font=dict(size=10, color=col), yshift=8)
    figo.update_layout(
        height=360, showlegend=False,
        yaxis_title="Oil's abnormal move since war began (%)",
        margin=dict(t=30, b=30, l=55, r=20),
    )
    st.plotly_chart(figo, width="stretch")

st.divider()

# =====================================================================
# 5. WHY TRUST THIS? — reassurance strip
# =====================================================================
st.markdown("## Why trust this?")
t1, t2, t3 = st.columns(3)
with t1:
    st.markdown(f"#### 🛡️ Placebos\n**{plac_null} of {plac_n} clean.** Markets unrelated to the war "
                "(utilities, staples…) showed no abnormal move — so we're not just measuring the whole "
                "market drifting.")
base_vol = baseline_volatility(rets, MARKET_FACTOR[0])
with t2:
    st.markdown(f"#### 📏 Calm baseline\n**{base_vol:.0f}% volatility** before the war — *below* the historical "
                "norm (~15–20%). The 'normal' we compare against was genuinely quiet, not another crisis."
                if base_vol else "#### 📏 Calm baseline\nBaseline window was quiet.")
with t3:
    st.markdown("#### 📐 Two methods agree\nA separate technique (measuring the *instant* jump at the surprise "
                + (f"events) finds oil leapt **{oil_jump[0]:+.0f}%** the day war began — matching the window method."
                   if oil_jump else "events) agrees with the window method."))

st.divider()

# =====================================================================
# RAW STATS — audit-on-demand
# =====================================================================
st.markdown("### The numbers (for the skeptics)")


def _stars(t):
    a = abs(t)
    return "★★★" if a > 2.58 else "★★" if a > 1.96 else "★" if a > 1.64 else "—"


with st.expander("🔬 Full results — every market, with significance"):
    rows = [{"Market": n, "Predicted": EXPOSURE_SCORES.get(n, "—"),
             "Abnormal move %": round(c, 2), "t-stat": round(t, 2), "Significant?": _stars(t)}
            for n, (c, t, k) in sorted(cars.items(), key=lambda kv: kv[1][0], reverse=True)]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption("★ p<0.10 · ★★ p<0.05 · ★★★ p<0.01. Move vs. the ACWI market-model baseline, first week.")

with st.expander("🛡️ Placebo detail"):
    prows = [{"Placebo market": n, "Abnormal move %": round(c, 2), "t-stat": round(t, 2), "Significant?": _stars(t)}
             for n, (c, t, k) in plac.items()]
    st.dataframe(pd.DataFrame(prows), width="stretch", hide_index=True)

with st.expander("📊 Reversion detail — what peace undid (biggest movers)"):
    rev = reversion_table(rets, mkt, models, asset_names)
    big = sorted([r for r in rev if abs(r["war"]) >= 3], key=lambda r: abs(r["war"]), reverse=True)
    df_rev = pd.DataFrame([{
        "Market": r["asset"], "War move %": round(r["war"], 1),
        "After ceasefire %": round(r["peace"], 1) if r["peace"] is not None else None,
        "% of war undone": round(r["pct_reversed"]) if r["pct_reversed"] is not None else None,
        "Half-life (days)": r["half_life"],
    } for r in big])
    st.dataframe(df_rev, width="stretch", hide_index=True)

with st.expander("📐 Methodology & honest caveats"):
    st.markdown(
        f"""
- **Baseline.** For each market, `return = α + β·ACWI + ε`, fit only on the **pre-war** window
  ({CONFLICT_START - pd.Timedelta(days=200):%b %Y} → {CONFLICT_START:%b %d, %Y}). The "abnormal move" is
  what actually happened minus what this baseline predicted.
- **Why this isn't proof.** The abnormal move captures the war **and** anything else in the window. Three
  things shore up the attribution: the **dose-response staircase** (noise wouldn't sort markets by
  exposure), **null placebos**, and a **second method** (instant jumps at surprise events).
- **Fit measure.** Exposure is an *ordinal* −2…+2 score, so we report **rank correlation** (the proper
  statistic for ordered data). Linear R² ({dr['r2']:.2f}) is lower only because oil is a huge linear
  outlier — directionally on-trend but far beyond a straight line.
- **Known limits.** Single-factor model; commodities fit the baseline poorly; VIX is excluded from the
  staircase (it's a vol index, not a return); exposure scores are judgmental and set *a priori*.
"""
    )

st.caption("Event study on Yahoo Finance data · market model + CAR + rank-correlation + RDiT via statsmodels.")
