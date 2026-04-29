"""Ring 1 — The Epicenter: Oil & Energy"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config import (
    render_sidebar, load_data, normalize_to_start, total_change,
    find_conflict_td, pct_change_period, max_drawdown, max_gain, volatility,
    make_chart, add_milestones, color_val, generate_commentary,
    EPICENTER, COLOR_UP, COLOR_DOWN, COLORS,
)

st.set_page_config(page_title="Ring 1 — Oil & Energy", layout="wide")
start_dt, end_dt = render_sidebar()

st.markdown("# Ring 1 — The Epicenter: Oil & Energy")
st.markdown(
    "Iran controls the **Strait of Hormuz** — the narrow waterway through which roughly "
    "**20% of the world's oil** passes daily. Any threat to this chokepoint sends energy prices "
    "surging immediately. This is where the ripple begins."
)

st.divider()

# --- Fetch ---
with st.spinner("Loading energy data..."):
    data = load_data(EPICENTER, start_dt, end_dt)

if data.empty:
    st.error("Could not fetch energy data.")
    st.stop()

conflict_td = find_conflict_td(data)

# --- Price Chart (absolute) ---
st.markdown("## Commodity Prices")
fig_abs = make_chart(data, normalize=False, height=400, start_dt=start_dt, end_dt=end_dt)
if fig_abs:
    st.plotly_chart(fig_abs, width="stretch")

# --- Oil Price Per Barrel ---
if "Crude Oil WTI" in data.columns:
    oil = data["Crude Oil WTI"].dropna()
    if len(oil) >= 2:
        st.markdown("### Oil Price Per Barrel")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("At Start", f"${oil.iloc[0]:.2f}")
        c2.metric("Peak", f"${oil.max():.2f}")
        c3.metric("Latest", f"${oil.iloc[-1]:.2f}")
        chg = ((oil.iloc[-1] - oil.iloc[0]) / oil.iloc[0]) * 100
        c4.metric("Total Change", f"{chg:+.2f}%")

st.divider()

# --- Normalized Comparison ---
st.markdown("## Normalized Comparison (% Change)")
st.caption("Comparing WTI, Brent, and Natural Gas on the same scale — who moved most?")
fig_norm = make_chart(data, normalize=True, height=400, start_dt=start_dt, end_dt=end_dt)
if fig_norm:
    st.plotly_chart(fig_norm, width="stretch")

st.divider()

# --- Data-Driven Commentary ---
st.markdown("## What the Data Says")

# WTI commentary
for cname, exp_reason, ctx in [
    ("Crude Oil WTI",
     "Middle East conflicts threaten supply routes, particularly the Strait of Hormuz, creating immediate upward pressure on prices",
     "WTI is the US benchmark — if the conflict is perceived as contained to the Middle East, WTI may react less than Brent."),
    ("Brent Crude",
     "As the international benchmark, Brent is more sensitive to Middle East supply disruptions than US-produced WTI",
     "A larger move in Brent vs WTI signals the market is pricing in region-specific supply risk rather than global demand changes."),
    ("Natural Gas",
     "Energy supply fears can spill over into natural gas as countries seek alternative fuel sources and LNG demand shifts",
     "Natural gas has its own supply/demand dynamics — weather, storage levels — that can decouple it from oil, so a muted gas reaction suggests the conflict's impact is concentrated in oil markets."),
]:
    if cname in data.columns:
        s = data[cname].dropna()
        st.markdown(f"### {cname}")
        st.markdown(generate_commentary(
            cname, "up", exp_reason, total_change(s),
            extra_context=ctx,
            chg_7d=pct_change_period(s, conflict_td, 7) if conflict_td else None,
            dd=max_drawdown(s),
        ))
        st.markdown("")

st.divider()

# --- WTI vs Brent Spread ---
if "Crude Oil WTI" in data.columns and "Brent Crude" in data.columns:
    st.markdown("## WTI–Brent Spread")
    st.markdown(
        "The spread between WTI and Brent tells you about **regional supply dynamics**. "
        "A widening spread often signals that Middle East disruptions are hitting Brent "
        "(the international benchmark) harder than US-produced WTI."
    )
    spread = data["Brent Crude"] - data["Crude Oil WTI"]
    spread = spread.dropna()
    if len(spread) > 1:
        fig_spread = go.Figure()
        fig_spread.add_trace(go.Scatter(
            x=spread.index, y=spread.values,
            mode="lines", name="Brent − WTI",
            line=dict(width=2.5, color="#f59e0b"),
            fill="tozeroy", fillcolor="rgba(245, 158, 11, 0.1)",
            hovertemplate="%{x|%b %d, %Y}<br>Spread: $%{y:.2f}<extra></extra>",
        ))
        add_milestones(fig_spread, start_dt, end_dt)
        fig_spread.update_layout(
            height=350, margin=dict(t=20, b=30, l=50, r=20),
            yaxis_title="Spread ($/barrel)", hovermode="x unified",
        )
        st.plotly_chart(fig_spread, width="stretch")

        spread_start = spread.iloc[0]
        spread_end = spread.iloc[-1]
        c1, c2 = st.columns(2)
        c1.metric("Spread at Start", f"${spread_start:.2f}")
        c2.metric("Spread Now", f"${spread_end:.2f}")

        # Spread commentary
        spread_chg = spread_end - spread_start
        if spread_chg > 0.5:
            st.info(
                f"The Brent-WTI spread **widened by ${spread_chg:.2f}**. "
                "This suggests the market sees the conflict as a **regional supply disruption** — "
                "Brent (tied to international/Middle East supply) is being hit harder than WTI (US production)."
            )
        elif spread_chg < -0.5:
            st.info(
                f"The Brent-WTI spread **narrowed by ${abs(spread_chg):.2f}**. "
                "This is unusual during a Middle East conflict — it may indicate that US supply concerns "
                "(sanctions, policy) are catching up, or that the Middle East disruption is seen as contained."
            )
        else:
            st.info(
                "The Brent-WTI spread has been **relatively stable**. "
                "The market isn't differentiating strongly between regional and US oil — "
                "suggesting the shock is being priced as a global risk rather than a localized supply issue."
            )

st.divider()

# --- Deep Analysis ---
st.markdown("## Deep Analysis")

metrics = []
for name in EPICENTER:
    if name in data.columns:
        s = data[name].dropna()
        chg_7 = pct_change_period(s, conflict_td, 7) if conflict_td else None
        metrics.append({
            "Commodity": name,
            "Total Change %": total_change(s),
            "7-Day Change %": chg_7,
            "Max Gain %": max_gain(s),
            "Max Drawdown %": max_drawdown(s),
            "Volatility (ann.)": volatility(s),
        })

if metrics:
    mdf = pd.DataFrame(metrics)
    fmt = {c: "{:+.2f}%" for c in mdf.columns if c != "Commodity"}
    fmt["Volatility (ann.)"] = "{:.1f}%"
    st.dataframe(
        mdf.style.format(fmt, na_rep="N/A")
        .map(color_val, subset=[c for c in mdf.columns if "Change" in c or "Gain" in c or "Drawdown" in c]),
        width="stretch", hide_index=True,
    )

st.divider()
st.caption("Ring 1 — The epicenter where the ripple begins.")
