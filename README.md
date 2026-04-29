# The Ripple Effect: How the US-Iran Conflict Reshaped Global Markets

## Core Question

**When a geopolitical conflict occurs, how does the shock radiate from the epicenter outward — across commodities, regions, sectors, and individual companies?**

## The Concept

This dashboard visualizes market impact as **concentric rings** radiating from the epicenter of the US-Iran conflict (February 28, 2026). Each ring represents a layer further from the direct impact zone.

```
Ring 1 — Oil & Energy (Epicenter)
  Ring 2 — Regional Markets (Contagion)
    Ring 3 — Sector Winners & Losers
      Ring 4 — Company Spotlight
        Ring 5 — Fear & Safety Gauges
```

## What the Dashboard Shows

### At a Glance
Top-level scoreboard showing total % change for 8 key indicators since the conflict started.

### Ring 1 — The Epicenter: Oil & Energy
- Crude Oil (WTI), Brent Crude, Natural Gas
- Price-per-barrel tracker
- Key escalation milestones marked on all charts

### Ring 2 — Regional Contagion
- 7 regional indices: US (SPY), Europe (VGK), Saudi Arabia (KSA), Turkey (TUR), Emerging Markets (EEM), Japan (EWJ), China (FXI)
- Normalized overlay chart to compare which regions were hit hardest
- Regional impact scorecard with 7-day and total % changes

### Ring 3 — Sector Winners & Losers
- 7 US sectors tracked: Energy, Defense, Airlines, Tech, Financials, Healthcare, Consumer Discretionary
- Split into **Winners** and **Losers** divergence charts
- All-sectors overlay in expandable view

### Ring 4 — Company Spotlight
- **Defense:** Lockheed Martin (LMT), RTX/Raytheon (RTX)
- **Oil Majors:** ExxonMobil (XOM), Chevron (CVX)
- **Airlines:** Delta (DAL), United (UAL)
- Individual charts per group with actual % change callouts

### Ring 5 — Fear & Safety Gauges
- VIX (fear), Gold (GLD), US Treasuries (TLT), US Dollar (UUP)
- Shows where scared money went

### The Full Story
Step-by-step propagation narrative with actual data — how the shock traveled from oil to regions to sectors to safe havens.

## Assets Tracked (28 total)

| Ring | Assets | Tickers |
|------|--------|---------|
| Epicenter | Crude Oil WTI, Brent Crude, Natural Gas | CL=F, BZ=F, NG=F |
| Regional | US, Europe, Saudi Arabia, Turkey, EM, Japan, China | SPY, VGK, KSA, TUR, EEM, EWJ, FXI |
| Sectors | Energy, Defense, Airlines, Tech, Financials, Healthcare, Consumer | XLE, ITA, JETS, XLK, XLF, XLV, XLY |
| Companies | Lockheed, RTX, Exxon, Chevron, Delta, United | LMT, RTX, XOM, CVX, DAL, UAL |
| Safety | VIX, Gold, Treasuries, Dollar | ^VIX, GLD, TLT, UUP |

## Features

- **Adjustable date range** via sidebar — zoom in on specific escalation periods
- **Key milestone markers** on all charts — see exactly when events happened
- **Normalized % change view** — compare assets on the same scale regardless of price
- **Winners vs Losers split** — sector divergence at a glance
- **Full propagation narrative** — data-driven storytelling, not just charts

## Tech Stack

- **Python 3**
- **Streamlit** — dashboard UI
- **yfinance** — market data (free, no API key)
- **Plotly** — interactive charts
- **Pandas** — data processing

## Setup & Run

```bash
cd geopolitical-market-dashboard
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`.

## Steps Taken

1. **Defined the narrative** — "ripple effect" metaphor: shock radiates outward in rings
2. **Selected 28 assets** across 5 rings, each representing a different distance from the epicenter
3. **Built the timeline** — key conflict milestones marked across all charts for context
4. **Designed ring-by-ring sections** — each ring tells a different part of the story
5. **Added divergence analysis** — sectors split into winners/losers, not just listed
6. **Company-level drill-down** — defense, oil, airlines grouped by exposure type
7. **Fear & safety analysis** — tracking where capital fled, not just what fell
8. **Propagation narrative** — final section ties all rings together into a single story

## Future Ideas

- Correlation heatmap: which assets moved together vs diverged?
- Volume analysis: did trading volume spike alongside price moves?
- Sentiment overlay: news headline sentiment mapped to price action
- Historical comparison: overlay with 2020 Iran-US tensions or 2022 Russia-Ukraine
- Strait of Hormuz shipping tracker: vessel traffic data as a real-time risk gauge
