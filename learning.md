# Learning Document — The Ripple Effect Dashboard

A comprehensive breakdown of everything built, every decision made, every bug hit, and every lesson learned while building "The Ripple Effect" — a Streamlit dashboard that tracks how the US-Iran conflict reshaped global markets.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [The Core Concept — Concentric Rings](#2-the-core-concept--concentric-rings)
3. [Architecture & File Structure](#3-architecture--file-structure)
4. [Technology Stack & Why Each Tool](#4-technology-stack--why-each-tool)
5. [config.py — The Shared Brain](#5-configpy--the-shared-brain)
6. [Data Fetching — yfinance Deep Dive](#6-data-fetching--yfinance-deep-dive)
7. [Analysis Helpers — The Math Behind the Numbers](#7-analysis-helpers--the-math-behind-the-numbers)
8. [The Dynamic Commentary Engine](#8-the-dynamic-commentary-engine)
9. [Page-by-Page Breakdown](#9-page-by-page-breakdown)
10. [Roadblocks & How We Solved Them](#10-roadblocks--how-we-solved-them)
11. [Design Decisions & Trade-offs](#11-design-decisions--trade-offs)
12. [Evolution of the Project](#12-evolution-of-the-project)
13. [Key Streamlit Patterns Used](#13-key-streamlit-patterns-used)
14. [What Makes This Dashboard "Living"](#14-what-makes-this-dashboard-living)
15. [Lessons Learned](#15-lessons-learned)

---

## 1. Project Overview

**What it is:** A multi-page Streamlit dashboard that visualizes the financial market impact of the US-Iran military conflict (starting Feb 28, 2026) as a ripple radiating outward in 5 concentric rings — from the oil epicenter to global fear gauges.

**What it tracks:** 28 financial assets across 5 categories, with live data from Yahoo Finance, interactive Plotly charts, and AI-style commentary that rewrites itself as new data flows in.

**Why it matters:** Most market dashboards show you what happened. This one tells you *why* it matters and *whether the market's reaction matches what theory predicts*. Every paragraph of text on every page is generated from the actual data — change the date range, and the entire narrative changes.

---

## 2. The Core Concept — Concentric Rings

The "ripple effect" metaphor structures the entire dashboard:

```
Ring 1 — Oil & Energy (Epicenter)
  Ring 2 — Regional Markets (Contagion)
    Ring 3 — Sector Winners & Losers
      Ring 4 — Company Spotlight
        Ring 5 — Fear & Safety Gauges
```

**Why rings?** A geopolitical shock doesn't hit everything equally. It starts at the point of impact (oil, because Iran controls the Strait of Hormuz) and radiates outward. Each ring represents a layer further from the direct impact:

- **Ring 1 (Oil):** The most direct impact. Iran threatens oil supply → oil prices move immediately.
- **Ring 2 (Regions):** Which countries get hit? Energy importers (Europe, Japan) vs exporters (Saudi Arabia).
- **Ring 3 (Sectors):** Within the US market, energy and defense benefit while airlines get crushed.
- **Ring 4 (Companies):** Specific stocks tell the real money story — Lockheed Martin vs Delta Airlines.
- **Ring 5 (Fear & Safety):** Where does scared money go? VIX, Gold, Treasuries, Dollar.

This structure gives users a mental model for how geopolitical shocks propagate through financial markets.

---

## 3. Architecture & File Structure

```
geopolitical-market-dashboard/
├── app.py                          # Home page — dynamic executive summary
├── config.py                       # Shared configuration, data fetching, helpers, commentary engine
├── requirements.txt                # Python dependencies
├── README.md                       # Project documentation
├── learning.md                     # This file
└── pages/
    ├── 1_Ring_1_Oil_Energy.py      # Ring 1 — Oil & Energy deep dive
    ├── 2_Ring_2_Regional.py        # Ring 2 — Regional contagion
    ├── 3_Ring_3_Sectors.py         # Ring 3 — Sector winners & losers
    ├── 4_Ring_4_Companies.py       # Ring 4 — Company spotlight
    └── 5_Ring_5_Fear_Safety.py     # Ring 5 — Fear & safety gauges
```

### Why this structure?

Streamlit's multi-page app convention: files in the `pages/` directory automatically become sidebar navigation items. The filename prefix (`1_`, `2_`, etc.) controls the ordering. The `app.py` file in the root is always the home page.

Everything shared across pages lives in `config.py` — this prevents code duplication and ensures all pages use the same data fetching, analysis functions, color scheme, and commentary engine.

---

## 4. Technology Stack & Why Each Tool

### Streamlit
**What:** Python framework that turns scripts into web apps.
**Why:** Zero frontend code needed. We write Python and Streamlit handles the HTML/CSS/JS. Perfect for data dashboards.
**Key features used:**
- `st.set_page_config()` — page title and wide layout
- `st.sidebar` — shared date controls and navigation
- `st.columns()` — grid layouts for metrics
- `st.metric()` — delta-colored KPI cards
- `st.plotly_chart()` — interactive chart rendering
- `st.dataframe()` — styled data tables
- `st.session_state` — shared state across pages
- `@st.cache_data()` — data caching with TTL
- `st.spinner()` — loading indicators
- `st.error()`, `st.warning()`, `st.success()`, `st.info()` — contextual callouts

### yfinance
**What:** Python library that pulls data from Yahoo Finance — free, no API key required.
**Why:** Zero setup friction. No authentication, no rate limit management, no billing. Just `yf.download(ticker, start, end)`.
**Gotchas learned:** See the Roadblocks section — the `end` date is exclusive, MultiIndex columns can appear unexpectedly, and future dates return empty DataFrames.

### Plotly
**What:** Interactive charting library.
**Why:** Hover tooltips, zoom, pan, and professional styling out of the box. Integrates natively with Streamlit via `st.plotly_chart()`.
**Key features used:**
- `go.Figure()` + `go.Scatter()` — line charts
- `go.Bar()` — horizontal bar charts for rankings
- `px.imshow()` — correlation heatmaps
- `fig.add_shape()` — milestone vertical lines
- `fig.add_hline()` — zero-line reference
- Custom hover templates with `hovertemplate`

### Pandas
**What:** Data manipulation library.
**Why:** The backbone of all data operations — fetching, cleaning, transforming, analyzing. Every analysis helper operates on Pandas Series or DataFrames.

---

## 5. config.py — The Shared Brain

This is the most important file. Everything shared across all 6 pages lives here.

### Constants

```python
CONFLICT_START = datetime(2026, 2, 28)
```
The anchor date. Every analysis references this.

```python
MILESTONES = [
    (datetime(2026, 2, 28), "Conflict Escalation", "US-Israel/Iran military tensions spike"),
    (datetime(2026, 3, 3),  "Oil Supply Fears", "Strait of Hormuz shipping threat emerges"),
    (datetime(2026, 3, 7),  "Sanctions Expanded", "New sanctions on Iranian oil exports"),
    (datetime(2026, 3, 12), "Market Selloff", "Global indices drop on escalation fears"),
    (datetime(2026, 3, 17), "Diplomatic Talks", "Initial de-escalation signals emerge"),
]
```
Key dates that get marked as vertical dotted lines on every chart across every page.

### Ticker Dictionaries

Five dictionaries map human-readable names to Yahoo Finance ticker symbols:

```python
EPICENTER = {"Crude Oil WTI": "CL=F", "Brent Crude": "BZ=F", "Natural Gas": "NG=F"}
REGIONS   = {"US (S&P 500)": "SPY", "Europe (VGK)": "VGK", ...}  # 7 tickers
SECTORS   = {"Energy (XLE)": "XLE", "Defense (ITA)": "ITA", ...}  # 7 tickers
COMPANIES = {"Lockheed Martin": "LMT", "RTX (Raytheon)": "RTX", ...}  # 6 tickers
SAFETY    = {"VIX": "^VIX", "Gold (GLD)": "GLD", ...}  # 4 tickers
```

Total: **28 tickers** across 5 groups.

**Why dictionaries?** The key is the display name (shown on charts/tables), the value is the Yahoo Finance ticker. This decouples presentation from data fetching.

### Date Range Management

```python
def init_date_range():
    today = datetime.now()
    if "start_dt" not in st.session_state:
        st.session_state.start_dt = CONFLICT_START - timedelta(days=14)
    if "end_dt" not in st.session_state:
        st.session_state.end_dt = today
```

- **Start date** defaults to 14 days before the conflict — gives context for the "before" period.
- **End date** defaults to `datetime.now()` — this is what makes the dashboard "living". Each new trading day extends the analysis window automatically.
- Both are stored in `st.session_state` so they persist across page navigation.

### The Sidebar (`render_sidebar`)

Every page calls `render_sidebar()` to get a consistent sidebar with:
1. Dashboard title
2. Date input controls (From/To)
3. Key milestone dates (filtered to the current window)
4. A "Refresh Data" button that clears the cache

The function returns `(start_dt, end_dt)` which every page uses.

---

## 6. Data Fetching — yfinance Deep Dive

### The Caching Strategy

```python
@st.cache_data(ttl=600, show_spinner=False)
def fetch_group(tickers_tuple, start, end):
```

- **`@st.cache_data`**: Streamlit's caching decorator. Same inputs → same output, no re-fetch.
- **`ttl=600`**: Cache expires after 10 minutes (600 seconds). This balances freshness vs API load.
- **`show_spinner=False`**: We handle our own spinners with `st.spinner()` at the page level.
- **`tickers_tuple`**: Streamlit caching requires hashable arguments. Dicts aren't hashable, so we convert to a tuple of `(name, ticker)` pairs.

### The `load_data` Wrapper

```python
def load_data(tickers_dict, start_dt, end_dt):
    return fetch_group(tuple(tickers_dict.items()), start_dt, end_dt)
```

Pages call `load_data(REGIONS, start_dt, end_dt)`. The wrapper converts the dict to a tuple for caching.

### How `fetch_group` Works

```python
def fetch_group(tickers_tuple, start, end):
    tickers = dict(tickers_tuple)
    frames = {}
    for name, ticker in tickers.items():
        try:
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
```

Step by step:
1. Convert tuple back to dict
2. Loop through each ticker, download from Yahoo Finance
3. `end + timedelta(days=2)` — critical fix for yfinance's exclusive end date (see Roadblocks)
4. Handle `MultiIndex` columns — yfinance sometimes returns them unexpectedly
5. Extract only the "Close" column, rename it to the human-readable name
6. Concatenate all series into a single DataFrame with a shared DatetimeIndex
7. Silently skip any tickers that fail (network issues, delisted, etc.)

The result is a DataFrame like:

```
                  Crude Oil WTI  Brent Crude  Natural Gas
Date
2026-02-14             71.23       75.41         2.31
2026-02-15             71.55       75.68         2.29
...
```

---

## 7. Analysis Helpers — The Math Behind the Numbers

### `normalize_to_start(df)`

```python
def normalize_to_start(df):
    first_valid = df.apply(lambda s: s.dropna().iloc[0] if len(s.dropna()) > 0 else None)
    return ((df / first_valid) - 1) * 100
```

**What it does:** Converts absolute prices to % change from the first data point.

**Why:** You can't compare $70/barrel oil with a $500 S&P 500 ETF on the same chart. Normalization puts everything on the same scale — "how much has each asset moved from its starting point?"

**Math:** If oil starts at $70 and is now $75: `((75 / 70) - 1) * 100 = +7.14%`

This is used on almost every chart in the dashboard.

### `total_change(series)`

```python
def total_change(series):
    clean = series.dropna()
    if len(clean) < 2:
        return None
    return ((clean.iloc[-1] - clean.iloc[0]) / clean.iloc[0]) * 100
```

**What:** Total % change from first to last data point. The most basic metric.

### `pct_change_period(series, start_idx, n_days)`

```python
def pct_change_period(series, start_idx, n_days):
    post = series.loc[start_idx:]
    post = post.dropna()
    if len(post) <= n_days:
        return None
    return ((post.iloc[n_days] - post.iloc[0]) / post.iloc[0]) * 100
```

**What:** % change over exactly N trading days after a reference point (the conflict start).

**Why:** "How did oil react in the first 3 days?" vs "How did it react over the full period?" These can be very different and tell different stories about market dynamics.

### `max_drawdown(series)`

```python
def max_drawdown(series):
    clean = series.dropna()
    if len(clean) < 2:
        return None
    peak = clean.expanding().max()
    dd = ((clean - peak) / peak) * 100
    return dd.min()
```

**What:** The worst peak-to-trough decline during the period.

**Why:** Total change can be misleading. An asset might end up +2% but have dropped -15% at one point. Max drawdown captures the worst pain point.

**How:** `expanding().max()` tracks the running maximum. At each point, we calculate how far below that peak the current price is. The worst such drop is the max drawdown.

### `max_gain(series)`

The mirror of max drawdown — the best trough-to-peak gain. Uses `expanding().min()` to track the running minimum.

### `volatility(series, window=5)`

```python
def volatility(series, window=5):
    clean = series.dropna()
    if len(clean) < window + 1:
        return None
    returns = clean.pct_change().dropna()
    return returns.std() * (252 ** 0.5) * 100
```

**What:** Annualized volatility — how much the asset bounces around.

**Math:**
1. Calculate daily returns (`pct_change()`)
2. Take the standard deviation of those returns
3. Multiply by `sqrt(252)` to annualize (252 trading days/year)
4. Multiply by 100 to express as percentage

Higher volatility = more uncertainty, wilder swings.

### `correlation_matrix(df)`

```python
def correlation_matrix(df):
    returns = df.pct_change().dropna()
    if len(returns) < 5:
        return None
    return returns.corr()
```

**What:** Correlation of daily returns between all asset pairs.

**Why:** High correlation means assets moved together (global shock). Low correlation means some regions/sectors were insulated.

**Note:** We correlate *returns* (daily % changes), not *prices*. Correlating prices is a common mistake that gives misleading results due to shared trends.

---

## 8. The Dynamic Commentary Engine

This is the most novel part of the dashboard. Instead of static text descriptions, every paragraph adapts to the actual data.

### The Problem It Solves

Static text becomes stale immediately. If you write "Oil surged 10%" and tomorrow oil is only up 3%, your dashboard is wrong. We needed text that:
1. Updates automatically as new data arrives
2. Changes tone based on whether the data matches expectations
3. Adds context about momentum, drawdowns, and surprises
4. Reads like natural prose, not a data table in sentence form

### How It Works

#### Step 1: Classify the outcome

```python
matched = (expected_dir == "up" and actual_chg > 0.5) or (expected_dir == "down" and actual_chg < -0.5)
surprised = (expected_dir == "up" and actual_chg < -0.5) or (expected_dir == "down" and actual_chg > 0.5)
muted = not matched and not surprised
```

Every asset has an "expected direction" during a conflict. Oil is expected to go up. Airlines are expected to go down. The commentary engine classifies the actual outcome as:
- **Matched:** Reality matches the textbook prediction
- **Surprised:** Reality is the opposite of what theory predicts
- **Muted:** The move is too small to confirm or deny (<0.5%)

#### Step 2: Build the paragraph sentence by sentence

```python
sentences = []

# Opening — what the textbook says
sentences.append(f"In a crisis like this, the textbook expects {asset_name} to {expected_word} — {expected_reason}.")

# Core — what actually happened (tone changes based on matched/surprised/muted)
if matched:
    sentences.append(f"The data confirms this: {asset_name} {_move_phrase(actual_chg)}, tracking the expected pattern closely.")
elif surprised:
    sentences.append(f"The data tells a different story. Instead of the expected {expected_word}, ...")
else:
    sentences.append(f"In practice, {asset_name} {_move_phrase(actual_chg)}, neither confirming nor denying the thesis...")
```

#### Step 3: Layer in momentum and volatility

If 7-day data is available, the engine adds trajectory insight:
- "The move has been accelerating — later weeks saw bigger shifts than the first."
- "Most of the move happened in the first week, with momentum fading since."
- "The direction has reversed — the initial reaction and the current position tell different stories."

If max drawdown is severe (< -5%), it adds:
- "It hasn't been a smooth ride either — at one point X was down as much as Y% from its peak."

#### Step 4: Interpret with context

Each asset has hand-written `extra_context` that explains what a surprise or match *means*:
- If gold fell during a conflict: "rising interest rates are outweighing the fear bid"
- If Saudi Arabia rose: "benefiting from higher oil export revenues"
- If defense stocks fell: "the market may be anticipating de-escalation"

#### The `_move_phrase` helper

```python
def _move_phrase(chg):
    if chg > 5:   return f"has surged {chg:+.2f}%"
    if chg > 2:   return f"is up a notable {chg:+.2f}%"
    if chg > 0.5: return f"has edged higher by {chg:+.2f}%"
    if chg < -5:  return f"has plunged {chg:+.2f}%"
    if chg < -2:  return f"is down a significant {chg:+.2f}%"
    ...
```

This turns raw numbers into natural language with appropriate intensity. +0.3% is "barely moved". +12% is "surged". The language scales with the magnitude.

### Why This Matters

On Day 1 of the conflict, oil might be +8% and the commentary says "has surged." Two weeks later, if oil retreats to +1%, the same page now says "has edged higher" and adds "Most of the move happened in the first week, with momentum fading since." No code change needed — the text automatically adapts.

---

## 9. Page-by-Page Breakdown

### Home Page (`app.py`) — Executive Summary

**Purpose:** Give a 30-second overview of the entire conflict's market impact without clicking into any ring.

**How it works:**
1. Fetches data from ALL 5 ticker groups
2. Calculates `total_change` for every key asset
3. Shows "At a Glance" metric cards for 8 headline numbers
4. Builds an Executive Summary paragraph dynamically:
   - Market mood (SPY + VIX combo — 5 different tonal patterns)
   - Oil epicenter assessment
   - Regional contagion count (how many of 7 regions are down)
   - Sector divergence (Energy vs Airlines spread)
   - Defense thesis check
   - Safe haven flow analysis (Gold + Treasuries pattern)
   - Company highlights (only mentioned if moves are significant)
5. Ring-by-Ring Snapshots with mini charts and dynamic text
6. Conflict timeline

**Key patterns:**
- The Executive Summary has conditional branches that produce different prose depending on the data. For example:
  - SPY down >3% AND VIX up >10% → "delivered a significant blow to global markets"
  - SPY down >1% AND VIX up >3% → "under pressure but not in freefall"
  - SPY flat → "largely shrugged off the conflict"

### Ring 1 — Oil & Energy (`1_Ring_1_Oil_Energy.py`)

**Sections:**
1. **Commodity Prices** — absolute price chart
2. **Oil Price Per Barrel** — start/peak/latest/change metrics for WTI
3. **Normalized Comparison** — WTI vs Brent vs Natural Gas on same scale
4. **Data-Driven Commentary** — per-commodity paragraphs from the commentary engine
5. **WTI-Brent Spread** — the difference between international and US oil benchmarks, with dynamic interpretation (widening = regional supply disruption, narrowing = unusual)
6. **Deep Analysis** — full metrics table

**Why the WTI-Brent spread matters:** If Brent rises more than WTI, the market sees the conflict as a Middle East supply issue. If they move together, it's a global demand story. This distinction matters for understanding the market's interpretation.

### Ring 2 — Regional Contagion (`2_Ring_2_Regional.py`)

**Sections:**
1. **All Regions Normalized** — overlay chart of 7 regional indices
2. **Region-by-Region Commentary** — each region gets a paragraph with specific expectations (e.g., Saudi Arabia expected to go UP because it benefits from higher oil; Turkey expected to go DOWN because it's a net energy importer)
3. **Regional Impact Scorecard** — table with 3-day, 7-day, total change, max drawdown, volatility
4. **Contagion Assessment** — dynamic alert (5+ regions down = "Global contagion confirmed", 3+ = "Partial contagion", <3 = "Limited contagion")
5. **Head-to-Head Comparison** — dropdown to pick 2 regions and compare
6. **Correlation Heatmap** — with dynamic average correlation insight

**The `REGION_EXPECTATIONS` dict:** Each region has a `dir` (expected direction), `reason` (why), and `context` (what it means if the expectation is wrong). This feeds the commentary engine.

### Ring 3 — Sector Winners & Losers (`3_Ring_3_Sectors.py`)

**Sections:**
1. **The Divergence** — splits sectors into Winners (positive return) and Losers (negative return) with separate charts side by side
2. **Sector-by-Sector Commentary** — expectations for each of 7 sectors
3. **All Sectors Overlay** — combined view
4. **Sector Ranking** — horizontal bar chart sorted by total return (green for positive, red for negative)
5. **Deep Analysis Table**
6. **Sector Correlation Heatmap**

**Key insight:** The Winner/Loser split is dynamic. If the date range changes, sectors can move between categories. A sector that was a "winner" in the first week might become a "loser" by month end.

### Ring 4 — Company Spotlight (`4_Ring_4_Companies.py`)

**Structure:** Companies are organized into 3 thematic groups:
- **Defense Contractors:** Lockheed Martin, RTX (Raytheon) — expected beneficiaries
- **Oil Majors:** ExxonMobil, Chevron — expected beneficiaries
- **Airlines:** Delta, United — expected losers

Each group gets:
1. Investment thesis explanation
2. Normalized chart comparing the two companies in the group
3. Metrics row (total change, 3-day, 7-day, drawdown, volatility)
4. Per-company commentary

**The Divergence Trade:** At the bottom, the page calculates the average return of defense stocks vs airline stocks. A large positive spread confirms the "conflict divergence trade" is playing out.

### Ring 5 — Fear & Safety Gauges (`5_Ring_5_Fear_Safety.py`)

**Sections:**
1. **All Gauges Normalized** — overlay of VIX, Gold, Treasuries, Dollar
2. **Summary Cards** — quick metrics for each
3. **Individual Deep Dives** — each gauge gets:
   - Chart with area fill
   - Background explanation (what VIX measures, why gold is a safe haven, etc.)
   - Start/Peak/Latest/Change metrics
   - Data-driven commentary
   - VIX-specific: level interpretation (below 15 = calm, 15-25 = normal, 25-35 = elevated, 35+ = panic)
4. **Capital Flow Story** — dynamic pattern detection:
   - VIX up + Gold up + Treasuries up = "Full flight to safety"
   - VIX up + Gold flat = "Fear without the gold bid"
   - VIX flat + Gold up = "Quiet rotation"
   - VIX flat + Gold flat = "Market shrug"
5. **Full Analysis Table**

---

## 10. Roadblocks & How We Solved Them

### Roadblock 1: Plotly `add_vline` Timestamp Error

**The bug:**
```
TypeError: Addition/subtraction of integers and integer-arrays with Timestamp is no longer supported
```

**What happened:** Plotly's `fig.add_vline(x=datetime_value)` broke with newer Pandas versions that no longer support adding integers to Timestamps.

**The fix:** Replaced `add_vline()` with manual shape + annotation:
```python
fig.add_shape(
    type="line", x0=dt, x1=dt,
    y0=0, y1=1, yref="paper",
    line=dict(dash="dot", color=MILESTONE_COLOR, width=1),
)
```

**Lesson:** Higher-level convenience functions in Plotly can break across library versions. The lower-level `add_shape` API is more stable and gives more control.

### Roadblock 2: yfinance Exclusive End Date

**The bug:** Charts were consistently missing the last 1-2 trading days. If today is March 25, data stopped at March 22 or 23.

**What happened:** yfinance's `end` parameter is **exclusive** — `end="2026-03-25"` returns data up to March 24, not including March 25. Combined with weekends, this meant the latest trading day was often cut off.

**The fix:**
```python
df = yf.download(ticker, start=start, end=end + timedelta(days=2), progress=False)
```

Adding a 2-day buffer ensures we always capture the latest available trading day.

**Lesson:** Always check whether date parameters in APIs are inclusive or exclusive. This is a common source of off-by-one bugs in time series data.

### Roadblock 3: yfinance MultiIndex Columns

**The bug:** Some yfinance downloads returned a DataFrame with `MultiIndex` columns like `("Close", "SPY")` instead of just `"Close"`.

**What happened:** When downloading a single ticker, yfinance sometimes returns a MultiIndex (especially in certain versions), and sometimes doesn't. This inconsistency broke our column selection.

**The fix:**
```python
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
```

Flatten the MultiIndex to just the first level before processing.

**Lesson:** Never assume the structure of a library's output is consistent. Defensive checks for both cases save debugging time.

### Roadblock 4: `use_container_width` Deprecation

**The bug:** Streamlit started throwing deprecation warnings:
```
FutureWarning: use_container_width will be removed in a future version. Use width="stretch" instead.
```

**The fix:** Global find-and-replace of `use_container_width=True` → `width="stretch"` across all files.

**Lesson:** Streamlit moves fast and deprecates APIs. Always check the latest docs when you see warnings.

### Roadblock 5: Correlation Heatmap Error with `pd.np.eye`

**The bug:**
```
ValueError: Boolean array expected for the condition, not int64
```

**What happened:** An early attempt to mask the diagonal of the correlation matrix used `pd.np.eye()` (Pandas exposing NumPy), which was deprecated and returned incorrect types.

**The fix:** Replace with a simple loop:
```python
mask = corr.copy()
for i in range(len(mask)):
    mask.iloc[i, i] = None
avg_corr = mask.stack().mean()
```

Setting diagonal values to `None` and using `.stack().mean()` (which ignores NaN by default) gives the correct average off-diagonal correlation.

**Lesson:** Avoid using deprecated cross-library bridges like `pd.np`. Import NumPy directly if needed, or use pure Pandas alternatives.

### Roadblock 6: Future Date Events Returning Empty Data

**The bug:** Originally included milestones like "Fed Meeting May 2026" and "CPI Report March 2026" — but these were future dates that Yahoo Finance had no data for, causing empty DataFrames and broken charts.

**The fix:** Replaced all future events with real historical events that fall within the analysis window.

**Lesson:** When building data-driven dashboards, all reference points must have actual data available. Validate data existence before building features around it.

### Roadblock 7: Commentary Format Too Rigid

**The bug (design, not code):** The first commentary system used a rigid format:
```
**Expected:** Oil should rally during Middle East conflicts.
**Actual:** Oil is up +4.2%.
**Verdict:** ✅ Matches expectations.
```

The user found this too mechanical and repetitive across 28 assets.

**The fix:** Complete rewrite of the commentary engine to produce flowing paragraphs:
> "In a crisis like this, the textbook expects crude oil to rally — Middle East conflicts threaten supply routes, particularly the Strait of Hormuz. The data confirms this: crude oil has surged +8.23%, tracking the expected pattern closely. Most of the move happened in the first week, with momentum fading since."

**How:** Instead of a template with placeholders, we build an array of sentences conditionally and join them. The tone, structure, and content all adapt based on the data classification (matched/surprised/muted) and additional metrics (momentum, drawdown).

**Lesson:** Data presentation is as important as data accuracy. Natural language that adapts its tone feels intelligent; rigid templates feel robotic.

### Roadblock 8: Streamlit Auto-Reload Issues

**The bug:** During development, saving a file sometimes didn't trigger Streamlit's auto-reload, or the reload would fail silently.

**The fix:** Stop the server (`Ctrl+C`) and restart it (`streamlit run app.py`).

**Lesson:** Streamlit's file watcher is generally reliable but can get confused during rapid development, especially when modifying `config.py` (imported by all pages). When in doubt, restart.

---

## 11. Design Decisions & Trade-offs

### Decision: One `config.py` vs. per-page helpers
**Chose:** Single shared config.
**Why:** DRY principle. All pages use the same analysis functions, color scheme, and sidebar. Changes propagate everywhere instantly.
**Trade-off:** `config.py` is ~365 lines and growing. If the project scaled further, we might split into `config/data.py`, `config/analysis.py`, `config/charts.py`.

### Decision: Cache TTL of 600 seconds (10 minutes)
**Chose:** 10-minute cache.
**Why:** Market data during trading hours updates every second, but users don't need real-time data for this analysis. 10 minutes balances freshness with performance.
**Trade-off:** During fast-moving markets, data could be up to 10 minutes stale. The "Refresh Data" button lets users force an update.

### Decision: `width="stretch"` on all charts
**Chose:** Full-width charts.
**Why:** Dashboard has `layout="wide"`. Narrow charts waste horizontal space and make time series harder to read.

### Decision: Normalized charts as default
**Chose:** Most charts show % change from start, not absolute prices.
**Why:** You can't compare $70 oil with a $500 ETF on the same y-axis. Normalization enables apples-to-apples comparison.
**Trade-off:** Users lose the intuitive "price" reference. Ring 1 compensates by showing both absolute AND normalized charts.

### Decision: Expectations hard-coded per asset
**Chose:** Hand-written `expected_dir`, `reason`, and `context` for each of the 28 assets.
**Why:** These represent financial domain knowledge (e.g., "Turkey is a net energy importer, so it gets hit when oil rises"). This isn't data that can be calculated — it's expertise.
**Trade-off:** If the conflict context changes (e.g., a new type of geopolitical event), all expectations would need manual updating.

### Decision: Silent failure on data fetch
**Chose:** `except Exception: pass` in the data fetcher.
**Why:** If 1 of 7 regional tickers fails, we still want to show the other 6. A single failure shouldn't crash the entire page.
**Trade-off:** Users might not notice a missing ticker. The scorecards help — a missing row is visible.

---

## 12. Evolution of the Project

The dashboard evolved through several major iterations:

### V1: Multi-Event Comparison
**Idea:** Compare market reactions across different geopolitical events (US-Iran, Fed rate hike, CPI shock).
**Problem:** Too broad. Each event has different mechanics. A rate hike affects markets through completely different channels than a military conflict.

### V2: US-Iran Single-Page Dashboard
**Idea:** Focus exclusively on US-Iran but put everything on one page.
**Problem:** Too much scrolling. 28 assets on one page is overwhelming.

### V3: Multi-Page with Rings
**Idea:** Split into 5 pages (one per ring) with a shared sidebar.
**Benefit:** Each page is focused. Users can go deep on what interests them.

### V4: Static Commentary
**Idea:** Add text explanations alongside charts.
**Problem:** Text became stale as dates changed. Rigid Expected/Actual/Verdict format was repetitive.

### V5: Dynamic Commentary Engine
**Idea:** Generate all text from the data. Every paragraph adapts.
**Benefit:** Change the date range → entire narrative changes. New trading day → updated analysis.

### V6: Dynamic Home Page
**Idea:** Home page pulls insights from all 5 rings into a single executive summary.
**Benefit:** 30-second overview before diving into any ring. Also fully dynamic.

---

## 13. Key Streamlit Patterns Used

### Pattern: Session State for Shared Settings
```python
if "start_dt" not in st.session_state:
    st.session_state.start_dt = default_value
```
Used to share the date range across all pages. When a user changes the date on one page, it persists when navigating to another.

### Pattern: Cache with Hashable Arguments
```python
@st.cache_data(ttl=600)
def fetch_group(tickers_tuple, start, end):  # tuple, not dict
```
Streamlit's cache keys on the function arguments. Dicts aren't hashable, so we convert to tuples.

### Pattern: Spinner + Cache Combo
```python
with st.spinner("Loading data..."):
    data = load_data(TICKERS, start, end)
```
The spinner shows on the first load. On subsequent loads (cache hit), it flashes briefly or not at all.

### Pattern: Conditional Callouts
```python
if metric > threshold:
    st.error("Bad things happened.")
elif metric > lower_threshold:
    st.warning("Things are concerning.")
else:
    st.success("Things look okay.")
```
Used throughout for dynamic assessments (contagion level, VIX interpretation, correlation strength, etc.).

### Pattern: Styled DataFrames
```python
mdf.style.format(fmt, na_rep="N/A").map(color_val, subset=[...])
```
- `format()` applies number formatting (like `{:+.2f}%`)
- `map()` applies conditional coloring (green for positive, red for negative)
- `na_rep="N/A"` handles missing data gracefully

---

## 14. What Makes This Dashboard "Living"

Three mechanisms ensure the dashboard stays current without code changes:

### 1. End Date = `datetime.now()`
The analysis window automatically extends to include today. Every new trading day adds a new data point.

### 2. All Text Is Data-Driven
No hard-coded numbers in any prose. Every sentence is generated from `total_change()`, `max_drawdown()`, etc. If oil was +8% yesterday and is +3% today, the commentary shifts from "has surged" to "is up a notable."

### 3. Conditional Logic, Not Templates
The commentary engine doesn't just fill in blanks. It has `if/elif/else` branches that change the entire structure and tone of paragraphs based on the data. A "matched" outcome produces a confirmation narrative. A "surprised" outcome produces an investigation narrative. A "muted" outcome produces a "wait and see" narrative.

Together, these mean: **open the dashboard on any day and every number, chart, and paragraph reflects the current state of the market.**

---

## 15. Lessons Learned

### Technical Lessons

1. **Always check if API date parameters are inclusive or exclusive.** yfinance's `end` is exclusive — this single behavior caused the most confusion during development.

2. **Defensive data handling is essential.** Not every ticker will have data. Not every day will have a trading session. Every function needs to handle `None`, empty Series, and missing columns gracefully.

3. **Cache hashability matters.** Streamlit caching requires hashable arguments. This seemingly minor requirement shapes how you pass data between functions (tuples, not dicts).

4. **Library APIs change.** Plotly's `add_vline`, Streamlit's `use_container_width`, Pandas' `pd.np` — all broke or were deprecated during development. Use lower-level, more stable APIs when possible.

5. **Normalize before comparing.** You cannot plot $70 oil and $500 SPY on the same chart and learn anything useful. Percentage-change normalization is the most important transformation in comparative financial analysis.

6. **Correlate returns, not prices.** Two assets can have high price correlation simply because they both trend upward over time. Correlating daily returns reveals whether they actually respond to the same shocks.

### Design Lessons

7. **Natural language > rigid formats.** "Expected: up. Actual: up. Verdict: match." is boring after the second time. Flowing paragraphs that vary their word choice and structure keep users reading.

8. **Static text in a dynamic dashboard is a smell.** If your data changes but your explanations don't, users will notice the disconnect. Make every word data-driven or make it obviously permanent (like background education).

9. **The "30-second overview" test.** Users should be able to open the home page and understand the market situation in 30 seconds. Ring deep-dives are for the curious — the summary is for the busy.

10. **Structure the narrative before the code.** The "concentric rings" metaphor was designed first. The code followed. Having a clear story structure makes every implementation decision easier — you always know what each page needs to accomplish.

### Process Lessons

11. **Start simple, then iterate.** V1 was one page with basic charts. V6 has dynamic commentary, a multi-page architecture, and an executive summary. Each version added one major capability.

12. **User feedback drives the biggest improvements.** The shift from rigid Expected/Actual/Verdict format to natural paragraphs happened because of user feedback. The move from static to dynamic commentary happened because of user feedback. The best features weren't in the original plan.

13. **When something feels repetitive, automate the variation.** 28 assets with hand-written commentary would be a maintenance nightmare. The commentary engine generates unique text for each asset based on shared logic + per-asset expectations.

---

## Summary Stats

| Metric | Count |
|--------|-------|
| Total files | 8 (6 Python + requirements.txt + README.md) |
| Total lines of Python | ~1,500+ |
| Assets tracked | 28 |
| Pages | 6 (home + 5 rings) |
| Analysis functions | 7 (normalize, total_change, pct_change_period, max_drawdown, max_gain, volatility, correlation_matrix) |
| Chart types | Line, area fill, bar, heatmap, metric cards |
| Roadblocks hit | 8 major |
| Major iterations | 6 |
| Commentary variations | 3 tones (matched/surprised/muted) x momentum x drawdown layers |
