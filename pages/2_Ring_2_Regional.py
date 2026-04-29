"""Ring 2 — Regional Contagion"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from config import (
    render_sidebar, load_data, normalize_to_start, total_change,
    find_conflict_td, pct_change_period, max_drawdown, volatility,
    correlation_matrix, make_chart, add_milestones, color_val, generate_commentary,
    REGIONS, COLOR_UP, COLOR_DOWN, COLORS,
)

st.set_page_config(page_title="Ring 2 — Regional Contagion", layout="wide")
start_dt, end_dt = render_sidebar()

st.markdown("# Ring 2 — Regional Contagion")
st.markdown(
    "Did the shock stay in the Middle East or go global? This page tracks **7 regional indices** "
    "to map how the conflict's impact traveled geographically. "
    "Proximity to the conflict zone, energy dependence, and trade exposure all determine who gets hit hardest."
)

st.divider()

with st.spinner("Loading regional data..."):
    data = load_data(REGIONS, start_dt, end_dt)

if data.empty:
    st.error("Could not fetch regional data.")
    st.stop()

conflict_td = find_conflict_td(data)

# --- All Regions Overlay ---
st.markdown("## All Regions — Normalized")
st.caption("% change from start of window. Which region diverged the most?")
fig = make_chart(data, normalize=True, height=450, start_dt=start_dt, end_dt=end_dt)
if fig:
    st.plotly_chart(fig, width="stretch")

st.divider()

# --- Data-Driven Regional Commentary ---
st.markdown("## What the Data Says — Region by Region")

REGION_EXPECTATIONS = {
    "US (S&P 500)": {
        "dir": "down",
        "reason": "As the global benchmark, the S&P 500 typically sells off during geopolitical crises as investors reduce risk exposure and reprice uncertainty.",
        "context": "If the US market held up, it could signal that the conflict is perceived as regionally contained and unlikely to impact US economic growth directly.",
    },
    "Europe (VGK)": {
        "dir": "down",
        "reason": "Europe is highly energy-dependent — it imports a significant portion of its oil and gas. Higher energy prices directly hit European consumers and manufacturers.",
        "context": "Europe's proximity to the Middle East and its energy import dependence make it especially vulnerable. A larger drop than the US would confirm this energy transmission channel.",
    },
    "Saudi Arabia (KSA)": {
        "dir": "up",
        "reason": "Saudi Arabia benefits from higher oil prices as the world's largest oil exporter. Conflict that raises oil prices directly boosts Saudi revenue and GDP.",
        "context": "However, if the conflict threatens Saudi territory or its own oil infrastructure, the market may price in operational risk that offsets the oil price benefit. The direction tells you which force the market sees as dominant.",
    },
    "Turkey (TUR)": {
        "dir": "down",
        "reason": "Turkey is geographically close to the conflict zone, is a net energy importer, and has its own complex relationships with Iran and the US — making it triply exposed.",
        "context": "Turkey's current account deficit worsens when oil prices rise (it imports nearly all its energy), adding currency pressure on top of equity losses.",
    },
    "Emerging Markets (EEM)": {
        "dir": "down",
        "reason": "Emerging markets suffer during geopolitical crises as capital flows to safer developed markets (the 'risk-off' trade), and higher oil prices hurt energy-importing EM economies.",
        "context": "If EM held up, it may indicate that commodity-exporting emerging markets (Brazil, South Africa) are offsetting losses in commodity importers (India, Southeast Asia).",
    },
    "Japan (EWJ)": {
        "dir": "down",
        "reason": "Japan imports nearly all its energy — higher oil prices are a direct tax on its economy, and geopolitical instability in the Middle East disrupts its critical supply routes.",
        "context": "Japan's yen sometimes strengthens during crises (yen carry trade unwind), which hurts Japanese exporters and adds a second layer of pressure on equities.",
    },
    "China (FXI)": {
        "dir": "down",
        "reason": "China is the world's largest oil importer — higher oil prices increase input costs across its manufacturing base and can slow economic growth.",
        "context": "China's reaction also depends on its diplomatic positioning. If it maintains trade with Iran despite sanctions, Chinese companies face secondary sanction risks that the market may price in.",
    },
}

for region_name, exp in REGION_EXPECTATIONS.items():
    if region_name in data.columns:
        s = data[region_name].dropna()
        st.markdown(f"### {region_name}")
        st.markdown(generate_commentary(
            region_name, exp["dir"], exp["reason"], total_change(s),
            extra_context=exp["context"],
            chg_7d=pct_change_period(s, conflict_td, 7) if conflict_td else None,
            dd=max_drawdown(s),
        ))
        st.markdown("")

st.divider()

# --- Regional Scorecard ---
st.markdown("## Regional Impact Scorecard")

metrics = []
for name in REGIONS:
    if name in data.columns:
        s = data[name].dropna()
        chg_3 = pct_change_period(s, conflict_td, 3) if conflict_td else None
        chg_7 = pct_change_period(s, conflict_td, 7) if conflict_td else None
        metrics.append({
            "Region": name,
            "3-Day": chg_3,
            "7-Day": chg_7,
            "Total": total_change(s),
            "Max Drawdown": max_drawdown(s),
            "Volatility (ann.)": volatility(s),
        })

if metrics:
    mdf = pd.DataFrame(metrics)
    fmt = {c: "{:+.2f}%" for c in mdf.columns if c != "Region"}
    fmt["Volatility (ann.)"] = "{:.1f}%"
    st.dataframe(
        mdf.style.format(fmt, na_rep="N/A")
        .map(color_val, subset=["3-Day", "7-Day", "Total", "Max Drawdown"]),
        width="stretch", hide_index=True,
    )

# Dynamic contagion assessment
if metrics:
    neg_count = sum(1 for m in metrics if m["Total"] is not None and m["Total"] < -1)
    total_count = sum(1 for m in metrics if m["Total"] is not None)
    if neg_count >= 5:
        st.error(
            f"**Global contagion confirmed.** {neg_count} out of {total_count} regions are down significantly. "
            "The shock has gone well beyond the Middle East — this is a truly global market event."
        )
    elif neg_count >= 3:
        st.warning(
            f"**Partial contagion.** {neg_count} out of {total_count} regions are down significantly. "
            "The shock has spread beyond the epicenter but hasn't fully engulfed all markets."
        )
    else:
        st.success(
            f"**Limited contagion.** Only {neg_count} out of {total_count} regions are down significantly. "
            "The shock appears regionally contained — global markets are largely shrugging it off."
        )

st.divider()

# --- Head-to-Head: Pick 2 regions ---
st.markdown("## Head-to-Head Comparison")
st.caption("Select two regions to compare side by side.")

available = [c for c in REGIONS if c in data.columns]
if len(available) >= 2:
    c1, c2 = st.columns(2)
    region_a = c1.selectbox("Region A", available, index=0)
    region_b = c2.selectbox("Region B", available, index=min(1, len(available) - 1))

    if region_a != region_b:
        compare_df = data[[region_a, region_b]].dropna()
        norm = normalize_to_start(compare_df)

        fig_cmp = go.Figure()
        for i, col in enumerate(norm.columns):
            fig_cmp.add_trace(go.Scatter(
                x=norm.index, y=norm[col],
                mode="lines", name=col,
                line=dict(width=2.5, color=COLORS[i]),
                hovertemplate=f"{col}<br>" + "%{x|%b %d}<br>%{y:+.2f}%<extra></extra>",
            ))
        add_milestones(fig_cmp, start_dt, end_dt)
        fig_cmp.add_hline(y=0, line_dash="dot", line_color="gray", line_width=0.8)
        fig_cmp.update_layout(
            height=380, margin=dict(t=20, b=30, l=50, r=20),
            yaxis_title="% Change", hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        )
        st.plotly_chart(fig_cmp, width="stretch")

        mc1, mc2 = st.columns(2)
        for col_sel, metric_col in [(region_a, mc1), (region_b, mc2)]:
            with metric_col:
                chg = total_change(data[col_sel])
                dd = max_drawdown(data[col_sel])
                vol = volatility(data[col_sel])
                st.markdown(f"**{col_sel}**")
                st.markdown(f"Total: **{chg:+.2f}%**" if chg else "Total: N/A")
                st.markdown(f"Max Drawdown: **{dd:+.2f}%**" if dd else "Max Drawdown: N/A")
                st.markdown(f"Volatility: **{vol:.1f}%**" if vol else "Volatility: N/A")
    else:
        st.info("Select two different regions to compare.")

st.divider()

# --- Correlation Heatmap ---
st.markdown("## Regional Correlation")
st.markdown(
    "How correlated were regional markets during this period? "
    "High correlation means the shock was truly global; low correlation means some regions "
    "were insulated."
)

corr = correlation_matrix(data)
if corr is not None:
    fig_corr = px.imshow(
        corr, text_auto=".2f",
        color_continuous_scale="RdYlGn",
        zmin=-1, zmax=1,
        aspect="auto",
    )
    fig_corr.update_layout(height=450, margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig_corr, width="stretch")

    # Dynamic correlation insight (exclude diagonal self-correlations)
    mask = corr.copy()
    for i in range(len(mask)):
        mask.iloc[i, i] = None
    avg_corr = mask.stack().mean()

    if avg_corr > 0.7:
        st.info(
            f"**Average cross-regional correlation: {avg_corr:.2f}** — Very high. "
            "All regions moved in lockstep, confirming this was a globally synchronized shock."
        )
    elif avg_corr > 0.4:
        st.info(
            f"**Average cross-regional correlation: {avg_corr:.2f}** — Moderate. "
            "Regions generally moved together but with meaningful differences — some were more insulated."
        )
    else:
        st.info(
            f"**Average cross-regional correlation: {avg_corr:.2f}** — Low. "
            "Regional markets largely decoupled — the shock had very different effects depending on geography."
        )

st.divider()
st.caption("Ring 2 — Mapping how far the shockwave traveled geographically.")
