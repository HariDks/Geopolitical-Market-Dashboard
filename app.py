"""
The Ripple Effect — Home Page
How the US-Iran Conflict Reshaped Global Markets
"""

import streamlit as st
import pandas as pd
from config import (
    render_sidebar, load_data, normalize_to_start, total_change,
    find_conflict_td, pct_change_period, max_drawdown, make_chart,
    color_val, _move_phrase,
    EPICENTER, REGIONS, SECTORS, COMPANIES, SAFETY, MILESTONES,
    COLOR_UP, COLOR_DOWN, CONFLICT_START,
)

st.set_page_config(page_title="The Ripple Effect — US-Iran Conflict", layout="wide")
start_dt, end_dt = render_sidebar()

# --- Header ---
st.markdown("# The Ripple Effect")
st.markdown("### How the US-Iran Conflict Reshaped Global Markets")
st.caption(f"Analysis window: {start_dt.strftime('%b %d, %Y')} → {end_dt.strftime('%b %d, %Y')}")

st.divider()

# --- Fetch all data ---
with st.spinner("Loading market data..."):
    data_epi = load_data(EPICENTER, start_dt, end_dt)
    data_reg = load_data(REGIONS, start_dt, end_dt)
    data_sec = load_data(SECTORS, start_dt, end_dt)
    data_comp = load_data(COMPANIES, start_dt, end_dt)
    data_safe = load_data(SAFETY, start_dt, end_dt)


# --- Helper to safely get total_change ---
def _chg(df, col):
    if df.empty or col not in df.columns:
        return None
    return total_change(df[col])


def _dd(df, col):
    if df.empty or col not in df.columns:
        return None
    return max_drawdown(df[col].dropna())


# Gather all key numbers
oil_chg = _chg(data_epi, "Crude Oil WTI")
brent_chg = _chg(data_epi, "Brent Crude")
gas_chg = _chg(data_epi, "Natural Gas")
spy_chg = _chg(data_reg, "US (S&P 500)")
eem_chg = _chg(data_reg, "Emerging Markets (EEM)")
europe_chg = _chg(data_reg, "Europe (VGK)")
saudi_chg = _chg(data_reg, "Saudi Arabia (KSA)")
turkey_chg = _chg(data_reg, "Turkey (TUR)")
japan_chg = _chg(data_reg, "Japan (EWJ)")
china_chg = _chg(data_reg, "China (FXI)")
xle_chg = _chg(data_sec, "Energy (XLE)")
ita_chg = _chg(data_sec, "Defense (ITA)")
jets_chg = _chg(data_sec, "Airlines (JETS)")
xlk_chg = _chg(data_sec, "Tech (XLK)")
xlv_chg = _chg(data_sec, "Healthcare (XLV)")
xly_chg = _chg(data_sec, "Consumer Disc. (XLY)")
xlf_chg = _chg(data_sec, "Financials (XLF)")
lmt_chg = _chg(data_comp, "Lockheed Martin")
rtx_chg = _chg(data_comp, "RTX (Raytheon)")
xom_chg = _chg(data_comp, "ExxonMobil")
cvx_chg = _chg(data_comp, "Chevron")
dal_chg = _chg(data_comp, "Delta Airlines")
ual_chg = _chg(data_comp, "United Airlines")
vix_chg = _chg(data_safe, "VIX")
gold_chg = _chg(data_safe, "Gold (GLD)")
tlt_chg = _chg(data_safe, "US Treasuries (TLT)")
uup_chg = _chg(data_safe, "US Dollar (UUP)")

spy_dd = _dd(data_reg, "US (S&P 500)")
jets_dd = _dd(data_sec, "Airlines (JETS)")

# =====================================================================
# AT A GLANCE — Metric Cards
# =====================================================================
st.markdown("## At a Glance")

summary = {
    "Crude Oil": oil_chg,
    "S&P 500": spy_chg,
    "VIX": vix_chg,
    "Gold": gold_chg,
    "Energy": xle_chg,
    "Defense": ita_chg,
    "Airlines": jets_chg,
    "Emg. Markets": eem_chg,
}

