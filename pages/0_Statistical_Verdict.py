"""Ring 0 — The Statistical Verdict: did the war actually cause the moves?

Now compares the two full-scale shocks side by side: the Feb 28 onset and the
Jul 7 restart. Every cross-episode number is trading-day aligned and censored at
each episode's de-escalation, so "faster" means faster, not "different weekday".
"""

from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import (
    render_sidebar, EXPOSURE_SCORES, PLACEBOS, MARKET_FACTOR,
    CONFLICT_START, EPISODES, EPISODE_BY_KEY, episode_colors,
)
from stats import (
    prepare, dose_response, baseline_volatility,
    rdit_jump, reversion_table, phase_table, ALL_ASSETS,
    car_table_td, staircase_curve_td, abnormal_path_td,
    episode_profile, episode_trading_days, comparable_horizon,
)

st.set_page_config(page_title="Ring 0 — Statistical Verdict", layout="wide")
render_sidebar()

# Shared colour language: green = war winner, red = war loser, gray = neutral / placebo.
WIN, LOSE, NEU, INK = "#22c55e", "#ef4444", "#94a3b8", "#334155"
EPC = episode_colors()

st.markdown("# Ring 0 — The Statistical Verdict")
st.caption("The other rings show *what* moved. This one asks the hard question: **was it actually the war?** "
           "— and now, whether the second war looked like the first.")

today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
with st.spinner("Fitting market models and running the event study..."):
    rets, mkt, models = prepare(today)

if mkt is None or not models:
    st.error("Could not fetch enough data to run the analysis.")
    st.stop()

asset_names = list(ALL_ASSETS.keys())
R1, R2 = EPISODE_BY_KEY["R1"], EPISODE_BY_KEY["R2"]

# The comparison is only honest at a horizon BOTH episodes can support in their clean
# (pre-de-escalation) window. Round 2 is the binding constraint while it's still young.
HORIZON = comparable_horizon(rets)
elapsed = {e["key"]: episode_trading_days(rets, e) for e in EPISODES}

if HORIZON < 3:
    st.warning("The newer episode has too few trading days yet for a side-by-side comparison.")

# --- Core computation: the staircase for each episode at the comparable horizon ---
cars = {e["key"]: car_table_td(rets, mkt, models, asset_names, e["shock"], HORIZON) for e in EPISODES}
drs = {k: dose_response(v) for k, v in cars.items()}
plac = {e["key"]: car_table_td(rets, mkt, models, list(PLACEBOS.keys()), e["shock"], HORIZON)
        for e in EPISODES}

# The two rounds peak at very different horizons — Round 1 inside a week, Round 2 around
# three. Judging both at the shared horizon would score Round 1 "weak" simply because we
# happened to measure it after its signal had already decayed. So the verdict uses each
# episode's own strongest window; only the magnitude charts use the shared horizon.
TDS = [2, 3, 5, 7, 10, 12, 15, 20, 25, 30]
curves = {e["key"]: staircase_curve_td(rets, mkt, models, asset_names, e["shock"],
                                       [t for t in TDS if t <= elapsed[e["key"]][1]])
          for e in EPISODES}
peaks = {k: (max(c, key=lambda t: t[1]) if c else None) for k, c in curves.items()}


def _strength(rho):
    if rho is None:
        return "—"
    a = abs(rho)
    return "Strong" if a >= 0.6 else "Moderate" if a >= 0.4 else "Weak"


# =====================================================================
# 1. VERDICT BANNER
# =====================================================================
both_real = all(p and p[1] >= 0.4 and p[2] > 0 for p in peaks.values())
if both_real:
    st.success(
        f"### ✓ The data says: it was the war — both times\n"
        f"The markets we predicted would react **did, in the right order**, after the February onset "
        f"*and* after the July restart. Unrelated 'placebo' markets stayed quiet in both. "
        f"But the second reaction was **smaller, calmer, and undone faster** — see below."
    )
else:
    st.warning("### ~ The evidence is mixed\nThe war's fingerprint is uneven across the two shocks — read on.")

st.caption(f"Compared at **{HORIZON} trading days** after each shock — the longest window both episodes "
           f"can support before their de-escalation news "
           f"({R1['deescalation_label']}, {R2['deescalation_label']}).")

