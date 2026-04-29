"""Shared configuration, data fetching, and helpers for all pages."""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# --- Dates ---
CONFLICT_START = datetime(2026, 2, 28)

# Key escalation milestones
MILESTONES = [
    (datetime(2026, 2, 28), "Conflict Escalation", "US-Israel/Iran military tensions spike"),
    (datetime(2026, 3, 3), "Oil Supply Fears", "Strait of Hormuz shipping threat emerges"),
    (datetime(2026, 3, 7), "Sanctions Expanded", "New sanctions on Iranian oil exports"),
    (datetime(2026, 3, 12), "Market Selloff", "Global indices drop on escalation fears"),
    (datetime(2026, 3, 17), "Diplomatic Talks", "Initial de-escalation signals emerge"),
]

# --- Ticker Groups ---
EPICENTER = {
    "Crude Oil WTI": "CL=F",
    "Brent Crude": "BZ=F",
    "Natural Gas": "NG=F",
}

REGIONS = {
    "US (S&P 500)": "SPY",
    "Europe (VGK)": "VGK",
    "Saudi Arabia (KSA)": "KSA",
    "Turkey (TUR)": "TUR",
    "Emerging Markets (EEM)": "EEM",
    "Japan (EWJ)": "EWJ",
    "China (FXI)": "FXI",
}

SECTORS = {
    "Energy (XLE)": "XLE",
    "Defense (ITA)": "ITA",
    "Airlines (JETS)": "JETS",
    "Tech (XLK)": "XLK",
    "Financials (XLF)": "XLF",
    "Healthcare (XLV)": "XLV",
    "Consumer Disc. (XLY)": "XLY",
}

COMPANIES = {
    "Lockheed Martin": "LMT",
    "RTX (Raytheon)": "RTX",
    "ExxonMobil": "XOM",
    "Chevron": "CVX",
    "Delta Airlines": "DAL",
    "United Airlines": "UAL",
}

SAFETY = {
    "VIX": "^VIX",
    "Gold (GLD)": "GLD",
    "US Treasuries (TLT)": "TLT",
    "US Dollar (UUP)": "UUP",
}

# --- Colors ---
COLORS = px.colors.qualitative.Set2
COLOR_UP = "#22c55e"
COLOR_DOWN = "#ef4444"
COLOR_NEUTRAL = "#94a3b8"
MILESTONE_COLOR = "rgba(239, 68, 68, 0.5)"


# --- Date range (shared via session state) ---
def init_date_range():
    today = datetime.now()
    if "start_dt" not in st.session_state:
        st.session_state.start_dt = CONFLICT_START - timedelta(days=14)
    if "end_dt" not in st.session_state:
        st.session_state.end_dt = today


def render_sidebar():
    """Render the shared sidebar with date controls and milestone list."""
    init_date_range()
    today = datetime.now()

    st.sidebar.markdown("# The Ripple Effect")
    st.sidebar.markdown("*US-Iran Conflict — Market Impact*")
    st.sidebar.divider()

    st.sidebar.markdown("### Analysis Window")
    col1, col2 = st.sidebar.columns(2)
    start = col1.date_input("From", value=st.session_state.start_dt, max_value=today)
    end = col2.date_input("To", value=st.session_state.end_dt, max_value=today)
    st.session_state.start_dt = datetime.combine(start, datetime.min.time())
    st.session_state.end_dt = datetime.combine(end, datetime.min.time())

    st.sidebar.divider()
    st.sidebar.markdown("### Key Dates")
    for dt, label, desc in MILESTONES:
        if st.session_state.start_dt <= dt <= st.session_state.end_dt:
            st.sidebar.markdown(f"**{dt.strftime('%b %d')}** — {label}")
            st.sidebar.caption(desc)
    st.sidebar.divider()
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    return st.session_state.start_dt, st.session_state.end_dt


# --- Data Fetching ---
@st.cache_data(ttl=600, show_spinner=False)
def fetch_group(tickers_tuple, start, end):
    """Fetch close prices for a tuple of (name, ticker) pairs."""
    tickers = dict(tickers_tuple)
    frames = {}
    for name, ticker in tickers.items():
        try:
            # yfinance 'end' is exclusive, so add 2 days buffer to capture the latest trading day
            df = yf.download(ticker, start=start, end=end + timedelta(days=2), progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                frames[name] = df[["Close"]].rename(columns={"Close": name})
        except Exception:
            pass
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames.values(), axis=1)
    combined.index = pd.to_datetime(combined.index)
    return combined