cols = st.columns(len(summary))
for i, (label, chg) in enumerate(summary.items()):
    with cols[i]:
        if chg is not None:
            st.metric(label, f"{chg:+.2f}%", delta_color="normal")
        else:
            st.metric(label, "N/A")

st.divider()

# =====================================================================
# EXECUTIVE SUMMARY — Dynamic paragraph
# =====================================================================
st.markdown("## Executive Summary")

exec_parts = []

# Opening: overall market mood
if spy_chg is not None and vix_chg is not None:
    if spy_chg < -3 and vix_chg > 10:
        exec_parts.append(
            f"The US-Iran conflict has delivered a significant blow to global markets. "
            f"The S&P 500 {_move_phrase(spy_chg)} while the VIX fear index {_move_phrase(vix_chg)}, "
            f"painting a picture of genuine market stress."
        )
    elif spy_chg < -1 and vix_chg > 3:
        exec_parts.append(
            f"Markets are under pressure but not in freefall. "
            f"The S&P 500 {_move_phrase(spy_chg)} and the VIX {_move_phrase(vix_chg)}, "
            f"suggesting investors are cautious but not panicking."
        )
    elif spy_chg < -1 and vix_chg < 3:
        exec_parts.append(
            f"An unusual pattern is emerging — the S&P 500 {_move_phrase(spy_chg)} "
            f"but the VIX {_move_phrase(vix_chg)}, suggesting the selloff is orderly rather than fear-driven."
        )
    elif abs(spy_chg) < 1:
        exec_parts.append(
            f"Broad markets have largely shrugged off the conflict so far. "
            f"The S&P 500 {_move_phrase(spy_chg)} — the impact is showing up in specific sectors "
            f"rather than in the headline index."
        )
    else:
        exec_parts.append(
            f"The market reaction has been mixed. The S&P 500 {_move_phrase(spy_chg)} "
            f"and the VIX {_move_phrase(vix_chg)}."
        )

# Oil epicenter
if oil_chg is not None:
    if oil_chg > 5:
        exec_parts.append(
            f"The epicenter of the shock is clear: crude oil {_move_phrase(oil_chg)}, "
            f"reflecting the market's fear of supply disruptions through the Strait of Hormuz."
        )
    elif oil_chg > 1:
        exec_parts.append(
            f"Oil prices have risen modestly ({oil_chg:+.2f}%), suggesting the market sees some supply risk "
            f"but isn't pricing in a worst-case disruption scenario."
        )
    elif oil_chg < -1:
        exec_parts.append(
            f"Surprisingly, oil {_move_phrase(oil_chg)} despite the conflict — "
            f"this could signal that global demand fears are overwhelming supply disruption concerns, "
            f"or that the market expects a quick resolution."
        )
    else:
        exec_parts.append(
            f"Oil has been surprisingly stable ({oil_chg:+.2f}%), "
            f"suggesting the market doesn't see an imminent supply disruption."
        )

# Regional contagion assessment
regional_changes = [
    ("US", spy_chg), ("Europe", europe_chg), ("Saudi Arabia", saudi_chg),
    ("Turkey", turkey_chg), ("Emerging Markets", eem_chg),
    ("Japan", japan_chg), ("China", china_chg),
]
neg_regions = [(name, chg) for name, chg in regional_changes if chg is not None and chg < -1]
pos_regions = [(name, chg) for name, chg in regional_changes if chg is not None and chg > 1]
total_regions = len([c for _, c in regional_changes if c is not None])

if len(neg_regions) >= 5:
    worst = min(neg_regions, key=lambda x: x[1])
    exec_parts.append(
        f"The contagion is global — {len(neg_regions)} out of {total_regions} tracked regions are down, "
        f"with {worst[0]} hit hardest at {worst[1]:+.2f}%. "
        f"This is not a contained regional event."
    )
