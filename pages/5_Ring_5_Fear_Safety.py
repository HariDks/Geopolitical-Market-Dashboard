"""Ring 5 — Fear & Safety Gauges"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config import (
    render_sidebar, load_data, normalize_to_start, total_change,
    find_conflict_td, pct_change_period, max_drawdown, max_gain, volatility,
    make_chart, add_milestones, color_val, generate_commentary,
    SAFETY, COLOR_UP, COLOR_DOWN, COLORS,
)

st.set_page_config(page_title="Ring 5 — Fear & Safety", layout="wide")
start_dt, end_dt = render_sidebar()

st.markdown("# Ring 5 — Fear & Safety: Where Did the Money Go?")
st.markdown(
    "When geopolitical risk spikes, capital doesn't vanish — it **moves**. "
    "This page tracks the destinations: VIX measures fear itself, Gold and Treasuries are "
    "the classic safe havens, and the US Dollar often strengthens as global capital seeks shelter."
)

st.divider()

with st.spinner("Loading safety data..."):
    data = load_data(SAFETY, start_dt, end_dt)

if data.empty:
    st.error("Could not fetch safety gauge data.")
    st.stop()

conflict_td = find_conflict_td(data)

# --- All Gauges Overlay ---
st.markdown("## All Safety Gauges — Normalized")
fig = make_chart(data, normalize=True, height=420, start_dt=start_dt, end_dt=end_dt)
if fig:
    st.plotly_chart(fig, width="stretch")

# --- Summary Cards ---
cols = st.columns(len(SAFETY))
for i, name in enumerate(SAFETY):
    with cols[i]:
        if name in data.columns:
            chg = total_change(data[name])
            short = name.split("(")[0].strip() if "(" in name else name
            if chg is not None:
                st.metric(short, f"{chg:+.2f}%")
            else:
                st.metric(short, "N/A")

st.divider()

# --- Individual Deep Dives with Data-Driven Commentary ---
GAUGE_INFO = {
    "VIX": {
        "title": "VIX — The Fear Index",
        "emoji": "😰",
        "background": (
            "The VIX measures **expected market volatility** over the next 30 days, derived from "
            "S&P 500 options pricing. It's often called the 'fear gauge' because it spikes when "
            "uncertainty rises.\n\n"
            "- **Below 15:** Markets are calm\n"
            "- **15–25:** Normal uncertainty\n"
            "- **25–35:** Elevated fear, significant stress\n"
            "- **Above 35:** Panic territory"
        ),
        "expected_dir": "up",
        "expected_reason": "Geopolitical conflicts inject uncertainty into markets — options traders pay more for protection, pushing the VIX higher.",
        "context": "A muted VIX response suggests the market views the conflict as contained or already priced in. A sustained VIX above 25 signals ongoing fear, not just a one-day spike.",
    },
    "Gold (GLD)": {
        "title": "Gold — The Ancient Safe Haven",
        "emoji": "🥇",
        "background": (
            "Gold has been a store of value for millennia. During crises, investors buy gold because:\n\n"
            "- **No counterparty risk** (unlike bonds or currencies)\n"
            "- **Negatively correlated** with risk sentiment\n"
            "- Acts as an **inflation hedge** when oil spikes\n"
            "- Central bank buying intensifies during uncertainty"
        ),
        "expected_dir": "up",
        "expected_reason": "Gold is the classic 'fear trade' — when geopolitical risk rises, investors buy gold as a store of value outside the financial system.",
        "context": "If gold fell during a conflict, it could mean rising interest rates (opportunity cost of holding gold) are outweighing the fear bid, or that the dollar is strengthening too aggressively.",
    },
    "US Treasuries (TLT)": {
        "title": "US Treasuries — Flight to Quality",
        "emoji": "🏛",
        "background": (
            "US government bonds are considered the safest asset in the world. When fear rises, "
            "investors sell risky assets and buy Treasuries, pushing prices up (and yields down).\n\n"
            "TLT tracks long-term (20+ year) Treasury bonds. A rising TLT means investors are "
            "paying a premium for safety."
        ),
        "expected_dir": "up",
        "expected_reason": "The classic 'flight to quality' — when equities sell off, capital flows into government bonds, pushing Treasury prices up and yields down.",
        "context": "If Treasuries fell during a conflict, it could indicate inflation fears (oil spike → inflation → higher yields) are overpowering the safety bid — an unusual and concerning signal.",
    },
    "US Dollar (UUP)": {
        "title": "US Dollar — Global Reserve Currency",
        "emoji": "💵",
        "background": (
            "The US dollar often strengthens during global crises because:\n\n"
            "- It's the world's **reserve currency**\n"
            "- **Dollar demand** spikes as entities scramble for USD to service debts\n"
            "- US assets are perceived as relatively safe\n\n"
            "However, if the conflict directly threatens US interests, the effect can be mixed."
        ),
        "expected_dir": "up",
        "expected_reason": "Global crises typically drive a 'dollar smile' — capital flows into USD as the world's reserve currency and ultimate safe haven.",
        "context": "A weakening dollar during a US-involved conflict could signal that markets see the US as part of the problem rather than the solution — undermining the safe-haven narrative.",
    },
}

for name, info in GAUGE_INFO.items():
    if name not in data.columns:
        continue

    st.markdown(f"## {info['emoji']} {info['title']}")

    col_chart, col_info = st.columns([3, 2])

    with col_chart:
        s = data[name].dropna()
        fig_ind = go.Figure()
        fig_ind.add_trace(go.Scatter(
            x=s.index, y=s.values,
            mode="lines", name=name,
            line=dict(width=2.5, color=COLORS[0]),
            fill="tozeroy", fillcolor="rgba(99, 102, 241, 0.08)",
            hovertemplate="%{x|%b %d, %Y}<br>%{y:.2f}<extra></extra>",
        ))
        add_milestones(fig_ind, start_dt, end_dt)
        fig_ind.update_layout(
            height=320, margin=dict(t=10, b=30, l=50, r=20),
            yaxis_title="Value", hovermode="x unified",
        )
        st.plotly_chart(fig_ind, width="stretch")

    with col_info:
        st.markdown("**Background:**")
        st.markdown(info["background"])

    # Quick stats
    s = data[name].dropna()
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Start", f"{s.iloc[0]:.2f}" if len(s) > 0 else "N/A")
    mc2.metric("Peak", f"{s.max():.2f}" if len(s) > 0 else "N/A")
    mc3.metric("Latest", f"{s.iloc[-1]:.2f}" if len(s) > 0 else "N/A")
    chg = total_change(s)
    mc4.metric("Change", f"{chg:+.2f}%" if chg is not None else "N/A")

    # Data-driven commentary
    st.markdown("### What the Data Says")
    st.markdown(generate_commentary(
        name.split("(")[0].strip() if "(" in name else name,
        info["expected_dir"],
        info["expected_reason"],
        chg,
        extra_context=info["context"],
        chg_7d=pct_change_period(s, conflict_td, 7) if conflict_td else None,
        dd=max_drawdown(s),
    ))

    # VIX-specific level interpretation
    if name == "VIX" and len(s) > 0:
        latest_vix = s.iloc[-1]
        if latest_vix >= 35:
            st.error(f"Current VIX: **{latest_vix:.1f}** — Panic territory. Markets are pricing in severe ongoing risk.")
        elif latest_vix >= 25:
            st.warning(f"Current VIX: **{latest_vix:.1f}** — Elevated fear. Significant market stress, but not full panic.")
        elif latest_vix >= 15:
            st.info(f"Current VIX: **{latest_vix:.1f}** — Normal range. Moderate uncertainty, market is not panicking.")
        else:
            st.success(f"Current VIX: **{latest_vix:.1f}** — Markets are calm. Low expected turbulence.")

    st.divider()

# --- Capital Flow Story (dynamic) ---
st.markdown("## The Capital Flow Story")

vix_chg = total_change(data["VIX"]) if "VIX" in data.columns else None
gold_chg = total_change(data["Gold (GLD)"]) if "Gold (GLD)" in data.columns else None
tlt_chg = total_change(data["US Treasuries (TLT)"]) if "US Treasuries (TLT)" in data.columns else None
uup_chg = total_change(data["US Dollar (UUP)"]) if "US Dollar (UUP)" in data.columns else None

# Build dynamic narrative
if vix_chg is not None and gold_chg is not None:
    if vix_chg > 5 and gold_chg > 2 and (tlt_chg is not None and tlt_chg > 0):
        st.error(
            "**Full flight to safety.** VIX spiked, gold rallied, and Treasuries rose — "
            "the market is treating this as a serious, sustained threat. Capital is actively fleeing "
            "risk assets for safe havens. This is the textbook pattern for a major geopolitical shock."
        )
    elif vix_chg > 5 and gold_chg < 1:
        st.warning(
            "**Fear without the gold bid.** VIX spiked but gold didn't rally meaningfully. "
            "This could mean rising rate expectations (making gold less attractive) are competing "
            "with the safety bid, or that the fear is more about equity volatility than systemic risk."
        )
    elif vix_chg < 2 and gold_chg > 2:
        st.info(
            "**Quiet rotation.** VIX stayed calm but gold rose — investors are hedging quietly "
            "without panic selling equities. This suggests measured concern rather than fear, "
            "possibly institutional portfolio rebalancing."
        )
    elif vix_chg < 2 and gold_chg < 1:
        st.success(
            "**Market shrug.** Neither VIX nor gold moved significantly. The market is either "
            "not taking the conflict seriously, has already priced it in, or sees de-escalation ahead."
        )
    else:
        st.info(
            f"**Mixed signals.** VIX moved {vix_chg:+.1f}% and gold moved {gold_chg:+.1f}%. "
            "The picture isn't cleanly bullish or bearish on fear — the market is still processing "
            "the situation."
        )

st.divider()

# --- Full Analysis Table ---
st.markdown("## Full Analysis")

metrics = []
for name in SAFETY:
    if name in data.columns:
        s = data[name].dropna()
        chg_3 = pct_change_period(s, conflict_td, 3) if conflict_td else None
        chg_7 = pct_change_period(s, conflict_td, 7) if conflict_td else None
        metrics.append({
            "Gauge": name,
            "3-Day": chg_3,
            "7-Day": chg_7,
            "Total": total_change(s),
            "Max Gain": max_gain(s),
            "Max Drawdown": max_drawdown(s),
            "Volatility": volatility(s),
        })

if metrics:
    mdf = pd.DataFrame(metrics)
    fmt = {c: "{:+.2f}%" for c in mdf.columns if c != "Gauge"}
    fmt["Volatility"] = "{:.1f}%"
    st.dataframe(
        mdf.style.format(fmt, na_rep="N/A")
        .map(color_val, subset=["3-Day", "7-Day", "Total", "Max Gain", "Max Drawdown"]),
        width="stretch", hide_index=True,
    )

st.divider()
st.caption("Ring 5 — The outermost ring: where capital takes shelter from the storm.")