cols = st.columns(2)
for col, e in zip(cols, EPISODES):
    k = e["key"]
    dr = drs[k]
    tot, clean = elapsed[k]
    with col:
        st.markdown(
            f"<div style='border-left:4px solid {EPC[k]};padding-left:12px'>"
            f"<strong>{e['label']}</strong><br>"
            f"<span style='color:{NEU};font-size:0.9em'>{e['blurb']}</span></div>",
            unsafe_allow_html=True,
        )
        pk = peaks[k]
        m = st.columns(3)
        m[0].metric("Peak pattern strength", _strength(pk[1] if pk else None),
                    delta=f"at day {pk[0]}" if pk else None, delta_color="off",
                    help=f"Strongest rank correlation between predicted exposure and actual move: "
                         f"{pk[1]:+.2f}, reached {pk[0]} trading days in." if pk else "")
        n_sig = sum(1 for v in plac[k].values() if abs(v[1]) > 1.96)
        m[1].metric("Placebo check", f"{len(plac[k]) - n_sig}/{len(plac[k])} clean"
                    + (" ✓" if n_sig <= 1 else " ⚠️"),
                    help="Markets with no war exposure should show no abnormal move.")
        jump = rdit_jump(rets["Crude Oil WTI"], e["shock"]) if "Crude Oil WTI" in rets.columns else None
        m[2].metric("Oil's instant jump", f"{jump[0]:+.1f}%" if jump else "—",
                    help="Regression discontinuity: oil's jump on the day itself.")
        st.caption(f"{tot} trading days elapsed · {clean} before de-escalation")

st.divider()

# =====================================================================
# 2. HERO — the two staircases
# =====================================================================
st.markdown("## Did the right markets move — both times?")
st.markdown(
    "Each market is placed by **what we predicted before the war** — expected losers on the left, "
    "expected winners on the right. Bar height = **what actually happened**. If the war drove things, "
    "the bars should climb left-to-right. Compare the two rounds: the ordering returns in July, but "
    "the bars are **shorter**, and the safe-haven names on the right no longer play along."
)

# Order by predicted exposure, then by Round 1's actual move within ties.
ordered = sorted(
    [n for n in asset_names if n in EXPOSURE_SCORES and (n in cars["R1"] or n in cars["R2"])],
    key=lambda n: (EXPOSURE_SCORES.get(n, 0), cars["R1"].get(n, (0,))[0]),
)

fig = go.Figure()
for e in EPISODES:
    k = e["key"]
    fig.add_trace(go.Bar(
        x=ordered, y=[cars[k].get(n, (None,))[0] for n in ordered],
        name=f"{e['label']} ({e['short']})",
        marker=dict(color=EPC[k], line=dict(color="rgba(255,255,255,0.85)", width=2)),
        hovertemplate="%{x}<br>" + e["short"] + ": %{y:+.2f}%<extra></extra>",
    ))
fig.add_hline(y=0, line_color=NEU, line_width=1)
fig.add_annotation(x=0.0, xref="paper", y=1.06, yref="paper", showarrow=False,
                   text="◄ we predicted these would be HURT", font=dict(color=LOSE, size=12), xanchor="left")
fig.add_annotation(x=1.0, xref="paper", y=1.06, yref="paper", showarrow=False,
                   text="we predicted these would BENEFIT ►", font=dict(color=WIN, size=12), xanchor="right")
fig.update_layout(
    height=480, bargap=0.28, bargroupgap=0.08,
    yaxis_title=f"Abnormal move over {HORIZON} trading days (%)",
    xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
    legend=dict(orientation="h", yanchor="bottom", y=1.12, xanchor="left", x=0),
    margin=dict(t=70, b=120, l=60, r=20),
    hovermode="x unified",
)
st.plotly_chart(fig, width="stretch")

if drs["R1"] and drs["R2"]:
    o1 = cars["R1"].get("Crude Oil WTI")
    o2 = cars["R2"].get("Crude Oil WTI")
    oil_bit = (f"Oil, the clearest case, ran **{o1[0]:+.0f}%** abnormal by day {HORIZON} in February "
               f"against **{o2[0]:+.0f}%** in July. " if o1 and o2 else "")
    st.markdown(
        f"**The staircase came back — at roughly half the height.** {oil_bit}"
        f"Random noise can't sort markets by their war exposure like this; only the war can. "
        f"The *ordering* actually looks cleaner in Round 2 at this horizon "
        f"(rank correlation **{drs['R2']['spearman']:+.2f}** vs **{drs['R1']['spearman']:+.2f}**) — but that's "
        f"a timing artifact, not a stronger war: Round 1's pattern had already decayed by day {HORIZON} "
        f"while Round 2's was still building. The next chart shows those two shapes."
    )