elif len(neg_regions) >= 3:
    exec_parts.append(
        f"The shock has spread partially — {len(neg_regions)} of {total_regions} regions are in negative territory. "
        + (f"Saudi Arabia bucked the trend at {saudi_chg:+.2f}%, benefiting from higher oil prices. " if saudi_chg is not None and saudi_chg > 0 else "")
    )
elif total_regions > 0:
    exec_parts.append(
        f"Regional contagion has been limited — only {len(neg_regions)} of {total_regions} regions are meaningfully down. "
        f"The shock appears contained."
    )

# Sector divergence
if xle_chg is not None and jets_chg is not None:
    spread = (xle_chg or 0) - (jets_chg or 0)
    if spread > 10:
        exec_parts.append(
            f"The sector divergence is dramatic: Energy {_move_phrase(xle_chg)} while Airlines {_move_phrase(jets_chg)}"
            + (f", with airlines at one point down as much as {jets_dd:.1f}% from peak" if jets_dd and jets_dd < -10 else "")
            + ". This is the classic conflict trade playing out in real time."
        )
    elif spread > 3:
        exec_parts.append(
            f"The expected sector rotation is visible but moderate — Energy is at {xle_chg:+.2f}% "
            f"versus Airlines at {jets_chg:+.2f}%."
        )
    else:
        exec_parts.append(
            f"Sector divergence is narrower than expected — Energy ({xle_chg:+.2f}%) and Airlines ({jets_chg:+.2f}%) "
            f"haven't separated as much as a typical conflict would predict."
        )

# Defense check
if ita_chg is not None:
    if ita_chg > 2:
        exec_parts.append(
            f"Defense stocks are responding to the conflict thesis, up {ita_chg:+.2f}%."
        )
    elif ita_chg < -1:
        exec_parts.append(
            f"Notably, defense stocks are actually down {ita_chg:+.2f}% — "
            f"contradicting the expectation that military conflict boosts this sector. "
            f"The market may be anticipating de-escalation or pricing in broader risk-off pressure."
        )

# Safe haven flows
if gold_chg is not None and tlt_chg is not None:
    if gold_chg > 2 and tlt_chg > 1:
        exec_parts.append(
            f"The flight to safety is real — Gold {_move_phrase(gold_chg)} and Treasuries {_move_phrase(tlt_chg)}. "
            f"Capital is actively seeking shelter."
        )
    elif gold_chg > 2 and tlt_chg < -1:
        exec_parts.append(
            f"Gold {_move_phrase(gold_chg)} but Treasuries {_move_phrase(tlt_chg)} — "
            f"an interesting split suggesting investors fear inflation (good for gold) more than they crave bond safety."
        )
    elif gold_chg < 0 and tlt_chg < 0:
        exec_parts.append(
            f"Neither gold nor Treasuries are rallying — both are negative. "
            f"This suggests the market isn't in genuine 'fear mode' despite the conflict headlines."
        )

# Company highlights
company_highlights = []
if lmt_chg is not None and lmt_chg > 3:
    company_highlights.append(f"Lockheed Martin ({lmt_chg:+.2f}%)")
if xom_chg is not None and xom_chg > 3:
    company_highlights.append(f"ExxonMobil ({xom_chg:+.2f}%)")
if ual_chg is not None and ual_chg < -10:
    company_highlights.append(f"United Airlines ({ual_chg:+.2f}%)")
if dal_chg is not None and dal_chg < -10:
    company_highlights.append(f"Delta ({dal_chg:+.2f}%)")

if company_highlights:
    exec_parts.append(
        f"At the company level, the biggest movers tell the story: {', '.join(company_highlights)}."
    )

# Closing
exec_parts.append(
    "Explore each ring in the sidebar for the full analysis — charts, data tables, and detailed commentary."
)

st.markdown(" ".join(exec_parts))

st.divider()

# =====================================================================
# RING-BY-RING SNAPSHOT — Mini summaries
# =====================================================================
st.markdown("## Ring-by-Ring Snapshot")

