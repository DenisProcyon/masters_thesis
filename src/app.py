import streamlit as st
import asyncio
import geopandas as gpd
import json
import time
import os
from urllib.parse import urlencode
from uuid import uuid4

from yt_production import analyze_all_states
from tg_production import launch
from telegram_pplt import download_posts

# ─────────────────────────── Constants ───────────────────────────────────────
GRAFANA_BASE_URL = os.getenv(
    "GRAFANA_BASE_URL",
    "http://localhost:3000/d/your_dashboard_uid/social-pulse",
)

# ─────────────────────────── Streamlit UI ─────────────────────────────────────
st.set_page_config(
    page_title="Social Pulse • Launcher",
    page_icon="🚀",
    layout="centered",
)
st.title("🚀 Social Pulse — Launch Scraping & ML Pipeline")

# --- Country Selection --------------------------------------------------------
if "country" not in st.session_state:
    st.session_state.country = "MX"
selected_country = st.selectbox(
    "Country of Analysis",
    ["MX", "BR", "US"],
    index=["MX", "BR", "US"].index(st.session_state.country),
)
st.session_state.country = selected_country

# --- Years Input -------------------------------------------------------------
years_input = st.text_input(
    "Years (range with hyphen)",
    value="2020-2022"
)

def parse_years(raw: str) -> list[int]:
    year_set = set()
    for part in raw.split(","):
        part = part.strip()
        if "-" in part:
            start, end = [int(x) for x in part.split("-", 1)]
            year_set.update(range(start, end + 1))
        elif part:
            year_set.add(int(part))
    return sorted(year_set)

years = parse_years(years_input)
if not years:
    st.warning("Please specify at least one year (e.g., 2020 or range 2018-2021).")
    st.stop()
st.markdown(f"**Selected years:** {years}")

# --- Social Factors Editor ---------------------------------------------------
if "factors" not in st.session_state:
    st.session_state.factors = [
        {"id": str(uuid4())[:8], "name": "food_access", "keywords": ["food", "hunger"]}
    ]

def add_factor():
    st.session_state.factors.append({"id": str(uuid4())[:8], "name": "", "keywords": []})

def remove_factor(factor_id: str):
    st.session_state.factors = [
        f for f in st.session_state.factors if f["id"] != factor_id
    ]

st.markdown("## 🗂️ Social Factors & Keywords")
for factor in st.session_state.factors:
    cols = st.columns([2, 5, 1])
    factor["name"] = cols[0].text_input(
        "Factor", value=factor["name"], key=f"factor_{factor['id']}"
    )
    kw_raw = cols[1].text_input(
        "Keywords (comma-separated)",
        value=", ".join(factor["keywords"]),
        key=f"kw_{factor['id']}"
    )
    factor["keywords"] = [k.strip() for k in kw_raw.split(",") if k.strip()]
    cols[2].button(
        "❌", key=f"del_{factor['id']}", on_click=remove_factor, args=(factor["id"],)
    )
    st.markdown("---")
st.button("➕ Add Factor", on_click=add_factor)

# --- Data Sources ------------------------------------------------------------
st.markdown("## 📡 Data Sources")

tg_raw = st.text_input(
    "Telegram Channels (comma-separated)",
    value="",
    help="Format: @channel1, @channel2, ..."
)
selected_tg = [c.strip() for c in tg_raw.split(",") if c.strip()]

sources = {
    "telegram": selected_tg
}

st.markdown("## 📁 GeoJSON Upload")
geojson_file = st.file_uploader(
    "Upload GeoJSON File",
    type=["geojson", "json"],
    help="Upload a GeoJSON file with region boundaries"
)
geojson_str = None
if geojson_file is not None:
    geojson_str = geojson_file.read().decode("utf-8")
    st.success("GeoJSON file loaded successfully!")

if "module1_done" not in st.session_state:
    st.session_state.module1_done = False
if "module2_done" not in st.session_state:
    st.session_state.module2_done = False

def run_youtube_parser(states: list[str], dimensions: dict[str, str]):
    data = analyze_all_states(
        start_year=years[0],
        end_year=years[-1],
        states=states,
        dimensions=dimensions
    )

    return data

def get_regions(geojson: str):
    data = json.loads(geojson)

    features = data["features"]

    gdf = gpd.GeoDataFrame.from_features(features)

    return gdf["state_name"].tolist()

def format_dimensions(dimensions: dict) -> dict[str, str]:
    result = {}
    for dimension in dimensions:
        result[dimension["name"].upper()] = " ".join(dimension["keywords"])

    return result

st.markdown("## 🚀 Launch")

if st.button("Run Pipeline"):
    st.session_state.module1_done = False
    st.session_state.module2_done = False

    progress = st.progress(0)

    if geojson_str is None:
        st.error("❌ Please upload GeoJSON")
    else:
        with st.spinner("1/6: Parsing GeoJSON..."):
            st.session_state.regions = get_regions(geojson_str)
            st.session_state.module1_done = True
        st.success("✅ GeoJSON parsing done")
        progress.progress(20)

        # with st.spinner("2/6: Downloading and Parsing YouTube Data Source..."):
        #     dims = format_dimensions(st.session_state.factors)
        #     st.session_state.yt_data = run_youtube_parser(
        #         states=st.session_state.regions,
        #         dimensions=dims,
        #     )
        # st.success("✅ YouTube parsing done")
        # progress.progress(40)

        # with st.spinner("3/6: Downloading data from Telegram..."):
        #    asyncio.run(download_posts(selected_tg, years[0], years[-1]))
        # st.success("✅ Telegram data downloaded")
        # progress.progress(60)

        with st.spinner("4/6: Processing Telegram data"):
            dims = format_dimensions(st.session_state.factors)
            st.session_state.tg_data = launch(
                start_year=years[0],
                end_year=years[-1],
                states=st.session_state.regions,
                dimensions=dims,
                channel_collections=[f'{i.replace("@", "")}_{years[0]}_{years[-1]}' for i in selected_tg]
            )
        st.success("✅ Telegram data processed")
        progress.progress(60)

        with st.spinner("5/6: Processing Telegram data..."):
            st.session_state = analyze_all_states()
        st.success("✅ ML Pipeline done")
        progress.progress(60)

        st.balloons()