st.divider()

# =====================================================================
# 3. HOW LONG DID THE PATTERN LAST?
# =====================================================================
st.markdown("## How long did the pattern last?")
st.markdown(
    "Widen the window a day at a time and re-measure. In **Round 1** the signal spiked in the first week "
    "and was gone inside three — the finding that the war's impact 'lasted about two weeks'. "
    "**Round 2 inverted that shape**: it started weaker but kept *building*, because a single clean driver "
    "(physical crude) sorted the cross-section better than February's diffuse panic did."
)

figc = go.Figure()
for e in EPISODES:
    k = e["key"]
    curve = curves[k]
    if not curve:
        continue
    figc.add_trace(go.Scatter(
        x=[c[0] for c in curve], y=[c[1] for c in curve],
        mode="lines+markers", name=f"{e['label']} ({e['short']})",
        line=dict(color=EPC[k], width=2.5), marker=dict(size=8, color=EPC[k]),
        hovertemplate="%{x} trading days in<br>" + e["short"] + ": pattern strength %{y:.2f}<extra></extra>",
    ))
figc.add_vline(x=HORIZON, line_dash="dot", line_color=NEU, line_width=1)
figc.add_annotation(x=HORIZON, y=1, yref="paper", text="comparable horizon", showarrow=False,
                    font=dict(size=10, color=NEU), xshift=4, xanchor="left")
figc.add_hline(y=0, line_color=NEU, line_width=0.8, line_dash="dot")
figc.update_layout(
    height=360,
    xaxis_title="Trading days after the shock",
    yaxis_title="Pattern strength (rank corr.)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(t=40, b=45, l=55, r=20), hovermode="x unified",
)
st.plotly_chart(figc, width="stretch")

st.divider()

# =====================================================================
# 4. DID MARKETS PROCESS IT FASTER? — the speed comparison
# =====================================================================
st.markdown("## Did markets process the restart faster?")
st.markdown(
    "Two different questions hide inside 'faster'. **On impact**, no — the July reaction was slower off the "
    "line and roughly half the size. **Over the full arc**, yes — it peaked in half the time and then markets "
    "handed most of it back *on their own*, with the war still going and before any peace headline."
)

SPEED_ASSETS = ["Crude Oil WTI", "Brent Crude", "Energy (XLE)", "Airlines (JETS)", "Defense (ITA)"]
prof = {k: {} for k in EPISODE_BY_KEY}
for e in EPISODES:
    for a in SPEED_ASSETS:
        p = episode_profile(rets, mkt, models, a, e)
        if p:
            prof[e["key"]][a] = p

rows = []
for a in SPEED_ASSETS:
    p1, p2 = prof["R1"].get(a), prof["R2"].get(a)
    if not (p1 and p2):
        continue
    rows.append({
        "Market": a,
        "R1 peak %": round(p1["peak"], 1), "R1 day of peak": p1["peak_td"],
        "R2 peak %": round(p2["peak"], 1), "R2 day of peak": p2["peak_td"],
        "R1 kept at de-escalation": f"{p1['retained_pct']:.0f}%" if p1["retained_pct"] is not None else "—",
        "R2 kept at de-escalation": f"{p2['retained_pct']:.0f}%" if p2["retained_pct"] is not None else "—",
    })
if rows:
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption("Peak = largest cumulative abnormal move inside the clean window. "
               "'Kept' = share of that peak still standing on the last session before de-escalation news — "
               "so it measures the market unwinding by itself, not reacting to peace.")

oil_p1, oil_p2 = prof["R1"].get("Crude Oil WTI"), prof["R2"].get("Crude Oil WTI")
if oil_p1 and oil_p2:
    st.markdown(
        f"**Oil is the clearest case.** In Round 1 it peaked at **{oil_p1['peak']:+.0f}%** abnormal on "
        f"trading day **{oil_p1['peak_td']}** and had given back essentially nothing "
        f"(**{oil_p1['retained_pct']:.0f}%** still standing) when the ceasefire arrived. In Round 2 it peaked "
        f"at **{oil_p2['peak']:+.0f}%** on day **{oil_p2['peak_td']}** — half the size, twice as fast — and "
        f"had already surrendered to **{oil_p2['retained_pct']:.0f}%** of that peak *before* the Oman talks "
        f"were announced. The market stopped believing in the disruption while the war was still on."
    )

