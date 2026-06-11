# Media Log Dashboard

An interactive Streamlit dashboard that reads live from a Google Sheet and displays your media log data with charts, breakdowns, and analysis.

---

## What's in this repo

```
media_dashboard/
├── app.py              ← The entire dashboard (one file)
├── requirements.txt    ← Python packages Streamlit Cloud needs to install
└── README.md           ← This file
```

## Using the dashboard

1. Open the app in your browser
2. Paste your Google Sheet URL into the sidebar
3. Use the filters to explore by year, month, quarter, or medium
4. The data refreshes automatically every 5 minutes, or hit **Refresh data** to force it

---

## Sections in the dashboard

| Section | What it shows |
|---|---|
| At a glance | Total entries, films, books, rewatches, hyperfixations, avg rating |
| Medium & Format | Entry counts by medium; stacked bar of medium x format |
| Rewatch & Hyperfixation | Donut charts + rewatch rate by medium |
| Who with & Format | Who you watched with; stacked bar with format breakdown |
| Genre | Genre counts; genre x medium stacked bar |
| Ratings | Distribution, avg by medium, avg by genre |
| Best & Worst rated | Top 10 and bottom 10 tables |
| Trends (full year only) | Monthly entries, cumulative line, avg rating trend, genre drift |
| Bonus analysis | Avg rating by social context, recommended breakdown |
| Raw data | Full expandable table of all entries |

---


