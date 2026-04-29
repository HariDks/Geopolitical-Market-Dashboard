"""Ring 4 — Company Spotlight"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config import (
    render_sidebar, load_data, normalize_to_start, total_change,
    find_conflict_td, pct_change_period, max_drawdown, max_gain, volatility,
    make_chart, add_milestones, color_val, generate_commentary,
    COMPANIES, COLOR_UP, COLOR_DOWN, COLORS,
)

st.set_page_config(page_title="Ring 4 — Companies", layout="wide")
start_dt, end_dt = render_sidebar()

st.markdown("# Ring 4 — Company Spotlight")
st.markdown(
    "Sectors tell you the theme. **Individual stocks** tell you the real story. "
    "Defense contractors and oil majors see direct revenue upside from conflict; "
    "airlines face margin compression from fuel costs. These are the companies most directly exposed."
)

st.divider()

with st.spinner("Loading company data..."):
    data = load_data(COMPANIES, start_dt, end_dt)

if data.empty:
    st.error("Could not fetch company data.")
    st.stop()

conflict_td = find_conflict_td(data)

# --- Company groups with expectations ---
GROUPS = {
    "Defense Contractors": {
        "tickers": ["Lockheed Martin", "RTX (Raytheon)"],
        "emoji": "🛡",
        "thesis": (
            "Defense companies benefit directly from conflict. Government defense budgets increase, "
            "existing contracts accelerate, and new orders flow in. Lockheed Martin (F-35, missiles) "
            "and RTX/Raytheon (Patriot systems, radar) are the two largest US defense primes."
        ),
        "expectations": {
            "Lockheed Martin": {
                "dir": "up",
                "reason": "As the world's largest defense contractor, Lockheed is the most direct beneficiary of US military spending — they make the F-35, Patriot missiles, and THAAD systems.",
                "context": "If Lockheed fell despite escalation, it may indicate the market doubts a sustained conflict, or that the stock was already pricing in geopolitical risk before the event."
            },
            "RTX (Raytheon)": {
                "dir": "up",
                "reason": "RTX makes missile defense systems (Patriot, SM-3) and radar technology — exactly what's deployed in Middle East conflicts.",
                "context": "RTX also has a large commercial aerospace division (Pratt & Whitney engines), so airline weakness from the same conflict can partially offset defense gains."
            },
        },
    },
    "Oil Majors": {
        "tickers": ["ExxonMobil", "Chevron"],
        "emoji": "🛢",
        "thesis": (
            "Higher oil prices flow directly to the bottom line for integrated oil companies. "
            "Their production costs don't change much, but revenue per barrel surges. "
            "Exxon and Chevron are the two largest US-listed oil majors."
        ),
        "expectations": {
            "ExxonMobil": {
                "dir": "up",
                "reason": "As the largest US oil producer, every dollar increase in oil price per barrel flows almost directly to Exxon's earnings.",
                "context": "If Exxon underperformed the oil price move, it may signal concerns about windfall taxes, sanctions complications, or that the market expects oil to retreat quickly."
            },
            "Chevron": {
                "dir": "up",
                "reason": "Chevron benefits from the same oil price dynamics as Exxon, with significant upstream production in the US and Middle East.",
                "context": "Chevron has more Middle East exposure than Exxon, which can be both a revenue opportunity and an operational risk during conflict."
            },
        },
    },
    "Airlines": {
        "tickers": ["Delta Airlines", "United Airlines"],
        "emoji": "✈️",
        "thesis": (
            "Fuel is typically 20-30% of an airline's operating costs. When oil spikes, margins get "
            "crushed — especially if hedging positions are insufficient. Additionally, geopolitical "
            "uncertainty reduces travel demand. Airlines are among the clearest losers."
        ),
        "expectations": {
            "Delta Airlines": {
                "dir": "down",
                "reason": "Delta is highly sensitive to jet fuel prices. A sustained oil spike directly compresses margins, and fear of conflict reduces international bookings.",
                "context": "If Delta held up, it could mean their fuel hedging program is working, or that strong domestic travel demand is offsetting international weakness."
            },
            "United Airlines": {
                "dir": "down",
                "reason": "United has the largest international route network among US carriers, making it especially vulnerable to geopolitical travel disruptions.",
                "context": "United's heavy international exposure means Middle East route cancellations or rerouting directly hits revenue, on top of the fuel cost impact."
            },
        },
    },
}

# --- Render each group ---
for group_name, info in GROUPS.items():
    st.markdown(f"## {info['emoji']} {group_name}")
    st.markdown(f"*{info['thesis']}*")
    st.markdown("")

    available = [t for t in info["tickers"] if t in data.columns]
    if not available:
        st.warning(f"No data available for {group_name}.")
        st.divider()
        continue

    group_df = data[available]
    norm = normalize_to_start(group_df)

    # Chart
    fig = go.Figure()
    for i, col in enumerate(norm.columns):
        fig.add_trace(go.Scatter(
            x=norm.index, y=norm[col],
            mode="lines", name=col,
            line=dict(width=2.5, color=COLORS[i]),
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

    # Metrics row
    metric_cols = st.columns(len(available))
    for i, name in enumerate(available):
        s = data[name].dropna()
        with metric_cols[i]:
            st.markdown(f"**{name}**")
            chg = total_change(s)
            if chg is not None:
                color = COLOR_UP if chg >= 0 else COLOR_DOWN
                st.markdown(f"Total: <span style='color:{color}; font-size:1.3em; font-weight:700'>{chg:+.2f}%</span>", unsafe_allow_html=True)

            c3 = pct_change_period(s, conflict_td, 3) if conflict_td else None
            c7 = pct_change_period(s, conflict_td, 7) if conflict_td else None
            dd = max_drawdown(s)
            vol = volatility(s)

            if c3 is not None:
                st.caption(f"3-day: {c3:+.2f}%")
            if c7 is not None:
                st.caption(f"7-day: {c7:+.2f}%")
            if dd is not None:
                st.caption(f"Max drawdown: {dd:+.2f}%")
            if vol is not None:
                st.caption(f"Volatility: {vol:.1f}%")

    # Data-driven commentary for each company
    st.markdown(f"### What the Data Says — {group_name}")
    for name in available:
        if name in info["expectations"]:
            exp = info["expectations"][name]
            s = data[name].dropna()
            st.markdown(f"**{name}**")
            st.markdown(generate_commentary(
                name, exp["dir"], exp["reason"], total_change(s),
                extra_context=exp["context"],
                chg_7d=pct_change_period(s, conflict_td, 7) if conflict_td else None,
                dd=max_drawdown(s),
            ))
            st.markdown("")

    st.divider()

# --- All Companies Overlay ---
st.markdown("## All Companies — Overlay")
st.caption("Defense and oil vs airlines — the conflict divergence trade.")

fig_all = make_chart(data, normalize=True, height=420, start_dt=start_dt, end_dt=end_dt)
if fig_all:
    st.plotly_chart(fig_all, width="stretch")

# Dynamic overall insight
defense_avg = None
airline_avg = None
defense_names = [n for n in ["Lockheed Martin", "RTX (Raytheon)"] if n in data.columns]
airline_names = [n for n in ["Delta Airlines", "United Airlines"] if n in data.columns]

if defense_names:
    defense_changes = [total_change(data[n]) for n in defense_names]
    defense_changes = [c for c in defense_changes if c is not None]
    if defense_changes:
        defense_avg = sum(defense_changes) / len(defense_changes)

if airline_names:
    airline_changes = [total_change(data[n]) for n in airline_names]
    airline_changes = [c for c in airline_changes if c is not None]
    if airline_changes:
        airline_avg = sum(airline_changes) / len(airline_changes)

if defense_avg is not None and airline_avg is not None:
    spread = defense_avg - airline_avg
    st.markdown("### The Divergence Trade")
    if spread > 5:
        st.success(
            f"The defense-airline spread is **{spread:+.1f} percentage points**. "
            "This is a classic conflict divergence — defense profits while airlines bleed. "
            "The textbook pattern is playing out clearly."
        )
    elif spread > 0:
        st.info(
            f"The defense-airline spread is **{spread:+.1f} percentage points**. "
            "There's a mild divergence, but it's not as dramatic as a full conflict premium would suggest. "
            "The market may be pricing in a short-lived or contained conflict."
        )
    else:
        st.warning(
            f"The defense-airline spread is **{spread:+.1f} percentage points** — "
            "defense is actually underperforming airlines. This is unusual during a military conflict. "
            "Possible explanations: the conflict was already priced in, de-escalation expectations, "
            "or broader market forces overwhelming the sector-specific impact."
        )

st.divider()

# --- Full Table ---
st.markdown("## Full Scorecard")

metrics = []
for name in COMPANIES:
    if name in data.columns:
        s = data[name].dropna()
        chg_3 = pct_change_period(s, conflict_td, 3) if conflict_td else None
        chg_7 = pct_change_period(s, conflict_td, 7) if conflict_td else None
        metrics.append({
            "Company": name,
            "3-Day": chg_3,
            "7-Day": chg_7,
            "Total": total_change(s),
            "Max Gain": max_gain(s),
            "Max Drawdown": max_drawdown(s),
            "Volatility": volatility(s),
        })

if metrics:
    mdf = pd.DataFrame(metrics)
    fmt = {c: "{:+.2f}%" for c in mdf.columns if c != "Company"}
    fmt["Volatility"] = "{:.1f}%"
    st.dataframe(
        mdf.style.format(fmt, na_rep="N/A")
        .map(color_val, subset=["3-Day", "7-Day", "Total", "Max Gain", "Max Drawdown"]),
        width="stretch", hide_index=True,
    )

st.divider()
st.caption("Ring 4 — Real companies, real money, real impact.")