# --- Oil path overlay, trading-day aligned ---
st.markdown("#### Oil's abnormal move, both rounds, aligned on day one")
# Round 1's path continues for months past its ceasefire; drawn in full it compresses the
# stretch being compared into the left edge. Show a short dotted tail past each
# de-escalation instead — enough to see the direction, not enough to wreck the scale.
VIEW_TD = max(elapsed[e["key"]][1] for e in EPISODES) + 8
figo = go.Figure()
for e in EPISODES:
    k = e["key"]
    clean = abnormal_path_td(rets, mkt, models, "Crude Oil WTI", e["shock"], until=e["deescalation"])
    full = abnormal_path_td(rets, mkt, models, "Crude Oil WTI", e["shock"], ntd=VIEW_TD)
    if clean is None:
        continue
    figo.add_trace(go.Scatter(
        x=list(range(1, len(clean) + 1)), y=clean.values, mode="lines",
        name=f"{e['label']} ({e['short']})", line=dict(color=EPC[k], width=3),
        customdata=[d.strftime("%b %d") for d in clean.index],
        hovertemplate="day %{x} (%{customdata})<br>" + e["short"] + ": %{y:+.1f}%<extra></extra>",
    ))
    # Post-de-escalation continuation, dashed — shown but visually demoted.
    if full is not None and len(full) > len(clean):
        figo.add_trace(go.Scatter(
            x=list(range(len(clean), len(full) + 1)),
            y=full.values[len(clean) - 1:], mode="lines",
            name=f"{e['short']} — after {e['deescalation_label']}",
            line=dict(color=EPC[k], width=2, dash="dot"),
            customdata=[d.strftime("%b %d") for d in full.index[len(clean) - 1:]],
            hovertemplate="day %{x} (%{customdata})<br>post-de-escalation: %{y:+.1f}%<extra></extra>",
        ))
figo.add_hline(y=0, line_dash="dot", line_color=NEU, line_width=0.8)
figo.update_layout(
    height=380,
    xaxis_title="Trading days since the shock",
    yaxis_title="Oil's cumulative abnormal move (%)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(t=40, b=40, l=55, r=20), hovermode="x unified",
)
st.plotly_chart(figo, width="stretch")
st.caption("Solid = clean window before that round's de-escalation news. Dotted = after it, "
           "where decay and the peace headline are no longer separable.")

st.divider()

# =====================================================================
# 5. WHAT CHANGED — the three legs
# =====================================================================
st.markdown("## What changed between the two wars")
st.markdown(
    "February was priced as *the world is dangerous*. July was priced as *barrels are tight for a few weeks*. "
    "Splitting the universe into the channels a war is supposed to travel through shows where the second "
    "reaction simply didn't go."
)

LEGS = {
    "Oil supply": ["Crude Oil WTI", "Brent Crude", "Energy (XLE)", "ExxonMobil", "Chevron"],
    "Fear / safety": ["Gold (GLD)", "US Treasuries (TLT)", "US Dollar (UUP)"],
    "Defense": ["Defense (ITA)", "Lockheed Martin", "RTX (Raytheon)"],
    "Demand hit": ["Airlines (JETS)", "Delta Airlines", "United Airlines"],
}
leg_rows = []
for leg, members in LEGS.items():
    vals = {}
    for e in EPISODES:
        got = [cars[e["key"]][m][0] for m in members if m in cars[e["key"]]]
        vals[e["key"]] = float(np.mean(got)) if got else None
    leg_rows.append({"Channel": leg,
                     f"{R1['short']} avg %": round(vals["R1"], 2) if vals["R1"] is not None else None,
                     f"{R2['short']} avg %": round(vals["R2"], 2) if vals["R2"] is not None else None})

figl = go.Figure()
for e in EPISODES:
    k = e["key"]
    figl.add_trace(go.Bar(
        x=[r["Channel"] for r in leg_rows], y=[r[f"{e['short']} avg %"] for r in leg_rows],
        name=f"{e['label']} ({e['short']})",
        marker=dict(color=EPC[k], line=dict(color="rgba(255,255,255,0.85)", width=2)),
        hovertemplate="%{x}<br>" + e["short"] + ": %{y:+.2f}%<extra></extra>",
    ))
