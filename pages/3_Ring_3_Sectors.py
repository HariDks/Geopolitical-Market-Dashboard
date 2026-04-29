"""Ring 3 — Sector Winners & Losers"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from config import (
    render_sidebar, load_data, normalize_to_start, total_change,
    find_conflict_td, pct_change_period, max_drawdown, max_gain, volatility,
    correlation_matrix, make_chart, add_milestones, color_val, generate_commentary,
    SECTORS, COLOR_UP, COLOR_DOWN, COLORS,
)

st.set_page_config(page_title="Ring 3 — Sectors", layout="wide")
start_dt, end_dt = render_sidebar()

st.markdown("# Ring 3 — Sector Winners & Losers")
st.markdown(
    "Within the US market, the conflict creates a clear divergence. "
    "**Energy** and **Defense** benefit directly from higher oil prices and increased military spending. "
    "**Airlines** get crushed by fuel costs. **Tech**, **Financials**, and **Healthcare** show "
    "how far the uncertainty ripple reaches into the broader economy."
)

st.divider()

with st.spinner("Loading sector data..."):
    data = load_data(SECTORS, start_dt, end_dt)

if data.empty:
    st.error("Could not fetch sector data.")
    st.stop()

conflict_td = find_conflict_td(data)
norm = normalize_to_start(data)

# --- Divergence: Winners vs Losers ---
st.markdown("## The Divergence")

winners = []
losers = []
for col in norm.columns:
    final = norm[col].dropna()
    if len(final) > 0 and final.iloc[-1] >= 0:
        winners.append(col)
    else:
        losers.append(col)

col_w, col_l = st.columns(2)

for target_col, names, title, default_color in [
    (col_w, winners, "Winners (positive return)", COLOR_UP),
    (col_l, losers, "Losers (negative return)", COLOR_DOWN),
]:
    with target_col:
        st.markdown(f"### {title}")
        if names:
            fig = go.Figure()
            for i, col in enumerate(names):
                fig.add_trace(go.Scatter(
                    x=norm.index, y=norm[col],
                    mode="lines", name=col,
                    line=dict(width=2.5),
                    hovertemplate=f"{col}<br>" + "%{x|%b %d}<br>%{y:+.2f}%<extra></extra>",
                ))
            add_milestones(fig, start_dt, end_dt)
            fig.add_hline(y=0, line_dash="dot", line_color="gray", line_width=0.8)
            fig.update_layout(
                height=380, margin=dict(t=20, b=30, l=50, r=20),
                yaxis_title="% Change", hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("None in this category for the selected window.")

st.divider()

# --- Data-Driven Sector Commentary ---
st.markdown("## What the Data Says — Sector by Sector")

SECTOR_EXPECTATIONS = {
    "Energy (XLE)": {
        "dir": "up",
        "reason": "Higher oil prices directly boost revenue for energy producers — their costs stay flat while the price of their product surges.",
        "context": "If energy falls despite rising oil, it may signal that the market expects a short-lived spike or fears demand destruction from a broader economic slowdown.",
    },
    "Defense (ITA)": {
        "dir": "up",
        "reason": "Military conflicts drive government defense spending, accelerate existing contracts, and create demand for weapons systems and defense technology.",
        "context": "Defense stocks sometimes lag initially (uncertainty) before rallying (as spending commitments become clear). A decline could signal the market sees de-escalation ahead.",
    },
    "Airlines (JETS)": {
        "dir": "down",
        "reason": "Fuel is 20-30% of airline operating costs. An oil spike crushes margins, and geopolitical fear reduces travel demand.",
        "context": "If airlines held up despite rising oil, it may indicate strong travel demand or effective fuel hedging offsetting the commodity pressure.",
    },
    "Tech (XLK)": {
        "dir": "down",
        "reason": "Tech stocks are growth-sensitive — geopolitical uncertainty raises risk premiums and can trigger a 'risk-off' rotation out of high-valuation sectors.",
        "context": "Tech can sometimes decouple from geopolitical events if the conflict is seen as contained and not affecting global economic growth.",
    },
    "Financials (XLF)": {
        "dir": "down",
        "reason": "Geopolitical uncertainty hurts financial stocks through increased credit risk, volatile trading conditions, and potential exposure to sanctioned entities.",
        "context": "However, if the crisis drives a flight to the dollar and higher rate expectations, financials could benefit from widening net interest margins.",
    },
    "Healthcare (XLV)": {
        "dir": "down",
        "reason": "Healthcare is typically defensive but not immune — broad market selloffs drag all sectors, though healthcare usually falls less than the market.",
        "context": "If healthcare outperformed while others fell, it confirms its reputation as a defensive sector — investors rotated into it for safety.",
    },
    "Consumer Disc. (XLY)": {
        "dir": "down",
        "reason": "Consumer discretionary spending is the first to get cut when uncertainty rises — people defer big purchases when they're worried about the economy.",
        "context": "Higher energy prices also squeeze consumer wallets directly, leaving less for discretionary spending.",
    },
}

for sector_name, exp in SECTOR_EXPECTATIONS.items():
    if sector_name in data.columns:
        s = data[sector_name].dropna()
        st.markdown(f"### {sector_name}")
        st.markdown(generate_commentary(
            sector_name, exp["dir"], exp["reason"], total_change(s),
            extra_context=exp["context"],
            chg_7d=pct_change_period(s, conflict_td, 7) if conflict_td else None,
            dd=max_drawdown(s),
        ))
        st.markdown("")

st.divider()

# --- All Sectors Overlay ---
st.markdown("## All Sectors — Overlay")
fig_all = make_chart(data, normalize=True, height=420, start_dt=start_dt, end_dt=end_dt)
if fig_all:
    st.plotly_chart(fig_all, width="stretch")

st.divider()

# --- Sector Ranking ---
st.markdown("## Sector Ranking")
st.caption("Ranked by total return over the analysis window.")

rankings = []
for name in SECTORS:
    if name in data.columns:
        s = data[name].dropna()
        rankings.append({
            "Sector": name,
            "Total Return": total_change(s),
        })

if rankings:
    rank_df = pd.DataFrame(rankings).sort_values("Total Return", ascending=False).reset_index(drop=True)
    rank_df.index = rank_df.index + 1
    rank_df.index.name = "Rank"

    fig_rank = go.Figure()
    colors = [COLOR_UP if v >= 0 else COLOR_DOWN for v in rank_df["Total Return"].fillna(0)]
    fig_rank.add_trace(go.Bar(
        y=rank_df["Sector"], x=rank_df["Total Return"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.2f}%" if pd.notna(v) else "N/A" for v in rank_df["Total Return"]],
        textposition="outside",
        hovertemplate="%{y}<br>%{x:+.2f}%<extra></extra>",
    ))
    fig_rank.update_layout(
        height=350, margin=dict(t=10, b=20, l=150, r=60),
        xaxis_title="% Change",
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig_rank, width="stretch")

st.divider()

# --- Deep Analysis Table ---
st.markdown("## Deep Analysis")

metrics = []
for name in SECTORS:
    if name in data.columns:
        s = data[name].dropna()
        chg_3 = pct_change_period(s, conflict_td, 3) if conflict_td else None
        chg_7 = pct_change_period(s, conflict_td, 7) if conflict_td else None
        metrics.append({
            "Sector": name,
            "3-Day": chg_3,
            "7-Day": chg_7,
            "Total": total_change(s),
            "Max Gain": max_gain(s),
            "Max Drawdown": max_drawdown(s),
            "Volatility (ann.)": volatility(s),
        })

if metrics:
    mdf = pd.DataFrame(metrics)
    fmt = {c: "{:+.2f}%" for c in mdf.columns if c != "Sector"}
    fmt["Volatility (ann.)"] = "{:.1f}%"
    st.dataframe(
        mdf.style.format(fmt, na_rep="N/A")
        .map(color_val, subset=["3-Day", "7-Day", "Total", "Max Gain", "Max Drawdown"]),
        width="stretch", hide_index=True,
    )

st.divider()

# --- Correlation ---
st.markdown("## Sector Correlation")
st.markdown(
    "Which sectors moved together? High correlation between Energy and Defense suggests "
    "a shared 'conflict beneficiary' trade. Negative correlation with Airlines confirms the "
    "winner/loser dynamic."
)

corr = correlation_matrix(data)
if corr is not None:
    fig_corr = px.imshow(
        corr, text_auto=".2f",
        color_continuous_scale="RdYlGn",
        zmin=-1, zmax=1, aspect="auto",
    )
    fig_corr.update_layout(height=450, margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig_corr, width="stretch")

st.divider()
st.caption("Ring 3 — Where the shock creates winners and losers within the US market.")
