import streamlit as st
import asyncio
import geopandas as gpd
import json
import time
import os
from urllib.parse import urlencode
from uuid import uuid4
from datetime import date

from yt_production import analyze_all_states as analyze_yt
from tg_production import launch as analyze_tg
from telegram_pplt import download_posts
from gt_production import run_google_trends
from serpapi_production import fetch_timeseries_data
from mediacloud_production import fetch_news_data as fetch_mediacloud_data
from google_news_production import fetch_gnews_data
from google_news_production.decoder import decode_gnews_links
from trafilatura_production import fetch_and_store_contents

# ─────────────────────────── Constants ───────────────────────────────────────
GRAFANA_BASE_URL = os.getenv(
    "GRAFANA_BASE_URL",
    "http://localhost:3000/d/your_dashboard_uid/social-pulse",
)

POVERTY_DIMENSIONS_TG = {
    "INCOME": """
    desempleo salario mínimo bajos ingresos deudas familiares pobreza laboral
    pérdida de empleo ingreso insuficiente precariedad laboral empleo informal
    falta de oportunidades laborales reducción de salario inestabilidad económica
    recesión subempleo despidos masivos contratos temporales informalidad
    costos de vida elevados falta de empleo formal insuficiencia salarial
    """,

    "ACCESS TO HEALTH SERVICES": """
    falta de acceso a servicios de salud hospitales saturados escasez de medicamentos 
    deficiencias en la atención médica carencia de personal médico emergencia sanitaria
    costos elevados de tratamientos cierre de centros de salud lista de espera prolongada
    equipos médicos inoperantes desabasto de vacunas falta de atención especializada
    """,

    "EDUCATIONAL_LAG": """
    deserción escolar suspensión de clases carencia de docentes  
    dificultades de acceso a la educación educación interrumpida rezago académico 
    falta de recursos escolares acceso desigual a la educación deficiencias en formación 
    básica carencia de materiales educativos 
    """,

    "ACCESS TO SOCIAL SECURITY": """
    empleo informal ausencia de prestaciones sociales falta de contrato laboral 
    exclusión del sistema de pensiones carencia de protección social trabajo precario 
    derechos laborales no garantizados falta de cotización al sistema desprotección estructural
    dificultades para acceder al seguro social informalidad laboral empleo sin afiliación
    """,

    "HOUSING": """
    vivienda precaria hacinamiento falta de servicios básicos 
    infraestructura deteriorada zonas marginadas viviendas inseguras
    """,
    
    "ACCESS TO FOOD": """
    inseguridad alimentaria acceso limitado a alimentos inflación precios
    raciones insuficientes pobreza alimentaria aumento de precios comeder comunitario
    canasta básica crisis alimentaria comida pobre ayuda alimentaria 
    insuficiencia nutricional alimentación deficiente encarecimiento de alimentos
    inflación en alimentos carencia alimentaria productos básicos banco de alimentos
    alimentos inaccesibles gasto alimentario elevado programas alimentarios
    """,

    "SOCIAL_COHESION": """
    discriminación étnica marginación social exclusión comunidades vulnerables
    conflictos intercomunitarios tensiones sociales barreras sociales 
    desigualdad aislamiento social
    """}

POVERTY_DIMENSIONS_YT = {
    "INCOME": """
    empleo trabajo salario ingresos dinero economía sueldo ahorro impuestos
    chamba lana nómina billete jale job salary income money
    """,
    "ACCESS TO HEALTH SERVICES": """
    salud médico hospital medicina tratamiento atención clínica seguro
    sistema de salud servicios médicos doctor cuidado ir al doctor health insurance
    seguro médico doctor particular ir a consulta healthcare medical treatment 
    """,
    "EDUCATIONAL LAG": """
    educación escuela universidad maestro estudiante aprendizaje escuela pública
    clases formación conocimiento título bachillerato preparatoria escuela secundaria
    """,
    "ACCESS TO SOCIAL SECURITY": """
    seguridad social pensión jubilación contrato derechos laborales
    prestaciones protección IMSS ISSSTE afore finiquito ahorro para retiro
    cotizar retirement benefits social security worker rights informal job
    """,
    "HOUSING": """
    vivienda casa habitación hogar alquiler renta depa housing utilities
    servicios agua luz gas electricidad construcción propiedad rent 
    techo colonia vecindario urbanización asentamiento cuartito mortgage
    """,
    "ACCESS TO FOOD": """
    alimentación comida nutrición alimentos dieta cocinar recetas
    canasta básica food security nutrition meal groceries
    comida saludable dieta balanceada comida rápida comida chatarra
    """,
    "SOCIAL COHESION": """
    comunidad sociedad integración participación convivencia barrio raza community
    respeto diversidad solidaridad inclusión pertenencia 
    vecinos apoyo redes sociales confianza belonging inclusion
    """,
}