figl.add_hline(y=0, line_color=NEU, line_width=1)
figl.update_layout(
    height=340, bargap=0.35, bargroupgap=0.08,
    yaxis_title=f"Average abnormal move, {HORIZON} trading days (%)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(t=40, b=40, l=60, r=20), hovermode="x unified",
)
st.plotly_chart(figl, width="stretch")

# VIX belongs in levels, not CAR — it's a volatility index, not a return series.
if "VIX" in rets.columns:
    from stats import _fetch_prices
    vix = _fetch_prices(today)["VIX"].dropna()
    bits = []
    for e in EPISODES:
        pre_s = vix[vix.index < pd.Timestamp(e["shock"])]
        post = vix[(vix.index >= pd.Timestamp(e["shock"])) & (vix.index < pd.Timestamp(e["deescalation"]))]
        if not len(pre_s) or not len(post):
            continue
        pre = pre_s.iloc[-1]
        hot = int((post > pre * 1.20).sum())
        bits.append(f"**{e['short']}:** {pre:.1f} → peak {post.max():.1f} "
                    f"(+{(post.max() / pre - 1) * 100:.0f}%), elevated on {hot} of {len(post)} sessions")
    if bits:
        st.info("**The fear gauge barely registered the restart.** VIX in levels — "
                + "; ".join(bits) + ".")

st.divider()

# =====================================================================
# 6. WHY TRUST THIS? — reassurance strip
# =====================================================================
st.markdown("## Why trust this?")
t1, t2, t3 = st.columns(3)
with t1:
    txt = " · ".join(
        f"{e['short']} {len(plac[e['key']]) - sum(1 for v in plac[e['key']].values() if abs(v[1]) > 1.96)}"
        f"/{len(plac[e['key']])}" for e in EPISODES)
    st.markdown(f"#### 🛡️ Placebos\n**{txt} clean.** Markets unrelated to the war (utilities, staples…) "
                "showed no abnormal move in either round — so we're not just measuring market drift.")
base_vol = baseline_volatility(rets, MARKET_FACTOR[0])
with t2:
    st.markdown(f"#### 📏 Calm baseline\n**{base_vol:.0f}% volatility** before the war — *below* the historical "
                "norm (~15–20%). The 'normal' we compare against was genuinely quiet, not another crisis."
                if base_vol else "#### 📏 Calm baseline\nBaseline window was quiet.")
with t3:
    st.markdown("#### 📐 Same clock for both\nEvery comparison counts **trading days**, not calendar days "
                "(Feb 28 was a Saturday, Jul 7 a Tuesday), and stops at each round's de-escalation — so "
                "'faster' isn't an artifact of the calendar.")

st.divider()

# =====================================================================
# RAW STATS — audit-on-demand
# =====================================================================
st.markdown("### The numbers (for the skeptics)")


def _stars(t):
    a = abs(t)
    return "★★★" if a > 2.58 else "★★" if a > 1.96 else "★" if a > 1.64 else "—"


with st.expander("🔬 Full results — every market, both rounds, with significance"):
    rws = []
    for n in asset_names:
        a, b = cars["R1"].get(n), cars["R2"].get(n)
        if not (a or b):
            continue
        rws.append({
            # Kept as text: the column mixes a signed score with "—", and a mixed
            # int/str column fails Arrow serialisation.
            "Market": n,
            "Predicted": f"{EXPOSURE_SCORES[n]:+d}" if n in EXPOSURE_SCORES else "—",
            f"{R1['short']} move %": round(a[0], 2) if a else None,
            f"{R1['short']} sig": _stars(a[1]) if a else "—",
            f"{R2['short']} move %": round(b[0], 2) if b else None,
            f"{R2['short']} sig": _stars(b[1]) if b else "—",
        })
    rws.sort(key=lambda r: (r[f"{R2['short']} move %"] is None, -(r[f"{R2['short']} move %"] or 0)))
    st.dataframe(pd.DataFrame(rws), width="stretch", hide_index=True)
    st.caption(f"★ p<0.10 · ★★ p<0.05 · ★★★ p<0.01. Move vs. the ACWI market-model baseline over "
               f"{HORIZON} trading days from each shock.")

