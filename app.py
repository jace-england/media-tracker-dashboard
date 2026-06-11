"""
Media Log Dashboard
-------------------
Reads live from a public Google Sheet and renders an interactive dashboard.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import io
import requests

# ─────────────────────────────────────────────
# PAGE CONFIG
# Must be the very first Streamlit call in the script.
# layout="wide" uses the full browser width instead of a narrow centred column.
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Media Log 2026",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# COLOUR PALETTE
# Centralised so you can retheme everything by changing these values.
# ─────────────────────────────────────────────
COLOURS = {
    "Film":        "#4F86C6",
    "TV":          "#E07B54",
    "Book":        "#6DBF82",
    "Anime":       "#B57EDC",
    "Documentary": "#F0C040",
    "Video Game":  "#E05C8A",
    "Manga":       "#50C8C0",
    "Music":       "#FF8C42",
    "Podcast":     "#7EC8E3",
    "Stage Show":  "#C8A882",
    "Web Series":  "#A0C878",
}
FALLBACK_COLOURS = px.colors.qualitative.Pastel
STAR = "⭐"
BG = "#0E1117"          # Streamlit dark background
CARD_BG = "#1E2130"     # Slightly lighter card background


# ─────────────────────────────────────────────
# CUSTOM CSS
# Injects CSS into the page to style metric cards and other elements.
# st.markdown with unsafe_allow_html=True lets us write raw HTML/CSS.
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Metric cards */
    .metric-card {
        background-color: #1E2130;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
        border: 1px solid #2D3250;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.1;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #8B95A8;
        margin-top: 6px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-sub {
        font-size: 0.85rem;
        color: #4F86C6;
        margin-top: 4px;
    }
    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #C9D1E0;
        margin-bottom: 4px;
        margin-top: 8px;
    }
    /* Divider */
    hr { border-color: #2D3250; }
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────

def get_colour(medium):
    """Return a hex colour for a given medium string."""
    return COLOURS.get(medium, FALLBACK_COLOURS[hash(medium) % len(FALLBACK_COLOURS)])


@st.cache_data(ttl=300)  # Cache for 5 minutes so the app doesn't hammer Google Sheets
def load_data(sheet_url: str) -> pd.DataFrame:
    """
    Fetch data from a public Google Sheet.

    Google Sheets can export any sheet as CSV via a special URL format:
        .../spreadsheets/d/{SHEET_ID}/export?format=csv&gid={TAB_GID}

    The function converts the export URL, fetches the CSV, and returns
    a cleaned DataFrame.

    ttl=300 means Streamlit will use the cached version for 5 minutes
    before re-fetching. Increase this if you want less frequent updates.
    """
    # Convert "share" URL to CSV export URL
    # e.g. https://docs.google.com/spreadsheets/d/ABC123/edit#gid=0
    #   -> https://docs.google.com/spreadsheets/d/ABC123/export?format=csv&gid=0
    if "/edit" in sheet_url:
        base = sheet_url.split("/edit")[0]
        gid = sheet_url.split("gid=")[-1] if "gid=" in sheet_url else "0"
        csv_url = f"{base}/export?format=csv&gid={gid}"
    elif "/export" in sheet_url:
        csv_url = sheet_url
    else:
        csv_url = sheet_url + "/export?format=csv"

    response = requests.get(csv_url, timeout=15)
    response.raise_for_status()

    df = pd.read_csv(io.StringIO(response.text))

    # ── Clean column names ──
    # Strip any accidental whitespace from headers
    df.columns = df.columns.str.strip()

    # ── Parse dates ──
    # Try DD/MM/YYYY first (your format), fall back to pandas auto-detection
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

    # ── Derive useful columns ──
    df["Month"] = df["Date"].dt.month                          # 1–12
    df["Month_Name"] = df["Date"].dt.strftime("%b")           # Jan, Feb…
    df["Month_Year"] = df["Date"].dt.strftime("%b %Y")        # Jan 2026
    df["Quarter"] = df["Date"].dt.quarter                     # 1–4
    df["Quarter_Name"] = "Q" + df["Date"].dt.quarter.astype(str)  # Q1, Q2…
    df["Year"] = df["Date"].dt.year

    # ── Normalise Rating to float ──
    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")

    # ── Normalise text fields ──
    for col in ["Medium", "Genre", "Format", "With?", "Rewatch?", "Hyperfixation?", "Recommended?"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace("nan", pd.NA)

    # Drop rows with no date or no media title
    df = df.dropna(subset=["Date", "Media"])

    return df


def metric_card(value, label, sub=None):
    """Render a styled metric card using HTML."""
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def stars(rating):
    """Convert a numeric rating to a star string, e.g. 4 → ⭐⭐⭐⭐"""
    if pd.isna(rating):
        return "–"
    return STAR * int(round(rating))


# ─────────────────────────────────────────────
# SIDEBAR
# The sidebar holds the Google Sheet URL input and all filters.
# st.sidebar.xxx puts widgets in the collapsible side panel.
# ─────────────────────────────────────────────

with st.sidebar:
    st.title("🎬 Media Log")
    st.caption("Dashboard settings")
    st.divider()

    # ── Sheet URL ──
    sheet_url = st.text_input(
        "Google Sheet URL",
        placeholder="Paste your Google Sheet URL here",
        help="Your sheet must be set to 'Anyone with the link can view'. "
             "Make sure you're sharing the Raw Data tab URL.",
    )

    st.divider()
    st.markdown("**Filters**")

    if sheet_url:
        try:
            df_raw = load_data(sheet_url)

            # ── Year filter ──
            years = sorted(df_raw["Year"].dropna().unique().astype(int))
            selected_year = st.selectbox("Year", years, index=len(years) - 1)

            # ── Time period ──
            period = st.radio(
                "View by",
                ["Full Year", "Monthly", "Quarterly"],
                horizontal=True,
            )

            if period == "Monthly":
                months = list(range(1, 13))
                month_names = [datetime(2026, m, 1).strftime("%B") for m in months]
                selected_month = st.selectbox(
                    "Month",
                    months,
                    format_func=lambda m: datetime(2026, m, 1).strftime("%B"),
                )
            elif period == "Quarterly":
                selected_quarter = st.selectbox("Quarter", [1, 2, 3, 4],
                                                format_func=lambda q: f"Q{q}")

            # ── Medium filter ──
            all_mediums = sorted(df_raw["Medium"].dropna().unique())
            selected_mediums = st.multiselect(
                "Medium",
                all_mediums,
                default=all_mediums,
                help="Filter to specific media types",
            )

            st.divider()
            st.caption(f"Last refreshed: {datetime.now().strftime('%H:%M:%S')}")
            if st.button("🔄 Refresh data"):
                st.cache_data.clear()
                st.rerun()

        except Exception as e:
            st.error(f"Could not load sheet: {e}")
            st.stop()
    else:
        st.info("👆 Paste your Google Sheet URL above to get started.")
        st.stop()


# ─────────────────────────────────────────────
# FILTER DATA
# Apply the sidebar selections to get the working DataFrame.
# ─────────────────────────────────────────────

df = df_raw[df_raw["Year"] == selected_year].copy()

if period == "Monthly":
    df = df[df["Month"] == selected_month]
    period_label = datetime(selected_year, selected_month, 1).strftime("%B %Y")
elif period == "Quarterly":
    df = df[df["Quarter"] == selected_quarter]
    period_label = f"Q{selected_quarter} {selected_year}"
else:
    period_label = str(selected_year)

if selected_mediums:
    df = df[df["Medium"].isin(selected_mediums)]

if df.empty:
    st.warning("No entries found for the selected filters.")
    st.stop()


# ─────────────────────────────────────────────
# HELPER: ordered month labels for charts
# ─────────────────────────────────────────────
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ─────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────

st.title(f"🎬 Media Log — {period_label}")
st.caption("Live data from Google Sheets · Refreshes every 5 minutes")
st.divider()


# ─────────────────────────────────────────────
# SECTION 1: SUMMARY SCORECARDS
# ─────────────────────────────────────────────

st.markdown('<div class="section-header">At a glance</div>', unsafe_allow_html=True)

total = len(df)
rewatches = (df["Rewatch?"] == "Yes").sum()
rewatch_pct = f"{rewatches / total * 100:.0f}% rewatches" if total else "–"
hyperfixations = (df["Hyperfixation?"] == "Yes").sum()
avg_rating = df["Rating"].mean()
avg_rating_str = f"{avg_rating:.1f} / 5" if not pd.isna(avg_rating) else "–"

# Count most-watched medium
top_medium = df["Medium"].value_counts().idxmax() if not df["Medium"].isna().all() else "–"
top_medium_count = df["Medium"].value_counts().max() if not df["Medium"].isna().all() else 0

cols = st.columns(6)
with cols[0]: metric_card(total, "Total entries")
with cols[1]: metric_card(df["Medium"].value_counts().get("Film", 0), "Films")
with cols[2]: metric_card(df["Medium"].value_counts().get("Book", 0), "Books")
with cols[3]: metric_card(rewatches, "Rewatches", rewatch_pct)
with cols[4]: metric_card(hyperfixations, "Hyperfixations",
                           f"{hyperfixations / total * 100:.0f}% of total" if total else "–")
with cols[5]: metric_card(avg_rating_str, "Avg rating")

st.divider()


# ─────────────────────────────────────────────
# SECTION 2: MEDIUM & FORMAT
# ─────────────────────────────────────────────

st.markdown('<div class="section-header">Medium & Format</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    # ── Medium breakdown (bar chart) ──
    med_counts = df["Medium"].value_counts().reset_index()
    med_counts.columns = ["Medium", "Count"]
    colour_map = {m: get_colour(m) for m in med_counts["Medium"]}

    fig = px.bar(
        med_counts, x="Medium", y="Count",
        color="Medium", color_discrete_map=colour_map,
        title="Entries by Medium",
        text="Count",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, plot_bgcolor=BG, paper_bgcolor=BG,
                      font_color="#C9D1E0", margin=dict(t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # ── Medium + Format stacked bar ──
    if "Format" in df.columns:
        mf = (df.groupby(["Medium", "Format"]).size()
                .reset_index(name="Count"))
        fig2 = px.bar(
            mf, x="Medium", y="Count", color="Format",
            title="Medium by Format",
            barmode="stack",
        )
        fig2.update_layout(plot_bgcolor=BG, paper_bgcolor=BG,
                           font_color="#C9D1E0", margin=dict(t=40, b=20))
        st.plotly_chart(fig2, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# SECTION 3: REWATCH & HYPERFIXATION
# ─────────────────────────────────────────────

st.markdown('<div class="section-header">Rewatch & Hyperfixation</div>', unsafe_allow_html=True)
col3, col4, col5 = st.columns(3)

with col3:
    rw = df["Rewatch?"].value_counts().reset_index()
    rw.columns = ["Answer", "Count"]
    fig_rw = px.pie(rw, names="Answer", values="Count",
                    title="Rewatch?",
                    color_discrete_sequence=["#4F86C6", "#E07B54"],
                    hole=0.45)
    fig_rw.update_layout(paper_bgcolor=BG, font_color="#C9D1E0", margin=dict(t=40))
    st.plotly_chart(fig_rw, use_container_width=True)

with col4:
    hf = df["Hyperfixation?"].value_counts().reset_index()
    hf.columns = ["Answer", "Count"]
    fig_hf = px.pie(hf, names="Answer", values="Count",
                    title="Hyperfixation?",
                    color_discrete_sequence=["#B57EDC", "#E07B54"],
                    hole=0.45)
    fig_hf.update_layout(paper_bgcolor=BG, font_color="#C9D1E0", margin=dict(t=40))
    st.plotly_chart(fig_hf, use_container_width=True)

with col5:
    # Rewatch rate by Medium
    rw_by_medium = (df[df["Rewatch?"].isin(["Yes", "No"])]
                    .groupby("Medium")["Rewatch?"]
                    .apply(lambda x: (x == "Yes").sum() / len(x) * 100)
                    .reset_index(name="Rewatch %")
                    .sort_values("Rewatch %", ascending=True))
    fig_rwm = px.bar(rw_by_medium, x="Rewatch %", y="Medium",
                     orientation="h",
                     title="Rewatch rate by Medium (%)",
                     color="Rewatch %",
                     color_continuous_scale="Blues")
    fig_rwm.update_layout(plot_bgcolor=BG, paper_bgcolor=BG,
                           font_color="#C9D1E0", margin=dict(t=40, b=20),
                           coloraxis_showscale=False)
    st.plotly_chart(fig_rwm, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# SECTION 4: WHO WITH & FORMAT
# ─────────────────────────────────────────────

st.markdown('<div class="section-header">Who watched with & Format</div>', unsafe_allow_html=True)
col6, col7 = st.columns(2)

with col6:
    if "With?" in df.columns:
        with_counts = df["With?"].value_counts().reset_index()
        with_counts.columns = ["With", "Count"]
        fig_with = px.bar(with_counts, x="Count", y="With",
                          orientation="h",
                          title="Who you watched with",
                          color="Count",
                          color_continuous_scale="Teal",
                          text="Count")
        fig_with.update_traces(textposition="outside")
        fig_with.update_layout(showlegend=False, plot_bgcolor=BG,
                                paper_bgcolor=BG, font_color="#C9D1E0",
                                margin=dict(t=40, b=20),
                                coloraxis_showscale=False,
                                yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_with, use_container_width=True)

with col7:
    if "With?" in df.columns and "Format" in df.columns:
        wf = (df.groupby(["With?", "Format"]).size()
                .reset_index(name="Count"))
        fig_wf = px.bar(wf, x="With?", y="Count", color="Format",
                        barmode="stack",
                        title="Who with × Format")
        fig_wf.update_layout(plot_bgcolor=BG, paper_bgcolor=BG,
                              font_color="#C9D1E0", margin=dict(t=40, b=20))
        st.plotly_chart(fig_wf, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# SECTION 5: GENRE
# ─────────────────────────────────────────────

st.markdown('<div class="section-header">Genre</div>', unsafe_allow_html=True)
col8, col9 = st.columns(2)

with col8:
    if "Genre" in df.columns:
        genre_counts = df["Genre"].value_counts().reset_index()
        genre_counts.columns = ["Genre", "Count"]
        fig_genre = px.bar(genre_counts, x="Count", y="Genre",
                           orientation="h",
                           title="Entries by Genre",
                           color="Count",
                           color_continuous_scale="Purp",
                           text="Count")
        fig_genre.update_traces(textposition="outside")
        fig_genre.update_layout(showlegend=False, plot_bgcolor=BG,
                                 paper_bgcolor=BG, font_color="#C9D1E0",
                                 margin=dict(t=40, b=20),
                                 coloraxis_showscale=False,
                                 yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_genre, use_container_width=True)

with col9:
    if "Genre" in df.columns:
        gm = (df.groupby(["Genre", "Medium"]).size()
                .reset_index(name="Count"))
        colour_map = {m: get_colour(m) for m in gm["Medium"].unique()}
        fig_gm = px.bar(gm, x="Genre", y="Count", color="Medium",
                        barmode="stack",
                        title="Genre × Medium",
                        color_discrete_map=colour_map)
        fig_gm.update_layout(plot_bgcolor=BG, paper_bgcolor=BG,
                              font_color="#C9D1E0",
                              margin=dict(t=40, b=20),
                              xaxis_tickangle=-35)
        st.plotly_chart(fig_gm, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# SECTION 6: RATINGS
# ─────────────────────────────────────────────

st.markdown('<div class="section-header">Ratings</div>', unsafe_allow_html=True)
col10, col11, col12 = st.columns(3)

with col10:
    # Rating distribution
    rated = df.dropna(subset=["Rating"])
    if not rated.empty:
        dist = (rated["Rating"].value_counts()
                               .reset_index()
                               .sort_values("Rating"))
        dist.columns = ["Rating", "Count"]
        dist["Stars"] = dist["Rating"].apply(lambda r: STAR * int(r))
        fig_dist = px.bar(dist, x="Stars", y="Count",
                          title="Rating distribution",
                          color="Rating",
                          color_continuous_scale="YlOrRd",
                          text="Count")
        fig_dist.update_traces(textposition="outside")
        fig_dist.update_layout(showlegend=False, plot_bgcolor=BG,
                                paper_bgcolor=BG, font_color="#C9D1E0",
                                coloraxis_showscale=False,
                                margin=dict(t=40, b=20))
        st.plotly_chart(fig_dist, use_container_width=True)

with col11:
    # Avg rating by Medium
    avg_by_med = (df.dropna(subset=["Rating"])
                    .groupby("Medium")["Rating"]
                    .mean()
                    .reset_index(name="Avg Rating")
                    .sort_values("Avg Rating"))
    colour_map = {m: get_colour(m) for m in avg_by_med["Medium"]}
    fig_avg = px.bar(avg_by_med, x="Avg Rating", y="Medium",
                     orientation="h",
                     title="Avg rating by Medium",
                     color="Medium",
                     color_discrete_map=colour_map,
                     text=avg_by_med["Avg Rating"].round(1))
    fig_avg.update_traces(textposition="outside")
    fig_avg.update_layout(showlegend=False, plot_bgcolor=BG,
                           paper_bgcolor=BG, font_color="#C9D1E0",
                           margin=dict(t=40, b=20),
                           xaxis_range=[0, 5.5])
    st.plotly_chart(fig_avg, use_container_width=True)

with col12:
    # Avg rating by Genre
    avg_by_genre = (df.dropna(subset=["Rating"])
                      .groupby("Genre")["Rating"]
                      .mean()
                      .reset_index(name="Avg Rating")
                      .sort_values("Avg Rating"))
    fig_avg_g = px.bar(avg_by_genre, x="Avg Rating", y="Genre",
                        orientation="h",
                        title="Avg rating by Genre",
                        color="Avg Rating",
                        color_continuous_scale="Purp",
                        text=avg_by_genre["Avg Rating"].round(1))
    fig_avg_g.update_traces(textposition="outside")
    fig_avg_g.update_layout(showlegend=False, plot_bgcolor=BG,
                              paper_bgcolor=BG, font_color="#C9D1E0",
                              coloraxis_showscale=False,
                              margin=dict(t=40, b=20),
                              xaxis_range=[0, 5.5])
    st.plotly_chart(fig_avg_g, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# SECTION 7: BEST & WORST
# ─────────────────────────────────────────────

st.markdown('<div class="section-header">Best & Worst rated</div>', unsafe_allow_html=True)
col13, col14 = st.columns(2)

rated_df = df.dropna(subset=["Rating"]).sort_values("Rating", ascending=False)

def format_table(frame):
    """Format a DataFrame for display: add star column, clean index."""
    display = frame[["Media", "Medium", "Genre", "Rating"]].copy()
    display["Rating"] = display["Rating"].apply(stars)
    display = display.reset_index(drop=True)
    display.index += 1
    return display

with col13:
    st.markdown("**🌟 Top rated**")
    top5 = rated_df.head(10)
    st.dataframe(format_table(top5), use_container_width=True, hide_index=False)

with col14:
    st.markdown("**💀 Bottom rated**")
    bot5 = rated_df.tail(10).sort_values("Rating")
    st.dataframe(format_table(bot5), use_container_width=True, hide_index=False)

st.divider()


# ─────────────────────────────────────────────
# SECTION 8: TIME TRENDS (full year only)
# ─────────────────────────────────────────────

if period == "Full Year":
    st.markdown('<div class="section-header">Trends over the year</div>',
                unsafe_allow_html=True)

    col15, col16 = st.columns(2)

    with col15:
        # Entries per month (stacked by medium)
        monthly = (df.groupby(["Month_Name", "Medium"]).size()
                     .reset_index(name="Count"))
        # Sort months correctly
        monthly["Month_Name"] = pd.Categorical(
            monthly["Month_Name"], categories=MONTH_ORDER, ordered=True)
        monthly = monthly.sort_values("Month_Name")
        colour_map = {m: get_colour(m) for m in monthly["Medium"].unique()}
        fig_trend = px.bar(monthly, x="Month_Name", y="Count",
                           color="Medium",
                           color_discrete_map=colour_map,
                           title="Entries per month by Medium",
                           barmode="stack")
        fig_trend.update_layout(plot_bgcolor=BG, paper_bgcolor=BG,
                                 font_color="#C9D1E0", margin=dict(t=40, b=20))
        st.plotly_chart(fig_trend, use_container_width=True)

    with col16:
        # Cumulative entries line chart
        daily = (df.groupby("Date").size()
                   .reset_index(name="Count")
                   .sort_values("Date"))
        daily["Cumulative"] = daily["Count"].cumsum()
        fig_cum = px.line(daily, x="Date", y="Cumulative",
                          title="Cumulative entries over the year",
                          markers=False)
        fig_cum.update_traces(line_color="#4F86C6", line_width=2)
        fig_cum.update_layout(plot_bgcolor=BG, paper_bgcolor=BG,
                               font_color="#C9D1E0", margin=dict(t=40, b=20))
        st.plotly_chart(fig_cum, use_container_width=True)

    col17, col18 = st.columns(2)

    with col17:
        # Monthly avg rating trend
        avg_month = (df.dropna(subset=["Rating"])
                       .groupby("Month_Name")["Rating"]
                       .mean()
                       .reset_index(name="Avg Rating"))
        avg_month["Month_Name"] = pd.Categorical(
            avg_month["Month_Name"], categories=MONTH_ORDER, ordered=True)
        avg_month = avg_month.sort_values("Month_Name")
        fig_avgm = px.line(avg_month, x="Month_Name", y="Avg Rating",
                           title="Average rating per month",
                           markers=True)
        fig_avgm.update_traces(line_color="#E07B54", line_width=2, marker_size=8)
        fig_avgm.update_layout(plot_bgcolor=BG, paper_bgcolor=BG,
                                font_color="#C9D1E0", margin=dict(t=40, b=20),
                                yaxis_range=[0, 5.5])
        st.plotly_chart(fig_avgm, use_container_width=True)

    with col18:
        # Genre drift: genre share per month (top 6 genres)
        top_genres = df["Genre"].value_counts().head(6).index.tolist()
        genre_month = (df[df["Genre"].isin(top_genres)]
                         .groupby(["Month_Name", "Genre"]).size()
                         .reset_index(name="Count"))
        genre_month["Month_Name"] = pd.Categorical(
            genre_month["Month_Name"], categories=MONTH_ORDER, ordered=True)
        genre_month = genre_month.sort_values("Month_Name")
        fig_gd = px.bar(genre_month, x="Month_Name", y="Count",
                        color="Genre",
                        barmode="stack",
                        title="Genre drift over the year (top 6)",
                        color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_gd.update_layout(plot_bgcolor=BG, paper_bgcolor=BG,
                              font_color="#C9D1E0", margin=dict(t=40, b=20))
        st.plotly_chart(fig_gd, use_container_width=True)

    st.divider()


# ─────────────────────────────────────────────
# SECTION 9: BONUS ANALYSIS
# ─────────────────────────────────────────────

st.markdown('<div class="section-header">Bonus analysis</div>', unsafe_allow_html=True)
col19, col20 = st.columns(2)

with col19:
    # Avg rating by social context (With?)
    if "With?" in df.columns:
        avg_with = (df.dropna(subset=["Rating"])
                      .groupby("With?")["Rating"]
                      .agg(["mean", "count"])
                      .reset_index()
                      .rename(columns={"mean": "Avg Rating", "count": "n"})
                      .query("n >= 2")   # only show groups with at least 2 entries
                      .sort_values("Avg Rating"))
        fig_aw = px.bar(avg_with, x="Avg Rating", y="With?",
                        orientation="h",
                        title="Avg rating by who you watched with",
                        color="Avg Rating",
                        color_continuous_scale="Teal",
                        text=avg_with["Avg Rating"].round(1),
                        hover_data={"n": True})
        fig_aw.update_traces(textposition="outside")
        fig_aw.update_layout(showlegend=False, plot_bgcolor=BG,
                              paper_bgcolor=BG, font_color="#C9D1E0",
                              coloraxis_showscale=False,
                              margin=dict(t=40, b=20),
                              xaxis_range=[0, 5.5])
        st.plotly_chart(fig_aw, use_container_width=True)

with col20:
    # Recommended breakdown
    if "Recommended?" in df.columns:
        rec = df["Recommended?"].value_counts().reset_index()
        rec.columns = ["Answer", "Count"]
        fig_rec = px.pie(rec, names="Answer", values="Count",
                         title="Would you recommend?",
                         color_discrete_sequence=["#6DBF82", "#E05C8A", "#F0C040"],
                         hole=0.45)
        fig_rec.update_layout(paper_bgcolor=BG, font_color="#C9D1E0",
                               margin=dict(t=40))
        st.plotly_chart(fig_rec, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# SECTION 10: RAW DATA TABLE
# Expandable so it doesn't clutter the page.
# ─────────────────────────────────────────────

with st.expander("📋 View raw data"):
    display_df = df.copy()
    display_df["Date"] = display_df["Date"].dt.strftime("%d/%m/%Y")
    display_df["Rating"] = display_df["Rating"].apply(stars)
    st.dataframe(
        display_df[["Date", "Media", "Medium", "Genre", "Format",
                    "With?", "Rewatch?", "Hyperfixation?", "Rating",
                    "Recommended?", "Review"]],
        use_container_width=True,
        hide_index=True,
    )