def load_data(tickers_dict, start_dt, end_dt):
    """Wrapper that converts dict to hashable tuple for caching."""
    return fetch_group(tuple(tickers_dict.items()), start_dt, end_dt)


# --- Analysis Helpers ---
def normalize_to_start(df):
    first_valid = df.apply(lambda s: s.dropna().iloc[0] if len(s.dropna()) > 0 else None)
    return ((df / first_valid) - 1) * 100


def total_change(series):
    clean = series.dropna()
    if len(clean) < 2:
        return None
    return ((clean.iloc[-1] - clean.iloc[0]) / clean.iloc[0]) * 100


def pct_change_period(series, start_idx, n_days):
    post = series.loc[start_idx:]
    post = post.dropna()
    if len(post) <= n_days:
        return None
    return ((post.iloc[n_days] - post.iloc[0]) / post.iloc[0]) * 100


def find_conflict_td(df):
    if df.empty:
        return None
    return min(df.index.tolist(), key=lambda d: abs(d - pd.Timestamp(CONFLICT_START)))


def max_drawdown(series):
    """Maximum peak-to-trough decline in %."""
    clean = series.dropna()
    if len(clean) < 2:
        return None
    peak = clean.expanding().max()
    dd = ((clean - peak) / peak) * 100
    return dd.min()


def max_gain(series):
    """Maximum trough-to-peak gain in %."""
    clean = series.dropna()
    if len(clean) < 2:
        return None
    trough = clean.expanding().min()
    gain = ((clean - trough) / trough) * 100
    return gain.max()


def volatility(series, window=5):
    """Rolling annualized volatility (std of daily returns * sqrt(252))."""
    clean = series.dropna()
    if len(clean) < window + 1:
        return None
    returns = clean.pct_change().dropna()
    return returns.std() * (252 ** 0.5) * 100


def correlation_matrix(df):
    """Daily return correlation matrix."""
    returns = df.pct_change().dropna()
    if len(returns) < 5:
        return None
    return returns.corr()


# --- Chart Helpers ---
def add_milestones(fig, start_dt, end_dt):
    for dt, label, _ in MILESTONES:
        if start_dt <= dt <= end_dt:
            fig.add_shape(
                type="line", x0=dt, x1=dt,
                y0=0, y1=1, yref="paper",
                line=dict(dash="dot", color=MILESTONE_COLOR, width=1),
            )


def make_chart(df, title="", normalize=True, height=400, show_milestones=True,
               start_dt=None, end_dt=None, colors=None):
    if df.empty:
        return None
    plot_df = normalize_to_start(df) if normalize else df
    fig = go.Figure()
    palette = colors or COLORS
    for i, col in enumerate(plot_df.columns):
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df[col],
            mode="lines", name=col,
            line=dict(width=2.5, color=palette[i % len(palette)]),
            hovertemplate=(
                f"{col}<br>" + "%{x|%b %d, %Y}<br>"
                + ("%{y:+.2f}%" if normalize else "%{y:.2f}")
                + "<extra></extra>"
            ),
        ))
    if show_milestones and start_dt and end_dt:
        add_milestones(fig, start_dt, end_dt)
    if normalize:
        fig.add_hline(y=0, line_dash="dot", line_color="gray", line_width=0.8)
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)) if title else None,
        height=height,
        margin=dict(t=50 if title else 20, b=30, l=50, r=20),
        yaxis_title="% Change" if normalize else "Price",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    return fig


def color_val(val):
    if val is None or pd.isna(val):
        return "color: gray"
    return f"color: {COLOR_UP}; font-weight: 600" if val >= 0 else f"color: {COLOR_DOWN}; font-weight: 600"


# --- Dynamic Commentary Engine ---

