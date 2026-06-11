# 🎬 Media Log Dashboard

An interactive Streamlit dashboard that reads live from your Google Sheet and displays your media log data with charts, breakdowns, and analysis.

---

## What's in this repo

```
media_dashboard/
├── app.py              ← The entire dashboard (one file)
├── requirements.txt    ← Python packages Streamlit Cloud needs to install
└── README.md           ← This file
```

---

## Setup: Step by step

### 1. Make your Google Sheet public (view only)

Your app needs to read the sheet without logging in. Don't worry — it's read-only, nobody can edit it.

1. Open your Google Sheet
2. Click the green **Share** button (top right)
3. Under "General access", change **Restricted** → **Anyone with the link**
4. Make sure the role is set to **Viewer** (not Editor)
5. Click **Copy link** and save it — you'll need this URL

> ⚠️ Make sure you copy the URL of the **Raw Data** tab specifically. To do this, click the Raw Data tab first, then copy the URL from your browser (it should end in `#gid=XXXXXXX`).

---

### 2. Add this code to your GitHub repo

You already have a GitHub repo from your fragrance app. You can either:

**Option A: Add to your existing repo**
- Create a new folder called `media_dashboard/` 
- Add `app.py` and `requirements.txt` inside it

**Option B: Create a new repo (recommended)**
- Go to github.com → New repository
- Name it `media-log-dashboard`
- Upload `app.py` and `requirements.txt`

---

### 3. Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **New app**
3. Connect your GitHub repo
4. Set the **Main file path** to `app.py` (or `media_dashboard/app.py` if in a subfolder)
5. Click **Deploy**

Streamlit will install everything in `requirements.txt` automatically.

---

### 4. Link it from your Google Sheets form

Once deployed, Streamlit gives you a URL like:
```
https://your-name-media-log-dashboard-app-XXXXX.streamlit.app
```

To add a link from your Form sheet in Google Sheets:
1. Pick an empty cell on your Form sheet (e.g. D2)
2. Type: `=HYPERLINK("YOUR_STREAMLIT_URL", "📊 Open Dashboard")`
3. The cell will become a clickable link — tap it on your phone to open the dashboard

---

## Using the dashboard

1. Open the app in your browser
2. Paste your Google Sheet URL into the sidebar
3. Use the filters to explore by year, month, quarter, or medium
4. The data refreshes automatically every 5 minutes — or hit **Refresh data** to force it

---

## Sections in the dashboard

| Section | What it shows |
|---|---|
| At a glance | Total entries, films, books, rewatches, hyperfixations, avg rating |
| Medium & Format | Entry counts by medium; stacked bar of medium × format |
| Rewatch & Hyperfixation | Donut charts + rewatch rate by medium |
| Who with & Format | Who you watched with; stacked bar with format breakdown |
| Genre | Genre counts; genre × medium stacked bar |
| Ratings | Distribution, avg by medium, avg by genre |
| Best & Worst rated | Top 10 and bottom 10 tables |
| Trends (full year only) | Monthly entries, cumulative line, avg rating trend, genre drift |
| Bonus analysis | Avg rating by social context, recommended breakdown |
| Raw data | Full expandable table of all entries |

---

## Troubleshooting

**"Could not load sheet"**  
→ Check the sheet is set to "Anyone with the link can view"  
→ Make sure you're pasting the Raw Data tab URL (with `#gid=`)

**Dates showing wrong**  
→ Your dates must be in DD/MM/YYYY format in the sheet. Check column A.

**A chart is missing**  
→ That chart requires a column that might be empty for your current filter. Try "Full Year" view.

**Dropdowns not appearing in filters**  
→ Make sure column names in your sheet exactly match: Medium, Genre, Format, With?, Rewatch?, Hyperfixation?, Recommended?