# Ring 1
st.markdown("### Ring 1 — Oil & Energy (Epicenter)")
r1_parts = []
if oil_chg is not None:
    r1_parts.append(f"Crude oil (WTI) {_move_phrase(oil_chg)}.")
if brent_chg is not None and oil_chg is not None:
    spread_diff = (brent_chg or 0) - (oil_chg or 0)
    if abs(spread_diff) > 1:
        leader = "Brent" if brent_chg > oil_chg else "WTI"
        r1_parts.append(f"{leader} is outpacing the other by {abs(spread_diff):.1f} percentage points, signaling {'regional' if leader == 'Brent' else 'US-focused'} supply concerns.")
    else:
        r1_parts.append("WTI and Brent are moving in lockstep — the market sees this as a global oil story, not a regional one.")
if gas_chg is not None:
    if abs(gas_chg) < 2:
        r1_parts.append("Natural gas is largely unaffected, confirming the shock is oil-specific.")
    else:
        r1_parts.append(f"Natural gas {_move_phrase(gas_chg)}, suggesting energy fears are spreading beyond crude.")
if r1_parts:
    st.markdown(" ".join(r1_parts))

if not data_epi.empty:
    fig_epi = make_chart(data_epi, normalize=True, height=300, start_dt=start_dt, end_dt=end_dt)
    if fig_epi:
        st.plotly_chart(fig_epi, width="stretch")

st.markdown("")

# Ring 2
st.markdown("### Ring 2 — Regional Contagion")
r2_parts = []
if neg_regions:
    worst = min(neg_regions, key=lambda x: x[1])
    best_neg = max(neg_regions, key=lambda x: x[1])
    r2_parts.append(f"{len(neg_regions)} of {total_regions} regions are in the red.")
    r2_parts.append(f"{worst[0]} is the worst hit at {worst[1]:+.2f}%.")
if pos_regions:
    best = max(pos_regions, key=lambda x: x[1])
    r2_parts.append(f"{best[0]} is the standout gainer at {best[1]:+.2f}%"
                    + (" — likely benefiting from higher oil export revenues." if best[0] == "Saudi Arabia" else "."))
if r2_parts:
    st.markdown(" ".join(r2_parts))

if not data_reg.empty:
    fig_reg = make_chart(data_reg, normalize=True, height=300, start_dt=start_dt, end_dt=end_dt)
    if fig_reg:
        st.plotly_chart(fig_reg, width="stretch")

st.markdown("")

# Ring 3
st.markdown("### Ring 3 — Sector Winners & Losers")
sector_list = [
    ("Energy (XLE)", xle_chg), ("Defense (ITA)", ita_chg), ("Airlines (JETS)", jets_chg),
    ("Tech (XLK)", xlk_chg), ("Financials (XLF)", xlf_chg),
    ("Healthcare (XLV)", xlv_chg), ("Consumer Disc. (XLY)", xly_chg),
]
sector_valid = [(n, c) for n, c in sector_list if c is not None]
if sector_valid:
    sector_sorted = sorted(sector_valid, key=lambda x: x[1], reverse=True)
    top = sector_sorted[0]
    bottom = sector_sorted[-1]
    r3_parts = [
        f"The top performer is {top[0]} at {top[1]:+.2f}%, while {bottom[0]} trails at {bottom[1]:+.2f}%.",
    ]
    winners = [n for n, c in sector_sorted if c > 0.5]
    losers = [n for n, c in sector_sorted if c < -0.5]
    if winners and losers:
        r3_parts.append(f"Clear winners: {', '.join(winners)}. Clear losers: {', '.join(losers)}.")
    st.markdown(" ".join(r3_parts))

if not data_sec.empty:
    fig_sec = make_chart(data_sec, normalize=True, height=300, start_dt=start_dt, end_dt=end_dt)
    if fig_sec:
        st.plotly_chart(fig_sec, width="stretch")

st.markdown("")