def _move_phrase(chg):
    """Turn a % change into a natural language phrase."""
    if chg is None:
        return "has no data available"
    abs_chg = abs(chg)
    if abs_chg < 0.5:
        return f"has barely moved ({chg:+.2f}%)"
    if chg > 5:
        return f"has surged {chg:+.2f}%"
    if chg > 2:
        return f"is up a notable {chg:+.2f}%"
    if chg > 0.5:
        return f"has edged higher by {chg:+.2f}%"
    if chg < -5:
        return f"has plunged {chg:+.2f}%"
    if chg < -2:
        return f"is down a significant {chg:+.2f}%"
    return f"has slipped {chg:+.2f}%"


def generate_commentary(asset_name, expected_dir, expected_reason, actual_chg,
                         extra_context="", chg_7d=None, dd=None, vol=None):
    """
    Generate a natural, flowing paragraph of commentary that adapts its tone,
    structure, and content based on the actual data.

    The output changes every time the underlying data changes — new trading days,
    updated prices, or a different date window will produce different text.

    Parameters:
        asset_name: display name
        expected_dir: "up" or "down"
        expected_reason: why (1 sentence)
        actual_chg: total % change
        extra_context: optional nuance sentence
        chg_7d: optional 7-day % change for momentum insight
        dd: optional max drawdown for volatility insight
        vol: optional annualized volatility
    """
    if actual_chg is None:
        return f"No data is available for {asset_name} in the selected window."

    expected_word = "rally" if expected_dir == "up" else "decline"
    opposite_word = "decline" if expected_dir == "up" else "rally"
    matched = (expected_dir == "up" and actual_chg > 0.5) or (expected_dir == "down" and actual_chg < -0.5)
    surprised = (expected_dir == "up" and actual_chg < -0.5) or (expected_dir == "down" and actual_chg > 0.5)
    muted = not matched and not surprised

    # --- Build the paragraph dynamically ---
    sentences = []

    # Opening: set the scene with what the textbook says
    sentences.append(
        f"In a crisis like this, the textbook expects {asset_name} to {expected_word} — {expected_reason.rstrip('.')}"
        + "."
    )

    # Core: what actually happened, with tone matching the outcome
    if matched:
        sentences.append(
            f"The data confirms this: {asset_name} {_move_phrase(actual_chg)}, "
            f"tracking the expected pattern closely."
        )
    elif surprised:
        sentences.append(
            f"The data tells a different story. Instead of the expected {expected_word}, "
            f"{asset_name} {_move_phrase(actual_chg)} — moving in the opposite direction."
        )
    else:
        sentences.append(
            f"In practice, {asset_name} {_move_phrase(actual_chg)}, "
            f"neither confirming nor denying the thesis — the market's reaction has been muted."
        )

    # Momentum layer: if 7-day data available, add trajectory insight
    if chg_7d is not None and actual_chg is not None:
        if abs(actual_chg) > 0.5:
            if (chg_7d > 0 and actual_chg > 0) or (chg_7d < 0 and actual_chg < 0):
                if abs(actual_chg) > abs(chg_7d):
                    sentences.append("The move has been accelerating — later weeks saw bigger shifts than the first.")
                else:
                    sentences.append("Most of the move happened in the first week, with momentum fading since.")
            elif abs(chg_7d) > 0.5 and abs(actual_chg) > 0.5 and (chg_7d > 0) != (actual_chg > 0):
                sentences.append(
                    "Interestingly, the direction has reversed — the initial reaction and the current position tell different stories."
                )

    # Volatility layer: if max drawdown is notably large
    if dd is not None and dd < -5:
        sentences.append(
            f"It hasn't been a smooth ride either — at one point {asset_name} "
            f"was down as much as {dd:.1f}% from its peak in this window."
        )

    # Interpretation: explain what the outcome means
    if surprised:
        sentences.append(
            f"This divergence from expectations is worth paying attention to. "
            + (extra_context if extra_context else
               f"It suggests the market is weighing factors beyond the simple conflict narrative for {asset_name}.")
        )
    elif matched and extra_context:
        sentences.append(extra_context)
    elif muted:
        sentences.append(
            extra_context if extra_context else
            f"The muted reaction suggests the market either had this priced in already or doesn't see {asset_name} as heavily exposed to this particular shock."
        )

    return " ".join(sentences)