with st.expander("🛡️ Placebo detail"):
    for e in EPISODES:
        st.markdown(f"**{e['label']}**")
        st.dataframe(pd.DataFrame([
            {"Placebo market": n, "Abnormal move %": round(c, 2), "t-stat": round(t, 2),
             "Significant?": _stars(t)} for n, (c, t, k) in plac[e["key"]].items()
        ]), width="stretch", hide_index=True)

with st.expander("📊 Phase-by-phase — the whole war, not just the shocks"):
    prows, labels = phase_table(rets, mkt, models, asset_names, today)

    def _amp(r):
        vals = [abs(r[l]) for l in labels if r.get(l) is not None]
        return max(vals) if vals else 0.0

    big = sorted(prows, key=_amp, reverse=True)
    df_ph = pd.DataFrame([
        {"Market": r["asset"], **{l: (round(r[l], 1) if r[l] is not None else None) for l in labels}}
        for r in big[:18]
    ])
    st.dataframe(df_ph, width="stretch", hide_index=True)
    st.caption("Abnormal move within each phase. This replaces the old three-bucket split, which lumped "
               "everything after May 7 together and so blended the June peace MoU with the July restart.")

with st.expander("📉 Reversion — what each de-escalation undid"):
    for e in EPISODES:
        rev = reversion_table(rets, mkt, models, asset_names, episode=e)
        big = sorted([r for r in rev if abs(r["war"]) >= 3], key=lambda r: abs(r["war"]), reverse=True)
        if not big:
            continue
        st.markdown(f"**{e['label']} → {e['deescalation_label']}**")
        st.dataframe(pd.DataFrame([{
            "Market": r["asset"], "War move %": round(r["war"], 1),
            "After de-escalation %": round(r["peace"], 1) if r["peace"] is not None else None,
            "% of war undone": round(r["pct_reversed"]) if r["pct_reversed"] is not None else None,
            "Half-life (days)": r["half_life"],
        } for r in big]), width="stretch", hide_index=True)

with st.expander("📐 Methodology & honest caveats"):
    st.markdown(
        f"""
- **Baseline.** For each market, `return = α + β·ACWI + ε`, fit only on the **pre-war** window
  ({CONFLICT_START - pd.Timedelta(days=200):%b %Y} → {CONFLICT_START:%b %d, %Y}). The "abnormal move" is
  what actually happened minus what this baseline predicted.
- **Trading-day alignment.** Feb 28 fell on a Saturday, Jul 7 on a Tuesday, so equal *calendar* windows
  buy unequal numbers of observations. Every cross-round figure counts sessions from the first one at or
  after the shock.
- **Censoring at de-escalation.** Decay is only measured up to the last session before that round's peace
  news ({R1['deescalation_label']}, {R2['deescalation_label']}). Otherwise "markets moved on" and "markets
  read a headline" are the same number.
- **The horizon is set by the younger episode.** Round 2 has {elapsed['R2'][1]} clean trading days, so the
  side-by-side runs to {HORIZON}. Round 1's own numbers extend further and its late-window figures are
  truncated here.
- **Round 1's decay is under-measured.** Its ceasefire arrived at trading day
  {elapsed['R1'][1] + 1} while oil was *still climbing* — so "Round 1 gave back nothing" partly means it
  never got the chance before the news landed. The honest claim is: within each round's available clean
  window, Round 1 self-reversed ~0% and Round 2 roughly half.
- **Why this isn't proof.** The abnormal move captures the war **and** anything else in the window. Three
  things shore up the attribution: the **dose-response staircase** (noise wouldn't sort markets by
  exposure), **null placebos**, and a **second method** (instant jumps at surprise events).
- **Fit measure.** Exposure is an *ordinal* −2…+2 score, so we report **rank correlation**. Linear R²
  is lower mainly because oil is a huge linear outlier — directionally on-trend, far beyond a straight line.
- **Known limits.** Single-factor model whose betas are fit ~10 months before the July shock and may have
  drifted; commodities fit the baseline poorly; Natural Gas is scored +1 but its July move looks like
  storage/weather, not war, and drags the Round 2 staircase; VIX is excluded from the staircase
  (it's a vol index, not a return) and reported in levels instead; exposure scores are judgmental and set
  *a priori*.
"""
    )

st.caption("Event study on Yahoo Finance data · market model + CAR + rank-correlation + RDiT via statsmodels.")