POVERTY_DIMENSIONS_GT = {
    'income': ['crisis', 'desempleo', 'pobreza'],
    'access_to_health_services': ['enfermedad', 'centro de salud'],
    'educational_lag': ['becas', 'escuela secundaria'],
    'access_to_social_security': ['pensiones', 'seguro social'],
    'access_to_food': ['banco de alimentos', 'tianguis', 'tiendeo', 'PromoDescuentos'],
    'housing': ['apoyo Infonavit', 'agua potable', 'FOVISSSTE'],
    'social_cohesion': ['violencia', 'conflictos', 'discriminación']
}

NAME_TO_CODE = {
    "Distrito Federal":      "MX-DF",
    "Guerrero":              "MX-GRO",
    "México":                "MX-MEX",
    "Morelos":               "MX-MOR",
    "Sinaloa":               "MX-SIN",
    "Baja California":       "MX-BCN",
    "Sonora":                "MX-SON",
    "Baja California Sur":   "MX-BCS",
    "Zacatecas":             "MX-ZAC",
    "Durango":               "MX-DUR",
    "Chihuahua":             "MX-CHH",
    "Colima":                "MX-COL",
    "Nayarit":               "MX-NAY",
    "Michoacán de Ocampo":   "MX-MIC",
    "Jalisco":               "MX-JAL",
    "Chiapas":               "MX-CHP",
    "Tabasco":               "MX-TAB",
    "Oaxaca":                "MX-OAX",
    "Guanajuato":            "MX-GUA",
    "Aguascalientes":        "MX-AGU",
    "Querétaro":             "MX-QUE",
    "San Luis Potosí":       "MX-SLP",
    "Tlaxcala":              "MX-TLA",
    "Puebla":                "MX-PUE",
    "Hidalgo":               "MX-HID",
    "Veracruz de Ignacio de la Llave": "MX-VER",
    "Nuevo León":            "MX-NLE",
    "Coahuila de Zaragoza":  "MX-COA",
    "Tamaulipas":            "MX-TAM",
    "Yucatán":               "MX-YUC",
    "Campeche":              "MX-CAM",
    "Quintana Roo":          "MX-ROO",
}

st.set_page_config(
    page_title="Thesis MVP • Launcher",
    page_icon="🚀",
    layout="centered",
)
st.title("Thesis MVP - Launcher")

presentation_mode = st.checkbox("Presentation mode")

if "country" not in st.session_state:
    st.session_state.country = "MX"
selected_country = st.selectbox(
    "Country of Analysis",
    ["MX", "BR", "US"],
    index=["MX", "BR", "US"].index(st.session_state.country),
)
st.session_state.country = selected_country

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

st.markdown("## 🗂️ Poverty Dimensions")
selected_dims = st.multiselect(
    "Choose dimensions to include",
    list(POVERTY_DIMENSIONS_YT.keys()),
    help="Select one or more poverty dimensions"
)
if not selected_dims:
    st.warning("Please select at least one poverty dimension.")
    st.stop()

st.session_state.dimensions_yt = [
    {"name": dim, "keywords": POVERTY_DIMENSIONS_YT[dim].split()}
    for dim in selected_dims
]
st.markdown(f"**Selected dimensions:** {selected_dims}")

st.session_state.dimensions_tg = [
    {"name": dim, "keywords": POVERTY_DIMENSIONS_TG[dim].split()}
    for dim in selected_dims
]

st.session_state.dimensions_gt = [
    {"name": dim.lower(), "keywords": POVERTY_DIMENSIONS_GT[dim.replace(" ", "_").lower()]}
    for dim in selected_dims
]

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