# Ring 4
st.markdown("### Ring 4 — Company Spotlight")
comp_list = [
    ("Lockheed Martin", lmt_chg), ("RTX (Raytheon)", rtx_chg),
    ("ExxonMobil", xom_chg), ("Chevron", cvx_chg),
    ("Delta Airlines", dal_chg), ("United Airlines", ual_chg),
]
comp_valid = [(n, c) for n, c in comp_list if c is not None]
if comp_valid:
    comp_sorted = sorted(comp_valid, key=lambda x: x[1], reverse=True)
    r4_parts = []
    defense_avg = sum(c for n, c in comp_valid if n in ["Lockheed Martin", "RTX (Raytheon)"]) / max(1, len([1 for n, c in comp_valid if n in ["Lockheed Martin", "RTX (Raytheon)"]]))
    airline_avg = sum(c for n, c in comp_valid if n in ["Delta Airlines", "United Airlines"]) / max(1, len([1 for n, c in comp_valid if n in ["Delta Airlines", "United Airlines"]]))
    oil_avg = sum(c for n, c in comp_valid if n in ["ExxonMobil", "Chevron"]) / max(1, len([1 for n, c in comp_valid if n in ["ExxonMobil", "Chevron"]]))

    r4_parts.append(f"Defense contractors are averaging {defense_avg:+.1f}%, oil majors {oil_avg:+.1f}%, and airlines {airline_avg:+.1f}%.")

    biggest = comp_sorted[0]
    smallest = comp_sorted[-1]
    r4_parts.append(f"The widest gap is between {biggest[0]} ({biggest[1]:+.2f}%) and {smallest[0]} ({smallest[1]:+.2f}%) — a {biggest[1] - smallest[1]:.1f} percentage point spread.")
    st.markdown(" ".join(r4_parts))

if not data_comp.empty:
    fig_comp = make_chart(data_comp, normalize=True, height=300, start_dt=start_dt, end_dt=end_dt)
    if fig_comp:
        st.plotly_chart(fig_comp, width="stretch")

st.markdown("")

# Ring 5
st.markdown("### Ring 5 — Fear & Safety Gauges")
r5_parts = []
if vix_chg is not None:
    if vix_chg > 10:
        r5_parts.append(f"Fear is elevated — the VIX {_move_phrase(vix_chg)}, indicating significant market anxiety.")
    elif vix_chg > 3:
        r5_parts.append(f"The VIX {_move_phrase(vix_chg)}, showing moderate nervousness.")
    elif vix_chg < -2:
        r5_parts.append(f"The VIX has actually declined ({vix_chg:+.2f}%) — markets are calmer now than when the window started.")
    else:
        r5_parts.append(f"The VIX {_move_phrase(vix_chg)} — no significant fear spike.")

safe_up = []
safe_down = []
for name, chg in [("Gold", gold_chg), ("Treasuries", tlt_chg), ("Dollar", uup_chg)]:
    if chg is not None:
        if chg > 1:
            safe_up.append(f"{name} ({chg:+.2f}%)")
        elif chg < -1:
            safe_down.append(f"{name} ({chg:+.2f}%)")

if safe_up:
    r5_parts.append(f"Capital is flowing into: {', '.join(safe_up)}.")
if safe_down:
    r5_parts.append(f"Notably declining: {', '.join(safe_down)}.")
if not safe_up and not safe_down:
    r5_parts.append("Safe haven assets are largely flat — no strong flight to safety.")

if r5_parts:
    st.markdown(" ".join(r5_parts))

if not data_safe.empty:
    fig_safe = make_chart(data_safe, normalize=True, height=300, start_dt=start_dt, end_dt=end_dt)
    if fig_safe:
        st.plotly_chart(fig_safe, width="stretch")

st.divider()

# =====================================================================
# CONFLICT TIMELINE
# =====================================================================
st.markdown("## Conflict Timeline")
for dt, label, desc in MILESTONES:
    if start_dt <= dt <= end_dt:
        st.markdown(f"**{dt.strftime('%b %d, %Y')}** — **{label}**: {desc}")

st.divider()
st.caption("Data sourced from Yahoo Finance via yfinance. Built with Streamlit + Plotly.")