st.markdown("## 📁 GeoJSON Upload & Admin Boundaries")
col_geo, col_admin = st.columns([3, 2])
geojson_file = col_geo.file_uploader(
    "Upload GeoJSON File",
    type=["geojson", "json"],
    help="Upload a GeoJSON file with region boundaries"
)
admin_level = col_admin.selectbox(
    "Boundary level",
    ["regions", "states", "counties"],
    index=0,
    help="Select administrative boundaries for factor aggregation"
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
    return analyze_yt(
        start_year=years[0], end_year=years[-1], states=states, dimensions=dimensions
    )

def get_regions(geojson: str):
    data = json.loads(geojson)
    gdf = gpd.GeoDataFrame.from_features(data["features"])
    return gdf["state_name"].tolist()

def format_dimensions(dimensions: list[dict]) -> dict[str, str]:
    return {d["name"].upper(): " ".join(d["keywords"]) for d in dimensions}

st.markdown("## 🚀 Launch")
if st.button("Run Pipeline"):
    progress = st.progress(0)

    if not presentation_mode:
        if geojson_str is None:
            st.error("❌ Please upload GeoJSON before running the pipeline.")
        else:
            with st.spinner("1/7: Parsing GeoJSON..."):
                st.session_state.regions = get_regions(geojson_str)[1:3]
            st.success("✅ GeoJSON parsing done")
            progress.progress(20)

            # with st.spinner("2/7: Parsing and proccesing YouTube data..."):
            #     dims = format_dimensions(st.session_state.dimensions_yt)
            #     st.session_state.yt_data = run_youtube_parser(
            #         states=st.session_state.regions,
            #         dimensions=dims,
            #     )
            # st.success("✅ YouTube parsing done")
            # progress.progress(40)

            # with st.spinner("3/7: Downloading and Processing Telegram data..."):
            #     asyncio.run(download_posts(selected_tg, years[0], years[-1]))
            #     dims = format_dimensions(st.session_state.dimensions_tg)
            #     st.session_state.tg_data = analyze_tg(
            #         start_year=years[0],
            #         end_year=years[-1],
            #         states=st.session_state.regions,
            #         dimensions=dims,
            #         channel_collections=[f"{i.replace('@', '')}_{years[0]}_{years[-1]}" for i in selected_tg]
            #     )
            # st.success("✅ Telegram parsing done")
            # progress.progress(60)

            # with st.spinner("4/7: Running Google Trends analysis..."):
            #     state_codes = [ NAME_TO_CODE[name] for name in st.session_state.regions ]
            #     st.session_state.state_codes = state_codes

            #     keyword_sets = [",".join(d["keywords"]) for d in st.session_state.dimensions_gt]
            #     keyword_sets = list(dict.fromkeys(keyword_sets))

            #     fetch_timeseries_data(
            #         keyword_sets=keyword_sets,
            #         states=state_codes
            #     )

            #     st.session_state.gt_data = run_google_trends(
            #         years=years,
            #         dimensions={d["name"]: d["keywords"] for d in st.session_state.dimensions_gt},
            #         states=state_codes,
            #         save_csv=True,
            #         out_dir="."
            #     )

            with st.spinner("6/7: Fetching Mediacloud outlets..."):
                state_names = st.session_state.regions
                start = date(years[0],1,1)
                end = date(years[-1],1,31)
                fetch_mediacloud_data(
                    keywords=state_names,
                    start_date=start,
                    end_date=end,
                    sleep_between_requests=5.0,
                    max_retries=5
                )

            with st.spinner("7/7: Fetching Google News outlets..."):
                state_names = st.session_state.regions 
                start = date(years[0],1,1)
                end = date(years[-1],1,31)
                fetch_gnews_data(
                    keywords=state_names,
                    start_date=start,
                    end_date=end,
                    max_workers=10,
                    chunk_days=10,
                    sleep_between=1.0
                )

                decode_gnews_links(states=state_names, max_workers=20)

            with st.spinner("7/8: Parsing HTML..."):
                states = st.session_state.regions
                fetch_and_store_contents(
                    states=states,
                    max_workers=10
                )
    
            st.success("✅ Text Processing Pipeline done")
            progress.progress(100)

            link = GRAFANA_BASE_URL.replace("your_dashboard_uid", "feolw0b2ubthca")
            st.markdown(f"➡️ [Open Dashboard]({link})")
    else:
        steps = [
            "Parsing GeoJSON",
            "Parsing YouTube Data",
            "Downloading Telegram Data",
            "Processing Telegram Data",
            "Running ML Pipeline",
            "Finalizing"
        ]
        total = len(steps)
        for idx, desc in enumerate(steps, start=1):
            with st.spinner(f"{idx}/{total}: {desc}..."):
                time.sleep(2)
            st.success(f"✅ {desc} done")
            progress.progress(int(idx/total * 100))

        link = GRAFANA_BASE_URL.replace("your_dashboard_uid", "feolw0b2ubthca")
        st.markdown(f"**Presentation mode complete** — [Open dashboard]({link})")
