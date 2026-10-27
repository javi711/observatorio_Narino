# -----------------------------------------------------------------------------
# INSTALACIÓN AUTOMÁTICA DE DEPENDENCIAS (Google Colab o ejecución local)
# Equivale a: pip install -q gradio plotly pandas requests scikit-learn statsmodels
#             scipy libpysal esda shapely geopandas
# Solo instala los paquetes que falten; si ya están, no hace nada.
# -----------------------------------------------------------------------------
import importlib.util as _ilu
import subprocess as _sp
import sys as _sys

_PAQUETES = {"gradio": "gradio", "plotly": "plotly", "pandas": "pandas", "requests": "requests",
             "sklearn": "scikit-learn", "statsmodels": "statsmodels", "scipy": "scipy",
             "libpysal": "libpysal", "esda": "esda", "shapely": "shapely", "geopandas": "geopandas"}
_FALTAN = [pip for mod, pip in _PAQUETES.items() if _ilu.find_spec(mod) is None]
if _FALTAN:
    print("▸ Instalando dependencias:", ", ".join(_FALTAN))
    _sp.check_call([_sys.executable, "-m", "pip", "install", "-q", *_FALTAN])

# -----------------------------------------------------------------------------
# MODO STREAMLIT (streamlit run app.py · Streamlit Community Cloud)
# Streamlit vuelve a ejecutar el script completo en cada visita e interacción, mientras
# que Gradio necesita UN servidor persistente; ejecutar ambos en el mismo proceso produce
# «Cannot call click outside of a gradio.Blocks context». Bajo Streamlit, el observatorio
# se lanza una sola vez como subproceso (python app.py) y se incrusta en la página; el
# resto de este script no se ejecuta dentro de Streamlit. En Colab o con «python app.py»
# este bloque se omite y la aplicación arranca normalmente.
# -----------------------------------------------------------------------------
import os as _os


def _en_streamlit():
    if _os.environ.get("OBS_SUBPROCESO") == "1" or "streamlit" not in _sys.modules:
        return False
    try:
        from streamlit.runtime import exists as _st_existe
        return bool(_st_existe())
    except Exception:
        return False


if _en_streamlit():
    import atexit as _atexit
    import re as _re
    import threading as _th
    import time as _time
    import streamlit as st
    import streamlit.components.v1 as _componentes

    st.set_page_config(page_title="Observatorio Económico y Social de Nariño", page_icon="🏛️", layout="wide")

    @st.cache_resource(show_spinner=False)
    def _servidor_gradio():
        """Lanza el observatorio Gradio una sola vez por proceso de Streamlit y captura sus URL."""
        entorno = dict(_os.environ, OBS_SUBPROCESO="1", PYTHONUNBUFFERED="1")
        proc = _sp.Popen([_sys.executable, "-u", _os.path.abspath(__file__)], env=entorno, stdout=_sp.PIPE,
                         stderr=_sp.STDOUT, text=True, bufsize=1)
        estado = {"proc": proc, "local": None, "publica": None, "sin_enlace": False, "log": []}

        def _leer():
            for linea in proc.stdout:
                linea = linea.rstrip()
                estado["log"] = (estado["log"] + [linea])[-200:]
                m = _re.search(r"Running on local URL:\s*(\S+)", linea)
                if m:
                    estado["local"] = m.group(1)
                m = _re.search(r"Running on public URL:\s*(\S+)", linea)
                if m:
                    estado["publica"] = m.group(1)
                if "Could not create share link" in linea:
                    estado["sin_enlace"] = True

        _th.Thread(target=_leer, daemon=True).start()
        _atexit.register(lambda: proc.poll() is None and proc.terminate())
        return estado

    st.markdown("<style>.block-container{padding:3rem 0.8rem 0 0.8rem;max-width:100%;}"
                "iframe{border:none;border-radius:12px;}</style>", unsafe_allow_html=True)
    _est = _servidor_gradio()
    with st.spinner("Iniciando el Observatorio: descargando cartografía MGN-DANE y datos oficiales (puede tardar 1–2 minutos la primera vez)…"):
        _t0 = _time.time()
        while (_est["publica"] is None and not _est["sin_enlace"] and _est["proc"].poll() is None
               and _time.time() - _t0 < 420):
            _time.sleep(1)
    if _est["sin_enlace"] and _est["local"] and _est["proc"].poll() is None:
        _time.sleep(2)
    _url = _est["publica"] or (_est["local"] if _est["sin_enlace"] and _est["proc"].poll() is None else None)
    if _url:
        _c1, _c2 = st.columns([4, 1])
        _c1.markdown("##### 🏛️ Observatorio Económico y Social de Nariño")
        _c2.link_button("Abrir en pantalla completa ↗", _url)
        if not _est["publica"]:
            st.info("No se pudo crear el enlace público de Gradio; se muestra la dirección local, visible solo desde este mismo equipo.")
        if hasattr(st, "iframe"):
            st.iframe(_url, height=1900)
        else:
            _componentes.iframe(_url, height=1900, scrolling=True)
    else:
        if _est["proc"].poll() is not None:
            st.error("El servidor del observatorio se detuvo. Últimas líneas del registro:")
        elif _est["sin_enlace"]:
            st.error("Gradio no pudo crear el enlace público que permite mostrar la interfaz dentro de Streamlit. Últimas líneas del registro:")
        else:
            st.warning("El observatorio sigue cargando. Recargue la página en un momento. Registro:")
        st.code("\n".join(_est["log"][-40:]) or "(sin registro)")
        if st.button("Reiniciar el servidor del observatorio"):
            if _est["proc"].poll() is None:
                _est["proc"].terminate()
            st.cache_resource.clear()
            st.rerun()
    st.stop()

# =============================================================================
#  OBSERVATORIO ECONÓMICO Y SOCIAL DE NARIÑO
#  Plataforma Territorial de Inteligencia Económica y Simulación de Políticas
#  Versión 2.0 auditada · celda única para Google Colab · interfaz Gradio
#
#  Principios de esta versión:
#   · Fuentes: DANE, DNP, MinDefensa/Policía,
#     MinEducación, MinSalud y MinJusticia/UNODC-SIMCI (API SODA en vivo o
#     instantánea oficial verificada embebida como respaldo).
#   · Cartografía oficial MGN-DANE de los 64 municipios unida por código DIVIPOLA.
#   · Imputación técnica (PCHIP) solo en huecos interiores de series anuales,
#     documentada celda a celda; nunca se extrapolan ni se anualizan cortes censales.
# =============================================================================

# -----------------------------------------------------------------------------
# 0. CONFIGURACIÓN EDITABLE (créditos, periodo, conexión)
# -----------------------------------------------------------------------------
CREDITOS = {
    "autores": ["Francisco Lagos", "Nataly Viteri", "Fernando Dominguez", "Laura Castañeda"],
    "rol": "Estudiantes de Seminario de Investigación",
    "programa": "Programa de Economía",
    "facultad": "[Facultad de Ciencias Económicas y Administrativas]",
    "universidad": "[Universidad de Nariño]",
    "docente": "[Julio Riascos]",
    "seminario": "[Investigación Regional / curso]",
    "ciudad_anio": "San Juan de Pasto, 2026",
}

CONFIG = {
    "anio_inicio": 2005,
    "anio_fin": 2025,
    "timeout_api": 30,
    "semilla": 52,
    "usar_api": True,
    # Marco Geoestadístico Nacional (MGN 2018, DANE) — límites municipales políticos.
    "geojson_url": "https://raw.githubusercontent.com/caticoa3/colombia_mapa/master/co_2018_MGN_MPIO_POLITICO.geojson",
    "fecha_instantanea": "27/10/2026",
}

# -----------------------------------------------------------------------------
# 1. IMPORTACIONES
# -----------------------------------------------------------------------------
import base64
import functools
import inspect
import json
import tempfile
import unicodedata
import warnings
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import requests
import gradio as gr
import plotly.graph_objects as go
import plotly.io as pio
import plotly.figure_factory as ff
from plotly.colors import sample_colorscale
from plotly.subplots import make_subplots
from scipy import stats as sps
from scipy.interpolate import PchipInterpolator
from scipy.cluster import hierarchy as sch
from shapely.geometry import shape
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from sklearn.metrics import (silhouette_score, calinski_harabasz_score, davies_bouldin_score,
                             mean_squared_error, mean_absolute_error, r2_score)
from sklearn.linear_model import LinearRegression, RidgeCV, LassoCV, ElasticNetCV
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import make_pipeline
from sklearn.compose import TransformedTargetRegressor
from sklearn.model_selection import GroupShuffleSplit, GroupKFold, KFold, cross_val_score, cross_val_predict
from sklearn.inspection import permutation_importance, partial_dependence
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.api import VAR
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset, acorr_ljungbox
from statsmodels.stats.stattools import jarque_bera, durbin_watson

try:
    import libpysal
    from esda.moran import Moran, Moran_Local
    from esda.geary import Geary
    HAY_PYSAL = True
except Exception:
    HAY_PYSAL = False

A0, A1 = CONFIG["anio_inicio"], CONFIG["anio_fin"]
ANIOS = np.arange(A0, A1 + 1)

# -----------------------------------------------------------------------------
# 2. SISTEMA DE DISEÑO: PALETA, CSS INSTITUCIONAL Y PLANTILLA PLOTLY
# -----------------------------------------------------------------------------
C = {
    "navy": "#0f172a", "azul": "#1e3a8a", "azul2": "#2563eb", "azul3": "#60a5fa",
    "fondo": "#f8fafc", "card": "#ffffff", "borde": "#e2e8f0",
    "texto": "#0f172a", "texto2": "#334155", "texto3": "#64748b", "grid": "#eef2f7",
    "verde": "#10b981", "rojo": "#ef4444", "ambar": "#f59e0b", "gris": "#94a3b8",
}

SUBREGIONES = ["Centro", "Exprovincia de Obando", "Sabana", "Abades", "Occidente", "Cordillera",
               "Juanambú", "Río Mayo", "Guambuyaco", "Pie de Monte Costero", "Sanquianga",
               "Pacífico Sur", "Telembí"]
COLOR_SUB = dict(zip(SUBREGIONES, ["#1e3a8a", "#2563eb", "#0891b2", "#0d9488", "#65a30d", "#a16207",
                                   "#c2410c", "#be123c", "#7c3aed", "#475569", "#0e7490", "#0369a1",
                                   "#9333ea"]))
ESCALA_AZUL = [[0, "#eff6ff"], [0.25, "#bfdbfe"], [0.5, "#60a5fa"], [0.75, "#2563eb"], [1, "#0f172a"]]
ESCALA_VERDE = [[0, "#f0fdf4"], [0.25, "#bbf7d0"], [0.5, "#4ade80"], [0.75, "#10b981"], [1, "#065f46"]]
ESCALA_ROJA = [[0, "#fff7ed"], [0.25, "#fed7aa"], [0.5, "#fb923c"], [0.75, "#dc2626"], [1, "#7f1d1d"]]
ESCALA_DIV = [[0, "#b91c1c"], [0.5, "#f8fafc"], [1, "#1e3a8a"]]
ESCALA_SEMAFORO = [[0, "#ef4444"], [0.5, "#fde68a"], [1, "#10b981"]]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
:root{--obs-navy:#0f172a;--obs-azul:#1e3a8a;--obs-fondo:#f8fafc;--obs-borde:#e2e8f0;--obs-verde:#10b981;--obs-rojo:#ef4444;--obs-ambar:#f59e0b;}
.gradio-container{background:#f8fafc !important;font-family:'Inter',system-ui,-apple-system,sans-serif !important;max-width:1440px !important;margin:0 auto !important;}
.gradio-container *{font-family:'Inter',system-ui,-apple-system,sans-serif;}
.gradio-container .mono, .gradio-container .mono *{font-family:'JetBrains Mono',ui-monospace,monospace !important;}
footer{display:none !important;}
.obs-topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;background:#0f172a;color:#e2e8f0;border-radius:14px;padding:12px 20px;margin-bottom:12px;}
.obs-topbar .marca{display:flex;align-items:center;gap:12px;}
.obs-topbar .marca b{color:#fff;font-size:15px;letter-spacing:-.01em;}
.obs-topbar .marca span{color:#94a3b8;font-size:12.5px;}
.obs-pill{display:inline-flex;align-items:center;gap:8px;border-radius:999px;padding:6px 14px;font-size:12.5px;font-weight:600;}
.obs-pill.on{background:rgba(16,185,129,.14);color:#6ee7b7;border:1px solid rgba(16,185,129,.35);}
.obs-pill.off{background:rgba(245,158,11,.14);color:#fcd34d;border:1px solid rgba(245,158,11,.35);}
.obs-pill i{width:8px;height:8px;border-radius:50%;display:inline-block;}
.obs-pill.on i{background:#10b981;box-shadow:0 0 0 3px rgba(16,185,129,.25);}
.obs-pill.off i{background:#f59e0b;box-shadow:0 0 0 3px rgba(245,158,11,.25);}
.obs-hero{position:relative;overflow:hidden;border-radius:22px;padding:34px 38px;color:#fff;background:linear-gradient(125deg,#0f172a 0%,#172554 45%,#1e3a8a 75%,#1d4ed8 100%);box-shadow:0 10px 40px rgba(15,23,42,.18);}
.obs-hero:after{content:"";position:absolute;right:-120px;top:-120px;width:420px;height:420px;border-radius:50%;background:radial-gradient(circle,rgba(96,165,250,.28),rgba(96,165,250,0) 70%);}
.obs-hero .fila{display:flex;gap:28px;align-items:center;position:relative;z-index:1;flex-wrap:wrap;}
.obs-hero .eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#93c5fd;font-weight:700;margin-bottom:8px;}
.obs-hero h1{color:#fff !important;font-size:34px !important;line-height:1.12 !important;font-weight:800 !important;letter-spacing:-.025em;margin:0 0 6px 0 !important;}
.obs-hero h2{color:#bfdbfe !important;font-size:17px !important;font-weight:500 !important;margin:0 0 12px 0 !important;}
.obs-hero .lema{color:#e0e7ff;font-size:14.5px;max-width:820px;line-height:1.6;}
.obs-ribbon{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px;position:relative;z-index:1;}
.obs-chip{background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.22);color:#e0e7ff;padding:5px 12px;border-radius:999px;font-size:12px;font-weight:600;}
.obs-chip.meta{background:rgba(16,185,129,.16);border-color:rgba(16,185,129,.4);color:#a7f3d0;}
.obs-chip.warn{background:rgba(245,158,11,.16);border-color:rgba(245,158,11,.4);color:#fde68a;}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(178px,1fr));gap:16px;margin:20px 0 6px 0;}
.kpi-card{background:#fff;border:1px solid #e2e8f0;border-radius:18px;padding:18px 18px 14px;box-shadow:0 1px 2px rgba(15,23,42,.04),0 6px 18px rgba(15,23,42,.05);display:flex;flex-direction:column;gap:6px;}
.kpi-top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;}
.kpi-label{font-size:11.5px;text-transform:uppercase;letter-spacing:.07em;color:#64748b;font-weight:700;line-height:1.35;}
.kpi-ico{width:34px;height:34px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:#eff6ff;font-size:17px;flex-shrink:0;}
.kpi-value{font-size:28px;font-weight:800;color:#0f172a;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.1;}
.kpi-sub{font-size:12px;color:#64748b;}
.kpi-foot{display:flex;justify-content:space-between;align-items:center;margin-top:4px;gap:6px;flex-wrap:wrap;}
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 9px;border-radius:999px;font-size:12px;font-weight:700;white-space:nowrap;}
.badge.ok{background:#d1fae5;color:#047857;}
.badge.warn{background:#fef3c7;color:#b45309;}
.badge.alert{background:#fee2e2;color:#b91c1c;}
.badge.neutral{background:#e2e8f0;color:#334155;}
.src{font-size:10.5px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;}
.src.oficial{color:#047857;}
.src.respaldo{color:#b45309;}
.obs-section-title{font-size:21px;font-weight:800;color:#0f172a;letter-spacing:-.015em;margin:26px 0 2px;}
.obs-section-sub{color:#64748b;font-size:14px;margin:0 0 12px;}
.obs-intro{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:18px 22px;margin:4px 0 8px;display:flex;gap:18px;align-items:flex-start;}
.obs-intro .ico{font-size:28px;line-height:1;}
.obs-intro h3{margin:0 0 4px !important;font-size:18px !important;font-weight:800 !important;color:#0f172a !important;}
.obs-intro p{margin:0 !important;color:#475569 !important;font-size:14px !important;line-height:1.6 !important;}
.obs-intro .met{margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;}
.obs-intro .met span{font-size:11.5px;font-weight:600;color:#1e3a8a;background:#eff6ff;border:1px solid #dbeafe;padding:2px 9px;border-radius:999px;}
.callout{border-radius:16px;padding:16px 20px;border:1px solid #bfdbfe;border-left:6px solid #1e3a8a;background:#f8fbff;}
.callout.ok{border-color:#a7f3d0;border-left-color:#10b981;background:#f0fdf9;}
.callout.warn{border-color:#fde68a;border-left-color:#f59e0b;background:#fffbeb;}
.callout.alert{border-color:#fecaca;border-left-color:#ef4444;background:#fef2f2;}
.callout h4{margin:0 0 6px !important;font-size:15px !important;font-weight:800 !important;color:#0f172a !important;display:flex;gap:8px;align-items:center;}
.callout p,.callout li{font-size:14px !important;line-height:1.65 !important;color:#334155 !important;margin:4px 0 !important;}
.callout ul{margin:6px 0 0 18px !important;padding:0 !important;}
.guide-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;}
.guide-card{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:18px;position:relative;}
.guide-card .num{width:30px;height:30px;border-radius:9px;background:#1e3a8a;color:#fff;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:14px;margin-bottom:10px;}
.guide-card h5{margin:0 0 6px !important;font-size:14.5px !important;font-weight:800 !important;color:#0f172a !important;}
.guide-card p{margin:0 !important;font-size:13px !important;color:#475569 !important;line-height:1.55 !important;}
.guide-card .tab{display:inline-block;margin-top:10px;font-size:11px;font-weight:700;color:#1e3a8a;background:#eff6ff;padding:2px 8px;border-radius:6px;}
.ficha{background:#fff;border:1px solid #e2e8f0;border-radius:18px;padding:22px 26px;display:grid;grid-template-columns:1.3fr 1fr;gap:26px;}
.ficha h4{margin:0 0 10px !important;font-size:15px !important;font-weight:800 !important;color:#0f172a !important;text-transform:uppercase;letter-spacing:.06em;}
.ficha dl{display:grid;grid-template-columns:150px 1fr;gap:6px 14px;margin:0;font-size:13.5px;}
.ficha dt{color:#64748b;font-weight:600;}
.ficha dd{margin:0;color:#0f172a;font-weight:500;}
.ficha .sello{border:1px dashed #cbd5e1;border-radius:14px;padding:16px;background:#f8fafc;font-size:13px;color:#334155;line-height:1.6;}
@media (max-width:900px){.ficha{grid-template-columns:1fr;}.obs-hero{padding:24px;}.obs-hero h1{font-size:26px !important;}}
.panel-control{background:#fff !important;border:1px solid #e2e8f0 !important;border-radius:18px !important;padding:14px 16px !important;box-shadow:0 1px 2px rgba(15,23,42,.04);}
.panel-titulo{font-size:12px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:#1e3a8a;margin:0 0 4px 2px;}
.tbl{width:100%;border-collapse:collapse;font-size:13px;background:#fff;}
.tbl th{background:#f1f5f9;color:#0f172a;text-align:left;padding:8px 10px;font-weight:700;border-bottom:1px solid #e2e8f0;white-space:nowrap;}
.tbl td{padding:7px 10px;border-bottom:1px solid #f1f5f9;color:#1e293b;font-variant-numeric:tabular-nums;}
.tbl tr:hover td{background:#f8fafc;}
.tbl td.num{text-align:right;}
.tbl-wrap{border:1px solid #e2e8f0;border-radius:12px;overflow:auto;max-height:520px;}
.tec h5{margin:14px 0 6px !important;font-size:13.5px !important;font-weight:800 !important;color:#1e3a8a !important;text-transform:uppercase;letter-spacing:.05em;}
.tec p{font-size:13px !important;color:#475569 !important;}
.mono{white-space:pre;overflow-x:auto;background:#0f172a;color:#e2e8f0;padding:14px 16px;border-radius:12px;font-size:12px;line-height:1.5;}
.sim-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;}
.sim-card{background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:14px 16px;}
.sim-card .l{font-size:11.5px;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:.06em;}
.sim-card .v{font-size:24px;font-weight:800;margin-top:4px;font-variant-numeric:tabular-nums;}
.sim-card .v.ok{color:#047857;} .sim-card .v.alert{color:#b91c1c;} .sim-card .v.neutral{color:#0f172a;}
.sim-card .d{font-size:12px;color:#64748b;margin-top:2px;}
.obs-btn-primary{background:linear-gradient(135deg,#1e3a8a,#2563eb) !important;color:#fff !important;border:none !important;font-weight:700 !important;}
.obs-btn-sec{background:#fff !important;color:#1e3a8a !important;border:1px solid #cbd5e1 !important;font-weight:700 !important;}
button[role=tab]{font-weight:600 !important;font-size:14px !important;}
.nota-fuente{font-size:12px;color:#64748b;margin-top:6px;}
.legend-dot{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:middle;}
"""

pio.templates["observatorio"] = go.layout.Template(layout=dict(
    font=dict(family="Inter, system-ui, sans-serif", size=12.5, color=C["texto2"]),
    title=dict(font=dict(size=15.5, color=C["navy"], family="Inter, system-ui, sans-serif"), x=0.01, xanchor="left", y=0.97),
    colorway=["#1e3a8a", "#10b981", "#f59e0b", "#ef4444", "#7c3aed", "#0891b2", "#c2410c", "#475569", "#2563eb", "#be123c"],
    separators=",.",
    hoverlabel=dict(bgcolor="white", bordercolor=C["borde"], font=dict(family="Inter, system-ui", size=12, color=C["navy"])),
    margin=dict(l=64, r=28, t=70, b=60), height=470, paper_bgcolor="white", plot_bgcolor="white",
    xaxis=dict(gridcolor=C["grid"], zerolinecolor=C["borde"], linecolor="#cbd5e1", ticks="outside",
               tickcolor="#cbd5e1", automargin=True, exponentformat="none",
               title=dict(font=dict(size=12, color=C["texto3"]))),
    yaxis=dict(gridcolor=C["grid"], zerolinecolor=C["borde"], linecolor="#cbd5e1", automargin=True,
               exponentformat="none", separatethousands=True, title=dict(font=dict(size=12, color=C["texto3"]))),
    legend=dict(orientation="h", yanchor="top", y=-0.16, xanchor="left", x=0, font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
))
pio.templates.default = "plotly_white+observatorio"


def fig_vacia(msg="Sin datos para la selección actual", alto=420):
    f = go.Figure()
    f.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                     font=dict(size=14, color=C["texto3"]))
    f.update_xaxes(visible=False)
    f.update_yaxes(visible=False)
    f.update_layout(height=alto, margin=dict(l=20, r=20, t=30, b=20))
    return f


# -----------------------------------------------------------------------------
# 3. FORMATOS NUMÉRICOS (convención colombiana: 1.234.567,89)
# -----------------------------------------------------------------------------
def fnum(x, dec=0):
    try:
        if x is None or not np.isfinite(float(x)):
            return "—"
    except Exception:
        return "—"
    s = f"{float(x):,.{dec}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_val(x, key, corto=False):
    m = META.get(key, {})
    d = m.get("dec", 1)
    t = m.get("tipo", "num")
    if t == "pct":
        return f"{fnum(x, d)} %"
    if t == "cop":
        return f"$ {fnum(x, d)}"
    if t == "ha":
        return f"{fnum(x, 0)} ha"
    if corto:
        return fnum(x, d)
    return f"{fnum(x, d)}"


def unidad(key):
    return META.get(key, {}).get("unidad", "")


def eje(fig, key, axis="y", row=None, col=None, titulo=True):
    m = META.get(key, {})
    t = m.get("tipo", "num")
    d = min(m.get("dec", 1), 2)
    kw = dict(tickformat=f",.{d}~f", separatethousands=True, exponentformat="none")
    if t == "pct":
        kw["ticksuffix"] = " %"
    elif t == "cop":
        kw["tickprefix"] = "$ "
    if titulo:
        kw["title_text"] = m.get("unidad", "")
    if row is not None:
        kw.update(row=row, col=col)
    (fig.update_yaxes if axis == "y" else fig.update_xaxes)(**kw)
    return fig


def variacion_txt(prev, cur, key):
    if prev is None or cur is None or not np.isfinite(prev) or not np.isfinite(cur):
        return "—"
    if META.get(key, {}).get("tipo") == "pct" or META.get(key, {}).get("unidad", "").startswith("%"):
        dd = cur - prev
        return f"{'+' if dd >= 0 else ''}{fnum(dd, 1)} p.p."
    if prev == 0:
        return "—"
    dd = (cur / prev - 1) * 100
    return f"{'+' if dd >= 0 else ''}{fnum(dd, 1)} %"




CSS += """
.badge.live{background:#d1fae5;color:#047857;}
.badge.snap{background:#dbeafe;color:#1e40af;}
.badge.imp{background:#fef3c7;color:#b45309;}
.src.live{color:#047857;} .src.snap{color:#1e40af;}
.kpi-grid{grid-template-columns:repeat(auto-fit,minmax(178px,1fr)) !important;}
.sel-box{margin-top:12px;background:#eff6ff;border:1px solid #bfdbfe;border-left:4px solid #2563eb;border-radius:10px;padding:10px 14px;}
.sel-box h5{margin:0 0 6px !important;font-size:13.5px !important;font-weight:800 !important;color:#1e3a8a !important;}
.sel-box ul{margin:0 !important;padding-left:18px !important;}
.sel-box li{color:#0f172a !important;font-size:13.5px;margin:3px 0;}
.estado-filtros{margin-top:8px;border-radius:10px;padding:7px 10px;font-size:12px;font-weight:700;line-height:1.35;text-align:center;}
.estado-filtros span{font-weight:500;font-size:11.5px;}
.estado-filtros.ok{background:#ecfdf5;color:#047857;border:1px solid #a7f3d0;}
.estado-filtros.pend{background:#fffbeb;color:#b45309;border:1px solid #fde68a;}
.perfil{background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;padding:18px 20px;margin:14px 0;box-shadow:0 2px 10px rgba(15,23,42,.05);}
.perfil .eyebrow{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:#2563eb;font-weight:800;}
.perfil h3{margin:4px 0 4px !important;font-size:22px !important;font-weight:800 !important;color:#0f172a !important;}
.perfil-cab p{margin:0 0 10px !important;color:#475569 !important;font-size:13.5px;}
.perfil .u{font-size:11px;color:#64748b;}
.perfil .tbl-wrap{max-height:none !important;}
.perfil-vacio{background:#eff6ff;border:1px dashed #93c5fd;border-radius:14px;padding:14px 18px;margin:14px 0;color:#1e3a8a;font-size:14px;line-height:1.55;}
.sem{font-size:12px;font-weight:700;white-space:nowrap;}
.sem.ok{color:#047857;} .sem.mal{color:#b91c1c;} .sem.neutro{color:#94a3b8;}
.nota-alcance{background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid #f59e0b;border-radius:10px;padding:9px 14px;margin:8px 0 4px;color:#334155;font-size:13px;}
/* Barra de navegación de pestañas: siempre visible, con nombres legibles en modo claro y oscuro */
.tab-wrapper{background:#ffffff !important;border:1px solid #cbd5e1 !important;border-radius:14px !important;padding:8px 10px !important;margin:6px 0 14px !important;box-shadow:0 2px 8px rgba(15,23,42,.08) !important;height:auto !important;}
.tab-container{height:auto !important;min-height:44px !important;gap:6px !important;flex-wrap:wrap !important;align-items:center !important;}
.tab-container::after{display:none !important;}
button[role=tab]{font-weight:700 !important;font-size:14px !important;color:#1e3a8a !important;background:#f1f5f9 !important;border:1px solid #cbd5e1 !important;border-radius:10px !important;padding:8px 14px !important;height:auto !important;opacity:1 !important;white-space:nowrap !important;transition:background .15s,border-color .15s,box-shadow .15s !important;}
button[role=tab]:hover{background:#dbeafe !important;border-color:#2563eb !important;color:#0f172a !important;}
button[role=tab][aria-selected=true],button[role=tab].selected{background:linear-gradient(135deg,#1e3a8a,#2563eb) !important;color:#ffffff !important;border-color:#1e3a8a !important;box-shadow:0 4px 12px rgba(30,58,138,.30) !important;}
button[role=tab][aria-selected=true]::after,button[role=tab].selected::after{display:none !important;}
.tab-container.visually-hidden button{font-weight:700 !important;font-size:14px !important;padding:8px 14px !important;border:1px solid transparent !important;margin-right:6px !important;}
.overflow-menu>button{background:linear-gradient(135deg,#1e3a8a,#2563eb) !important;color:#ffffff !important;border-radius:10px !important;padding:8px 12px !important;font-weight:700 !important;font-size:13px !important;display:flex !important;align-items:center !important;gap:4px !important;}
.overflow-menu>button::after{content:"Más pestañas";}
.overflow-menu>button svg{fill:#ffffff !important;color:#ffffff !important;}
.overflow-dropdown{background:#ffffff !important;border:1px solid #cbd5e1 !important;border-radius:10px !important;box-shadow:0 8px 24px rgba(15,23,42,.18) !important;}
.overflow-dropdown button{color:#1e3a8a !important;font-weight:700 !important;background:#ffffff !important;}
.overflow-dropdown button:hover{background:#eff6ff !important;}
.cita{font-size:12px;color:#475569;line-height:1.55;}
.cita a{color:#1e3a8a;}
"""

# -----------------------------------------------------------------------------
# 4. CATÁLOGO TERRITORIAL: 64 MUNICIPIOS EN 13 SUBREGIONES (código DIVIPOLA)
# -----------------------------------------------------------------------------
MUNICIPIOS = [
    ("52001", "Pasto", "Centro"), ("52240", "Chachagüí", "Centro"), ("52480", "Nariño", "Centro"),
    ("52381", "La Florida", "Centro"), ("52788", "Tangua", "Centro"), ("52885", "Yacuanquer", "Centro"),
    ("52356", "Ipiales", "Exprovincia de Obando"), ("52022", "Aldana", "Exprovincia de Obando"),
    ("52210", "Contadero", "Exprovincia de Obando"), ("52215", "Córdoba", "Exprovincia de Obando"),
    ("52224", "Cuaspud", "Exprovincia de Obando"), ("52227", "Cumbal", "Exprovincia de Obando"),
    ("52287", "Funes", "Exprovincia de Obando"), ("52317", "Guachucal", "Exprovincia de Obando"),
    ("52323", "Gualmatán", "Exprovincia de Obando"), ("52352", "Iles", "Exprovincia de Obando"),
    ("52560", "Potosí", "Exprovincia de Obando"), ("52573", "Puerres", "Exprovincia de Obando"),
    ("52585", "Pupiales", "Exprovincia de Obando"),
    ("52838", "Túquerres", "Sabana"), ("52320", "Guaitarilla", "Sabana"), ("52354", "Imués", "Sabana"),
    ("52506", "Ospina", "Sabana"), ("52720", "Sapuyes", "Sabana"),
    ("52678", "Samaniego", "Abades"), ("52699", "Santacruz", "Abades"), ("52565", "Providencia", "Abades"),
    ("52683", "Sandoná", "Occidente"), ("52036", "Ancuya", "Occidente"), ("52207", "Consacá", "Occidente"),
    ("52411", "Linares", "Occidente"),
    ("52540", "Policarpa", "Cordillera"), ("52233", "Cumbitara", "Cordillera"), ("52256", "El Rosario", "Cordillera"),
    ("52405", "Leiva", "Cordillera"), ("52786", "Taminango", "Cordillera"),
    ("52399", "La Unión", "Juanambú"), ("52051", "Arboleda", "Juanambú"), ("52110", "Buesaco", "Juanambú"),
    ("52687", "San Lorenzo", "Juanambú"), ("52694", "San Pedro de Cartago", "Juanambú"),
    ("52019", "Albán", "Río Mayo"), ("52083", "Belén", "Río Mayo"), ("52203", "Colón", "Río Mayo"),
    ("52258", "El Tablón de Gómez", "Río Mayo"), ("52378", "La Cruz", "Río Mayo"),
    ("52685", "San Bernardo", "Río Mayo"), ("52693", "San Pablo", "Río Mayo"),
    ("52260", "El Tambo", "Guambuyaco"), ("52254", "El Peñol", "Guambuyaco"),
    ("52385", "La Llanada", "Guambuyaco"), ("52418", "Los Andes", "Guambuyaco"),
    ("52435", "Mallama", "Pie de Monte Costero"), ("52612", "Ricaurte", "Pie de Monte Costero"),
    ("52250", "El Charco", "Sanquianga"), ("52390", "La Tola", "Sanquianga"), ("52473", "Mosquera", "Sanquianga"),
    ("52490", "Olaya Herrera", "Sanquianga"), ("52696", "Santa Bárbara", "Sanquianga"),
    ("52835", "Tumaco", "Pacífico Sur"), ("52520", "Francisco Pizarro", "Pacífico Sur"),
    ("52079", "Barbacoas", "Telembí"), ("52427", "Magüí", "Telembí"), ("52621", "Roberto Payán", "Telembí"),
]
assert len(MUNICIPIOS) == 64 and len({m[2] for m in MUNICIPIOS}) == 13 and len({m[0] for m in MUNICIPIOS}) == 64


def zona_de(sub, nombre):
    if nombre == "Pasto":
        return "Capital"
    if sub in ("Sanquianga", "Pacífico Sur", "Telembí"):
        return "Litoral Pacífico"
    if sub == "Pie de Monte Costero":
        return "Piedemonte costero"
    if sub == "Exprovincia de Obando":
        return "Frontera sur"
    if sub == "Cordillera":
        return "Cordillera"
    return "Zona andina"


CAT = pd.DataFrame(MUNICIPIOS, columns=["codigo", "municipio", "subregion"])
CAT["zona"] = [zona_de(s, n) for s, n in zip(CAT.subregion, CAT.municipio)]
CAT = CAT.sort_values("codigo").reset_index(drop=True)
CODIGOS = CAT.codigo.tolist()
NOMBRES = sorted(CAT.municipio.tolist(), key=lambda s: unicodedata.normalize("NFD", s))
MUN_A_SUB = dict(zip(CAT.municipio, CAT.subregion))
COD_A_MUN = dict(zip(CAT.codigo, CAT.municipio))
MUN_A_COD = dict(zip(CAT.municipio, CAT.codigo))

# -----------------------------------------------------------------------------
# 5. NORMALIZACIÓN TEXTUAL CANÓNICA (uniones determinísticas de nombres y códigos)
# -----------------------------------------------------------------------------
def normalizar_texto(texto):
    """Mayúsculas, sin diacríticos, sin paréntesis ni signos; espacios simples."""
    if texto is None or (isinstance(texto, float) and np.isnan(texto)):
        return ""
    t = str(texto).split("(")[0]
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    t = "".join(c if c.isalnum() else " " for c in t.upper())
    return " ".join(t.split())


ALIAS_MUN = {
    "SAN JUAN DE PASTO": "Pasto", "SAN ANDRES DE TUMACO": "Tumaco", "MAGUI PAYAN": "Magüí", "MAGUI": "Magüí",
    "CARLOSAMA": "Cuaspud", "CUASPUD CARLOSAMA": "Cuaspud", "SOTOMAYOR": "Los Andes", "LOS ANDES SOTOMAYOR": "Los Andes",
    "BERRUECOS": "Arboleda", "GENOVA": "Colón", "COLON GENOVA": "Colón", "SAN JOSE DE ALBAN": "Albán",
    "ISCUANDE": "Santa Bárbara", "SANTA BARBARA ISCUANDE": "Santa Bárbara", "BOCAS DE SATINGA": "Olaya Herrera",
    "SALAHONDA": "Francisco Pizarro", "EL CONTADERO": "Contadero", "SANTA CRUZ": "Santacruz", "GUACHAVES": "Santacruz",
}
CANON_MUN = {normalizar_texto(n): n for n in CAT.municipio}
CANON_MUN.update(ALIAS_MUN)


def codigo_municipio(nombre=None, codigo=None):
    """Devuelve el código DIVIPOLA de 5 dígitos a partir de un código (5 u 8 dígitos) o de un nombre."""
    if codigo is not None:
        c = "".join(ch for ch in str(codigo) if ch.isdigit())
        if len(c) >= 5 and c[:5] in COD_A_MUN:
            return c[:5]
        if len(c) == 4 and ("0" + c) in COD_A_MUN:
            return "0" + c
    n = CANON_MUN.get(normalizar_texto(nombre))
    return MUN_A_COD.get(n) if n else None


# -----------------------------------------------------------------------------
# 7. METADATOS DE INDICADORES (nivel, unidad, sentido normativo y fuente oficial)
#    sentido: +1 = más es mejor · -1 = más es peor · 0 = neutro
#    corte: "anual" (panel) o "censal" (un único corte transversal oficial)
# -----------------------------------------------------------------------------
META = {
    # ---------- Municipales: desarrollo social (corte censal 2018) ----------
    "ipm": dict(nombre="Pobreza multidimensional (IPM)", unidad="% de personas", tipo="pct", dec=1, sentido=-1, dim="Desarrollo social y demografía", corte="censal", fuente="DANE · IPM municipal CNPV 2018"),
    "ipm_rural": dict(nombre="IPM rural (centros poblados y rural disperso)", unidad="% de personas", tipo="pct", dec=1, sentido=-1, dim="Distribución del ingreso y equidad", corte="censal", fuente="DANE · IPM municipal CNPV 2018"),
    "brecha_ipm": dict(nombre="Brecha urbano-rural del IPM", unidad="puntos porcentuales", tipo="num", dec=1, sentido=-1, dim="Distribución del ingreso y equidad", corte="censal", fuente="DANE · IPM municipal CNPV 2018"),
    "priv_bajo_logro": dict(nombre="Bajo logro educativo", unidad="% de personas", tipo="pct", dec=1, sentido=-1, dim="Desarrollo social y demografía", corte="censal", fuente="DANE · Privaciones IPM CNPV 2018"),
    "priv_sin_agua": dict(nombre="Sin acceso a fuente de agua mejorada", unidad="% de personas", tipo="pct", dec=1, sentido=-1, dim="Desarrollo social y demografía", corte="censal", fuente="DANE · Privaciones IPM CNPV 2018"),
    "priv_excretas": dict(nombre="Inadecuada eliminación de excretas", unidad="% de personas", tipo="pct", dec=1, sentido=-1, dim="Desarrollo social y demografía", corte="censal", fuente="DANE · Privaciones IPM CNPV 2018"),
    "priv_sin_aseg": dict(nombre="Sin aseguramiento en salud", unidad="% de personas", tipo="pct", dec=1, sentido=-1, dim="Desarrollo social y demografía", corte="censal", fuente="DANE · Privaciones IPM CNPV 2018"),
    "priv_trab_informal": dict(nombre="Trabajo informal (privación IPM)", unidad="% de personas", tipo="pct", dec=1, sentido=-1, dim="Mercado de trabajo", corte="censal", fuente="DANE · Privaciones IPM CNPV 2018"),
    "priv_analfabetismo": dict(nombre="Analfabetismo", unidad="% de personas", tipo="pct", dec=1, sentido=-1, dim="Desarrollo social y demografía", corte="censal", fuente="DANE · Privaciones IPM CNPV 2018"),
    # ---------- Municipales: economía ----------
    "va_pc": dict(nombre="Valor agregado per cápita (real)", unidad="millones COP de 2015 por habitante", tipo="cop", dec=2, sentido=1, dim="Cuentas económicas y valor agregado", corte="anual", fuente="DANE · Valor agregado municipal 2011-2024p, deflactado con el VAB de Nariño"),
    "sh_primario": dict(nombre="Peso de actividades primarias en el VA", unidad="% del VA municipal (2024p)", tipo="pct", dec=1, sentido=0, dim="Cuentas económicas y valor agregado", corte="censal", fuente="DANE · VA municipal por grandes actividades 2024p"),
    # ---------- Municipales: seguridad e ilícitos ----------
    "tasa_homicidios": dict(nombre="Tasa de homicidios", unidad="por 100.000 hab.", tipo="num", dec=1, sentido=-1, dim="Seguridad ciudadana y orden público", corte="anual", fuente="MinDefensa · datos.gov.co m8fd-ahd9"),
    "tasa_secuestros": dict(nombre="Tasa de secuestros", unidad="por 100.000 hab.", tipo="num", dec=2, sentido=-1, dim="Seguridad ciudadana y orden público", corte="anual", fuente="MinDefensa · datos.gov.co d7zw-hpf4"),
    "tasa_vif": dict(nombre="Violencia intrafamiliar (denuncias)", unidad="por 100.000 hab.", tipo="num", dec=1, sentido=-1, dim="Desarrollo social y demografía", corte="anual", fuente="Policía Nacional · datos.gov.co vuyt-mqpw"),
    "coca_ha": dict(nombre="Cultivos de coca", unidad="hectáreas detectadas", tipo="ha", dec=0, sentido=-1, dim="Economías ilícitas y vulnerabilidad", corte="anual", fuente="MinJusticia/UNODC-SIMCI · datos.gov.co acs4-3wgp"),
    "coca_pct": dict(nombre="Coca sobre el área municipal", unidad="% del territorio", tipo="pct", dec=2, sentido=-1, dim="Economías ilícitas y vulnerabilidad", corte="anual", fuente="SIMCI y área oficial MGN-DANE"),
    # ---------- Municipales: educación y salud ----------
    "cobertura_neta": dict(nombre="Cobertura neta en educación", unidad="% de la población de 5 a 16 años", tipo="pct", dec=1, sentido=1, dim="Desarrollo social y demografía", corte="anual", fuente="MinEducación · datos.gov.co nudc-7mev"),
    "desercion": dict(nombre="Deserción escolar intraanual", unidad="% de matriculados", tipo="pct", dec=2, sentido=-1, dim="Desarrollo social y demografía", corte="anual", fuente="MinEducación · datos.gov.co nudc-7mev"),
    "partos_inst": dict(nombre="Partos institucionales", unidad="% de nacidos vivos", tipo="pct", dec=1, sentido=1, dim="Desarrollo social y demografía", corte="anual", fuente="MinSalud · datos.gov.co 4e4i-ua65"),
    # ---------- Municipales: finanzas públicas ----------
    "dep_transf": dict(nombre="Dependencia de transferencias", unidad="% de los ingresos totales", tipo="pct", dec=1, sentido=-1, dim="Gestión y finanzas públicas", corte="anual", fuente="DNP · Índice de Desempeño Fiscal"),
    "rec_propios": dict(nombre="Generación de recursos propios", unidad="% de ingresos corrientes (tributarios)", tipo="pct", dec=1, sentido=1, dim="Gestión y finanzas públicas", corte="anual", fuente="DNP · Índice de Desempeño Fiscal"),
    "inversion_pct": dict(nombre="Magnitud de la inversión", unidad="% del gasto total", tipo="pct", dec=1, sentido=1, dim="Gestión y finanzas públicas", corte="anual", fuente="DNP · Índice de Desempeño Fiscal"),
    "idf": dict(nombre="Índice de Desempeño Fiscal", unidad="puntaje (0 a 100)", tipo="num", dec=1, sentido=1, dim="Gestión y finanzas públicas", corte="anual", fuente="DNP · IDF (metodología 2000-2022)"),
    "mdm": dict(nombre="Medición del Desempeño Municipal", unidad="puntaje (0 a 100)", tipo="num", dec=1, sentido=1, dim="Gestión y finanzas públicas", corte="anual", fuente="DNP · datos.gov.co nkjx-rsq7"),
    "poblacion": dict(nombre="Población", unidad="habitantes", tipo="num", dec=0, sentido=0, dim="Desarrollo social y demografía", corte="anual", fuente="DANE · Proyecciones municipales CNPV 2018", log=True),
    # ---------- Departamentales ----------
    "pib": dict(nombre="PIB de Nariño (real)", unidad="miles de millones COP de 2015", tipo="cop", dec=0, sentido=1, dim="Cuentas económicas y valor agregado", nivel="dep", fuente="DANE · PIB departamental base 2015 (2025pr)", log=True),
    "crecimiento_pib": dict(nombre="Crecimiento real del PIB", unidad="% anual", tipo="pct", dec=1, sentido=1, dim="Cuentas económicas y valor agregado", nivel="dep", fuente="DANE · PIB departamental"),
    "pib_pc": dict(nombre="PIB per cápita real", unidad="millones COP de 2015", tipo="cop", dec=2, sentido=1, dim="Cuentas económicas y valor agregado", nivel="dep", fuente="DANE · PIB y proyecciones de población", log=True),
    "desempleo": dict(nombre="Tasa de desempleo (Pasto A.M.)", unidad="% de la fuerza de trabajo", tipo="pct", dec=1, sentido=-1, dim="Mercado de trabajo", nivel="dep", fuente="DANE · GEIH, 23 ciudades"),
    "tgp": dict(nombre="Tasa global de participación (Pasto A.M.)", unidad="% de la PET", tipo="pct", dec=1, sentido=1, dim="Mercado de trabajo", nivel="dep", fuente="DANE · GEIH"),
    "to": dict(nombre="Tasa de ocupación (Pasto A.M.)", unidad="% de la PET", tipo="pct", dec=1, sentido=1, dim="Mercado de trabajo", nivel="dep", fuente="DANE · GEIH"),
    "informalidad": dict(nombre="Informalidad laboral (Pasto A.M.)", unidad="% de ocupados", tipo="pct", dec=1, sentido=-1, dim="Mercado de trabajo", nivel="dep", fuente="DANE · GEIH-EISS"),
    "inflacion": dict(nombre="Inflación anual (IPC nacional)", unidad="% dic-dic", tipo="pct", dec=2, sentido=-1, dim="Variables monetarias y costo de vida", nivel="dep", fuente="DANE · IPC base 2018 (serie de empalme)"),
    "pobreza_monetaria": dict(nombre="Pobreza monetaria", unidad="% de personas", tipo="pct", dec=1, sentido=-1, dim="Distribución del ingreso y equidad", nivel="dep", fuente="DANE · Pobreza monetaria departamental"),
    "pobreza_extrema": dict(nombre="Pobreza monetaria extrema", unidad="% de personas", tipo="pct", dec=1, sentido=-1, dim="Distribución del ingreso y equidad", nivel="dep", fuente="DANE · Pobreza monetaria departamental"),
    "gini": dict(nombre="Coeficiente de Gini", unidad="índice (0 a 1)", tipo="num", dec=3, sentido=-1, dim="Distribución del ingreso y equidad", nivel="dep", fuente="DANE · Pobreza monetaria departamental"),
    "ipm_dep": dict(nombre="IPM departamental", unidad="% de personas", tipo="pct", dec=1, sentido=-1, dim="Desarrollo social y demografía", nivel="dep", fuente="DANE · IPM departamental (ECV)"),
    "tasa_homicidios_dep": dict(nombre="Tasa de homicidios de Nariño", unidad="por 100.000 hab.", tipo="num", dec=1, sentido=-1, dim="Seguridad ciudadana y orden público", nivel="dep", fuente="MinDefensa · m8fd-ahd9 y DANE"),
    "secuestros_dep": dict(nombre="Secuestros en Nariño", unidad="casos", tipo="num", dec=0, sentido=-1, dim="Seguridad ciudadana y orden público", nivel="dep", fuente="MinDefensa · d7zw-hpf4"),
    "coca_dep": dict(nombre="Cultivos de coca en Nariño", unidad="hectáreas", tipo="ha", dec=0, sentido=-1, dim="Economías ilícitas y vulnerabilidad", nivel="dep", fuente="UNODC-SIMCI · acs4-3wgp", log=True),
    "cobertura_dep": dict(nombre="Cobertura neta (promedio ponderado)", unidad="%", tipo="pct", dec=1, sentido=1, dim="Desarrollo social y demografía", nivel="dep", fuente="MinEducación · nudc-7mev"),
    "idf_mediana": dict(nombre="IDF mediano municipal", unidad="puntaje (0 a 100)", tipo="num", dec=1, sentido=1, dim="Gestión y finanzas públicas", nivel="dep", fuente="DNP · IDF"),
    "dep_transf_dep": dict(nombre="Dependencia de transferencias (mediana)", unidad="% de ingresos", tipo="pct", dec=1, sentido=-1, dim="Gestión y finanzas públicas", nivel="dep", fuente="DNP · IDF"),
    "recursos_dnp": dict(nombre="Inversión pagada en proyectos (MapaInversiones)", unidad="miles de millones COP", tipo="cop", dec=0, sentido=1, dim="Gestión y finanzas públicas", nivel="dep", fuente="DNP · datos.gov.co wc86-9j4a", log=True),
    "ctei": dict(nombre="Inversión en proyectos de CTeI", unidad="miles de millones COP", tipo="cop", dec=1, sentido=1, dim="Ciencia, tecnología e innovación", nivel="dep", fuente="DNP · MapaInversiones, sector CTeI"),
}
for _k, _m in META.items():
    _m.setdefault("nivel", "mun")
    _m.setdefault("corte", "anual")

IND_MUN = [k for k, v in META.items() if v["nivel"] == "mun" and k != "poblacion"]
IND_MUN_ANUAL = [k for k in IND_MUN if META[k]["corte"] == "anual"]
IND_MUN_CENSAL = [k for k in IND_MUN if META[k]["corte"] == "censal"]
IND_DEP = [k for k, v in META.items() if v["nivel"] == "dep"]


def nombre(k):
    return META.get(k, {}).get("nombre", k)


def minus(t):
    """Minúscula inicial salvo siglas (PIB, IPM, IDF…)."""
    if not t or (len(t) > 1 and t[1].isupper()):
        return t
    return t[:1].lower() + t[1:]


def opciones(keys):
    return [(nombre(k) + (" · 2018" if META.get(k, {}).get("corte") == "censal" and k != "sh_primario" else
                          " · 2024p" if k == "sh_primario" else ""), k) for k in keys]



# -----------------------------------------------------------------------------
# 6. MATRIZ EMPÍRICA CONSOLIDADA: INSTANTÁNEA OFICIAL VERIFICADA (27-oct-2026)
#    Cifras transcritas de los archivos y APIs oficiales citados en FUENTES_META.
#    Formato: codigo DIVIPOLA: valor_año0, valor_año1, ...  (vacío = sin registro)
# -----------------------------------------------------------------------------
SNAP = {}
SNAP["pob"] = (2005, """
52001:363816,367356,370582,373304,375760,378072,380245,382333,384087,385710,387388,389184,390727,392934,395380,397905,399607,400907,401996,403166,404102,404775,405306,405682,405938,406050
52019:11016,10921,10842,10746,10658,10545,10474,10355,10222,10104,9936,9807,9807,9641,9621,9654,9648,9642,9631,9628,9627,9620,9600,9583,9575,9548
52022:6678,6760,6845,6912,6943,6985,7046,7051,7130,7238,7244,7236,7355,7392,7473,7522,7589,7665,7705,7748,7802,7840,7882,7939,7971,7986
52036:9763,9782,9686,9587,9488,9403,9351,9333,9237,9052,8938,8849,8753,8781,8811,8829,8835,8839,8824,8823,8813,8803,8781,8756,8738,8706
52051:8013,8096,8156,8217,8256,8258,8274,8284,8313,8365,8402,8398,8399,8437,8562,8668,8767,8867,8962,9049,9147,9249,9326,9388,9481,9567
52079:43241,44401,45508,46546,47555,48536,49506,50449,51345,52221,53098,53984,54839,55628,57305,58972,60361,61548,62594,63548,64392,65144,65797,66415,66943,67447
52083:5080,5238,5321,5423,5543,5643,5722,5854,5918,5972,6000,6184,6276,6335,6317,6332,6332,6313,6307,6288,6278,6253,6247,6213,6200,6168
52110:22882,23047,23156,23235,23441,23453,23566,23636,23718,23757,23792,23852,23904,23906,24132,24359,24560,24709,24892,25040,25192,25325,25466,25590,25703,25824
52203:8807,8823,8799,8771,8780,8729,8693,8674,8633,8715,8679,8590,8530,8528,8524,8535,8539,8558,8537,8501,8510,8504,8470,8474,8450,8425
52207:12817,12918,13020,13129,13229,13260,13294,13367,13441,13492,13586,13676,13675,13790,14050,14321,14551,14782,14988,15175,15347,15520,15678,15817,15937,16051
52210:6998,7012,7060,7082,7100,7159,7095,7089,7121,7154,7226,7207,7238,7273,7318,7394,7439,7460,7485,7530,7554,7575,7582,7593,7609,7626
52215:14106,14278,14411,14560,14652,14749,14848,14951,15065,15189,15256,15349,15435,15509,15743,15954,16157,16357,16553,16735,16936,17107,17287,17460,17620,17799
52224:7986,8106,8236,8286,8435,8557,8657,8732,8835,8955,8966,9009,9142,9210,9302,9450,9569,9685,9777,9889,9995,10080,10193,10267,10370,10450
52227:28496,29241,29986,30724,31379,32017,32668,33332,33934,34494,35095,35762,36260,36870,37488,38121,38718,39296,39843,40406,40971,41498,42041,42565,43088,43595
52233:6312,6292,6301,6292,6190,6191,6152,6119,6069,6043,6017,5951,5935,5946,5946,5957,5954,5949,5936,5948,5949,5944,5929,5914,5899,5877
52240:13691,13857,14029,14153,14294,14439,14563,14683,14823,14921,15060,15160,15206,15359,15557,15758,15937,16081,16229,16366,16474,16581,16668,16766,16841,16899
52250:22940,22996,23033,23044,23010,22976,22941,22899,22860,22785,22741,22628,22569,22501,22445,22385,22350,22339,22348,22396,22434,22503,22582,22655,22735,22818
52254:9110,9022,8873,8738,8651,8514,8379,8217,8102,7985,7837,7645,7548,7439,7524,7602,7656,7720,7774,7831,7885,7937,7976,8020,8073,8118
52256:10830,10984,11119,11243,11367,11467,11616,11724,11791,11866,11980,12071,12209,12278,12412,12507,12617,12695,12801,12872,12964,13025,13096,13180,13228,13295
52258:12984,13158,13299,13390,13505,13621,13738,13767,13837,13926,14033,14154,14256,14340,14402,14492,14558,14590,14631,14671,14702,14728,14756,14760,14771,14774
52260:17940,17669,17394,17165,16887,16609,16316,16038,15735,15443,15210,14926,14488,14286,14359,14425,14464,14498,14518,14548,14560,14572,14587,14585,14596,14573
52287:7421,7416,7417,7445,7383,7321,7337,7368,7376,7323,7191,7166,7179,7240,7263,7319,7363,7378,7417,7441,7452,7484,7485,7523,7524,7527
52317:17020,17256,17505,17693,17878,18065,18263,18471,18663,18851,18984,19082,19297,19458,19660,19862,20042,20212,20338,20468,20577,20676,20764,20840,20904,20953
52320:12958,12894,12795,12704,12630,12530,12418,12262,12142,12066,11988,11716,11573,11567,11589,11605,11608,11607,11582,11604,11593,11572,11546,11551,11501,11489
52323:6608,6717,6757,6800,6856,6913,6901,6952,6968,6953,6952,6955,6992,7053,7180,7281,7375,7448,7542,7609,7677,7726,7791,7845,7896,7931
52352:7690,7721,7724,7699,7681,7730,7702,7735,7715,7715,7694,7632,7631,7655,7672,7698,7691,7698,7697,7678,7673,7664,7635,7624,7599,7587
52354:7951,7941,7963,7926,7815,7866,7820,7775,7730,7715,7667,7612,7631,7645,7698,7744,7756,7788,7823,7836,7843,7864,7874,7875,7867,7872
52356:104686,105928,107099,108147,109111,110004,110890,111737,112485,113186,113934,114694,115348,116128,117206,118300,119188,119965,120690,121440,122149,122747,123339,123904,124408,124902
52378:19509,19502,19475,19473,19363,19353,19273,19220,19114,19020,18954,18977,18781,18746,18922,19082,19221,19351,19442,19560,19684,19772,19852,19933,20040,20098
52381:10589,10585,10558,10534,10506,10473,10437,10398,10419,10312,10255,10174,10087,10102,10110,10137,10130,10117,10113,10098,10097,10081,10070,10059,10019,9994
52385:6929,6931,6871,6852,6798,6768,6798,6702,6704,6633,6599,6552,6517,6494,6509,6531,6550,6554,6569,6565,6575,6565,6566,6554,6551,6509
52390:7851,7824,7820,7794,7765,7750,7737,7662,7580,7566,7537,7508,7408,7390,7490,7576,7642,7700,7762,7838,7895,7963,8017,8065,8127,8180
52399:28915,29237,29545,29814,30068,30297,30521,30749,30949,31133,31341,31456,31785,31849,32307,32781,33179,33572,33941,34338,34707,35059,35400,35767,36070,36404
52405:9900,9931,9949,9938,9938,9931,9923,9886,9886,9853,9877,9796,9776,9771,9781,9778,9792,9789,9769,9779,9763,9740,9729,9730,9705,9680
52411:11676,11604,11505,11403,11296,11209,11115,11016,10868,10724,10549,10464,10305,10217,10253,10262,10251,10258,10236,10242,10237,10207,10206,10172,10158,10125
52418:10829,10764,10729,10623,10510,10426,10313,10181,10083,10052,9879,9738,9612,9557,9566,9574,9573,9560,9555,9553,9544,9542,9519,9505,9499,9478
52427:17422,18059,18691,19303,19883,20494,21049,21598,22130,22655,23200,23698,24238,24706,25340,25996,26548,27047,27528,27970,28377,28738,29078,29372,29643,29904
52435:8041,8159,8258,8327,8402,8498,8580,8569,8617,8728,8831,8878,8938,8993,8971,8992,8991,8960,8939,8934,8927,8906,8879,8827,8793,8769
52473:9743,9976,10150,10363,10571,10748,10903,11068,11209,11373,11539,11712,11832,11982,12007,12057,12072,12076,12080,12081,12083,12092,12057,12030,12023,11984
52480:4725,4726,4711,4707,4648,4569,4526,4528,4510,4451,4352,4321,4339,4358,4397,4429,4455,4486,4501,4530,4540,4550,4557,4586,4598,4606
52490:27396,27353,27229,27145,27020,26850,26703,26533,26330,26095,25953,25780,25556,25373,25611,25848,26119,26343,26579,26822,27052,27248,27487,27688,27866,28063
52506:7058,7068,7086,7105,7101,7105,7116,7106,7099,7084,7051,7120,7099,7106,7119,7126,7111,7114,7115,7111,7099,7099,7095,7077,7059,7038
52520:11881,12099,12308,12511,12714,12915,13082,13234,13425,13603,13759,13891,14060,14193,14463,14733,14984,15212,15441,15667,15906,16116,16296,16522,16693,16867
52540:9487,9531,9598,9647,9669,9713,9748,9779,9799,9798,9847,9900,9875,9896,9905,9904,9917,9891,9897,9905,9869,9870,9861,9834,9810,9792
52560:11676,11610,11548,11461,11367,11280,11196,11090,10959,10821,10689,10595,10450,10412,10428,10434,10434,10430,10407,10402,10396,10406,10364,10351,10314,10318
52565:8038,7827,7701,7500,7326,7111,6950,6701,6490,6317,6060,5907,5762,5561,5572,5574,5580,5567,5569,5555,5571,5572,5537,5532,5513,5523
52573:9193,9168,9161,9133,9016,8990,8939,8950,8920,8867,8773,8631,8554,8573,8585,8591,8584,8573,8537,8534,8488,8466,8431,8396,8375,8327
52585:17358,17397,17493,17525,17595,17543,17541,17541,17562,17484,17557,17693,17463,17500,17496,17507,17459,17426,17363,17327,17246,17207,17128,17047,16949,16875
52612:15011,15463,15856,16202,16580,16961,17320,17691,18023,18375,18679,19003,19316,19626,20132,20622,21108,21581,22060,22530,23033,23519,24010,24500,24982,25494
52621:11686,11805,11950,12003,12096,12166,12239,12314,12353,12450,12536,12615,12624,12658,12587,12475,12451,12418,12406,12427,12462,12505,12551,12593,12655,12722
52678:37521,36988,36439,35813,35212,34560,33968,33309,32639,31984,31352,30725,30141,29433,29434,29434,29451,29439,29411,29401,29386,29365,29299,29263,29198,29136
52683:24947,24664,24376,24102,23753,23427,23144,22790,22452,22136,21773,21500,21146,20775,20793,20839,20831,20828,20820,20826,20804,20774,20748,20724,20685,20641
52685:9635,9625,9616,9554,9540,9537,9495,9480,9411,9352,9337,9276,9229,9200,9207,9204,9216,9209,9192,9192,9190,9165,9159,9152,9133,9111
52687:17360,17506,17633,17762,17833,17928,18023,18106,18138,18138,18270,18396,18460,18479,18547,18602,18654,18681,18710,18725,18745,18748,18744,18718,18710,18678
52693:17253,17149,17031,16932,16765,16631,16448,16284,16182,16049,15913,15701,15461,15395,15406,15420,15435,15421,15401,15407,15378,15364,15329,15303,15281,15235
52694:6282,6361,6389,6461,6506,6555,6544,6550,6619,6647,6696,6707,6815,6850,6860,6858,6866,6853,6834,6842,6820,6790,6789,6756,6727,6701
52696:11551,11762,11933,12100,12288,12407,12566,12689,12789,12929,13083,13218,13318,13422,13549,13673,13788,13898,14020,14142,14254,14357,14487,14574,14650,14751
52699:9930,10042,10126,10202,10304,10333,10383,10454,10504,10512,10586,10689,10742,10790,10741,10697,10680,10680,10664,10666,10646,10629,10616,10603,10579,10547
52720:7411,7393,7402,7398,7386,7380,7325,7311,7296,7304,7353,7310,7317,7358,7358,7370,7383,7378,7389,7368,7374,7344,7353,7326,7306,7294
52786:18297,18334,18298,18278,18295,18274,18296,18197,18119,18127,18041,17955,17857,17862,17968,18086,18176,18246,18310,18398,18438,18485,18523,18559,18590,18616
52788:12929,13034,13073,13165,13182,13267,13272,13339,13326,13343,13387,13430,13400,13514,13708,13911,14089,14227,14387,14521,14662,14744,14864,14963,15027,15114
52835:202285,207097,211748,216073,220262,224316,228287,232172,235844,239414,243000,246582,249983,253643,257419,261178,264327,267076,269643,272306,274765,277065,279235,281280,283221,285032
52838:42058,42383,42698,42955,43199,43425,43630,43804,43975,44125,44324,44460,44649,44745,45170,45627,46018,46353,46667,47014,47314,47615,47874,48120,48373,48602
52885:10242,10323,10384,10454,10513,10611,10694,10757,10736,10816,10900,10930,10887,10940,11058,11185,11289,11372,11481,11573,11661,11751,11825,11894,11975,12042
""")
SNAP["ipm2018"] = (2018, """
52001:16.3,12.4,30.1
52019:44.2,22.9,52.6
52022:29.1,18.3,32.2
52036:22.2,11.9,26
52051:54.3,32.4,58.2
52079:76.1,61.3,83.3
52083:34.1,22.6,47.4
52110:39.2,22.8,46
52203:42.4,14.5,46.3
52207:34.9,22.2,37.9
52210:44,21.1,49.6
52215:41.8,21.6,47
52224:51.4,34.7,58.5
52227:28.6,15.3,31.9
52233:39.4,32.4,42.2
52240:32.2,24.2,36.4
52250:75.9,57,85.2
52254:43,18.6,48.7
52256:52.1,42.9,54.9
52258:50.4,24.6,53.6
52260:31.9,20.8,38.8
52287:41.1,30.8,49.6
52317:30.4,16.6,33
52320:33.6,22.5,40.3
52323:30.9,20.5,39.7
52352:43.6,31.5,48.3
52354:40.2,25.5,42.5
52356:23.4,14.7,41
52378:27.8,18.2,35.7
52381:59,39.5,63.9
52385:33.6,28.5,39.3
52390:73.9,67.4,80.2
52399:48.6,24.8,64.4
52405:55.3,36.1,64.5
52411:32.9,16.6,37.3
52418:44.9,29,58.7
52427:85.3,74.8,91.2
52435:39,19.9,42.1
52473:70.2,69.4,71
52480:40.8,34,53.4
52490:75.9,71,80.3
52506:28.9,18.7,33.1
52520:69.5,69.1,70.2
52540:38.7,32,41.7
52560:27.5,13.8,31
52565:55.3,28.8,65.3
52573:32.7,23.5,38.9
52585:32.2,19.6,38.6
52612:71.9,38.8,76.3
52621:81,66.9,85
52678:47.7,19.1,61.8
52683:28.9,21.8,35.7
52685:59.4,35,68.9
52687:55.3,32.7,58.4
52693:41.1,14.8,51.6
52694:54.6,13.4,60.2
52696:75.1,73.2,76.2
52699:65.1,40.5,69.6
52720:43,40.2,43.7
52786:36.1,22.6,40.3
52788:46,29.5,52
52835:53.7,45.8,63.3
52838:32.5,18.1,42.3
52885:44.2,28.7,51.3
""")
SNAP["priv2018"] = (2018, """
52001:7.1,41,1.1,5.8,26.4,8.8,2.8,2.6,0.5,2.3,13.1,1.5,15,0.8,81.8
52019:14.6,69.1,0.5,7.1,53.9,7.1,6.6,2.7,0.7,46.9,8.6,23.5,7.6,0.9,92.2
52022:10.3,70.6,1,6.4,36.9,10.9,26.7,3.1,0.3,7.4,15.7,15.6,7.3,1.2,89.9
52036:13,69.2,0.5,8.6,28.2,7.2,11.5,1.6,0,11.8,5.3,1.8,6.6,1,89.6
52051:25.2,75.8,1.5,2,58.2,12.3,15.4,4,0.6,35.6,13.9,30.3,14.8,0.6,94.1
52079:33.5,78.3,6.2,5.5,53,16.2,79.7,12.2,16.9,2.8,38.3,87.7,21.5,4.1,95.4
52083:13.9,65.9,0.4,10.8,48.5,15.9,7.5,1.9,0.2,13.5,13.6,7.6,8.6,0.3,93.6
52110:18.3,77.8,1,5.2,34.7,9.2,15.5,5.2,0.3,26.9,15.8,26.4,8.6,3.4,91
52203:23.1,78.4,1.1,4.7,37.9,3.3,11.8,5.6,1.1,38,13.4,21.4,7.4,2.8,93.4
52207:18,73.7,0.8,0.8,40.9,7.2,13,2.3,0.4,39,14.2,5.5,8.8,0.8,91.1
52210:12.1,70.5,1,2.2,47.6,14.9,35.3,3.5,0.1,60.4,14.4,10.1,8.3,1.9,92.3
52215:14,70.3,1.4,4.1,40.9,16.9,36.2,3.8,0.4,55.9,16.6,9.1,7.5,2.3,94.1
52224:12.3,77.4,1.5,0.4,55.8,17.8,58.1,6.4,1.9,43.3,12.6,47,8,1,94.4
52227:15.3,68.4,1.5,0.7,45.8,10.3,12.6,3.9,1.7,13.2,11.7,10,9.2,1.7,93.7
52233:14,76.9,1.2,1.8,46.4,7.8,18.9,10,3.5,10.6,15.7,17.2,8.2,2.3,93.5
52240:18.2,68.8,1.3,4.6,36.8,13,4.1,2.6,1.6,9.6,16.7,6.6,12.3,1.2,89.1
52250:31.5,75.6,7,6,52.9,15.5,89.3,9.2,27.9,4.8,38.4,79.7,26.6,4.7,95.7
52254:24.6,80.4,0.9,5.4,30.2,6,19.7,4.2,1.8,44.7,12.7,36.8,6.8,1.5,92.9
52256:17.1,80.3,0.8,8.3,53.4,8.2,9.6,3.3,0.4,55.3,14.8,23.3,6.5,1.5,94.6
52258:15.5,76,0.6,8.2,48.8,9,34.9,5.5,1,52.6,18.3,46.4,7.2,2.1,94.6
52260:15.9,74,0.6,1.5,37.9,11.4,8.6,3,1,28.9,10.9,14.8,6.8,2.3,91.3
52287:18.1,75.3,0.7,12,41.1,14,18.8,3.1,0.2,51.7,12.2,10.7,6,1,91.4
52317:16.7,72.7,1.3,1.3,48.9,9.2,10.3,3,0.3,13.1,9.2,7.2,8.7,0.8,93.1
52320:13.1,78.3,0.6,6.2,32.3,12,7.2,3.1,0.1,35.9,15.6,3.3,5.3,1.8,91.8
52323:9.4,67.4,0.6,3.9,47.4,12.6,10.5,1.8,0.2,29.9,15.6,2.7,5.7,1.1,92.8
52352:14.3,75.9,1.1,1.5,47.8,19.3,23.6,4.1,0.9,55.4,12.9,10.5,6.5,1.4,93.6
52354:15.3,71.1,1.2,4.8,54.2,8.4,19.4,2.2,0.3,28.1,10.3,23.3,9.6,0.8,91.2
52356:9.6,57,1.4,3.4,28.4,11.7,13.4,3.5,0.4,9.1,15.3,11.7,11.7,1.7,89.8
52378:18.1,70.1,0.5,2.8,39.9,9.2,3.4,3.4,0,23.6,9.9,1.5,6.6,0.9,92.4
52381:21.6,77,0.6,4.3,66.7,12.5,60,2.4,1.7,59.3,11.6,5.9,7.5,0.5,94.1
52385:10,67.1,1.3,1.8,54.7,9.2,9.5,2.6,2.8,19.1,15.1,22.8,7.4,0.6,94.5
52390:31.2,70,5.5,6.6,54.3,10.8,91.9,7.1,14.8,4.7,35.9,98.4,27.4,3,97
52399:17.9,67.5,1.1,3.4,52.6,11.1,49.4,3.9,1.6,36.9,13,39.7,9.1,1.1,93.4
52405:22,79.1,1.1,5.5,46.5,10.6,21.3,5.9,2.2,43.1,21,38.9,9.5,3.2,95.1
52411:17.9,76.7,0.5,6,35.5,8.7,14.1,3.1,0.3,14.6,14.1,9.2,5.5,2.2,91.4
52418:16,76.3,0.9,13.4,48,10.9,9,3.1,2.3,31.8,15.6,14.7,8.1,1.1,93.8
52427:34.5,82.3,10,7.6,69.7,18.4,82.7,19.9,23.7,5.1,53.3,95.9,27,4.4,98.6
52435:14.8,70,1.3,1.7,42.8,7,51.4,3.4,1,5.6,14.7,21.7,9,0.8,90.1
52473:23.5,65.6,7.7,3.8,43.5,4.6,98,6.6,42.7,1.1,29,96.3,35.6,3.9,95.4
52480:11.2,71.2,1.2,1.4,47.9,19,36.3,1.7,1.7,16,18.2,3.6,9.7,0.6,90.1
52490:27.4,74.1,8.1,5.9,52.2,13.7,95,10.5,40.7,3.8,40,90.4,25.8,4.2,96.9
52506:11.8,75.8,0.8,1.5,40.2,12.7,7.9,3.8,0,30.3,12.8,3.5,5.8,0.8,92.1
52520:29.8,73.1,3.5,5.3,45.9,8.3,82.9,6.9,53.5,0.9,34,65.3,19.8,3.3,94
52540:15.5,78.2,0.7,3.4,32.9,8.7,18.8,4.8,2.4,16.8,23.3,16.8,8.4,4.3,94.6
52560:11.4,77.3,1.4,1.4,27.8,15,5,4.1,0.1,18.9,17.6,0.7,7.7,2.8,94.8
52565:8.8,68.2,1.4,0.8,74.1,10,20,3.5,1.3,67.3,10.5,23.7,6,0.3,95.2
52573:10.3,67.4,0.9,3.1,49.3,13.7,17.2,2.3,0.1,28.3,13.9,9.7,7.4,0.9,90.9
52585:8.4,73.8,1.3,3.9,38.8,14,26.6,3.9,0.3,20.8,14,12.4,8.1,1.8,91.8
52612:33.1,75.6,5.4,3.3,53.8,17.5,79.8,12.2,24.7,7.2,33.5,67.5,19.1,4.3,94.1
52621:34.6,82.6,8.4,6.6,63.8,9,56.2,11.9,14,6.8,38.8,86.7,30.2,3.6,97.9
52678:20,73.1,0.9,5.5,47,9.7,29.4,4.5,7.5,41.4,13.9,25.4,5.9,1.5,93.9
52683:18.8,70,1,3.3,33.3,10,4.8,3.4,0.5,19.3,15.8,1.3,8.9,1.1,91.2
52685:17.6,76.7,0.7,7,71.3,9.4,18.9,2.9,0.3,37.9,16.2,42.5,8.1,0.7,95.2
52687:20.7,80.3,1.1,9.8,44.9,9.5,12.7,4.2,0.6,69.4,17.6,36.8,7,1.7,93.5
52693:21.3,73,0.5,5.9,37.2,6.9,18.6,3.3,0.2,22.6,13.4,41,7,1.6,91.5
52694:23.3,79.6,0.6,6.7,38.2,9,67.6,4.7,0.3,37.4,19.7,69.6,5.5,2.3,90.5
52696:26,76.4,7.6,3.3,54.8,10,97,7.1,34.5,0.6,32.7,90.9,23.8,2.3,95.9
52699:18.7,82.2,2.7,6.3,63.4,15.6,40.7,7.6,4.7,37.3,21.4,44.5,10,1.6,95.7
52720:12.5,80.4,0.7,2.3,54.1,17.8,8.3,2.2,0.2,31.5,17.2,8.7,7.1,0.9,94.1
52786:26.1,74.2,0.9,1.9,33.3,8.6,13,2.6,0.8,24.3,14.4,16,9.6,1.7,93.9
52788:16,79.2,1.2,1.4,57.1,15.7,14.7,5.4,0.1,31.3,15.3,8,8.1,0.7,89.5
52835:19.5,61.7,3.9,4.1,43.9,8.6,73.1,6.3,25.4,3,23.1,58.3,19.5,2.5,91.6
52838:11.7,71.5,1,4.2,35.1,13.9,18.8,3.7,0.6,19.2,17.7,9.8,9.1,1.5,93.4
52885:18.1,73.9,1,13.4,45.7,12.4,10.9,2.6,0.2,40.6,18.4,6.7,9,1.3,88.3
""")
SNAP["va_corr"] = (2011, """
52001:3093.37,3406.06,3762.49,3979.91,4438.92,4979.78,5214.58,5588.05,5991.86,5876.94,6718.85,7592.45,8241.49,8996.73
52019:76.48,60.22,78.82,93.98,122.54,108.48,128.69,149.44,133.36,144.58,157.28,181.96,274.81,301.59
52022:31.93,34.24,35.80,39.17,40.20,46.93,47.23,45.32,44.03,42.79,48.36,56.93,75.10,91.88
52036:35.49,35.23,41.26,44.48,47.04,40.00,43.79,51.63,56.72,59.36,64.85,79.68,77.92,93.35
52051:26.13,24.30,35.24,39.15,46.41,53.14,58.92,74.17,69.85,89.53,94.87,125.53,110.81,142.59
52079:157.88,162.64,130.23,244.70,273.95,327.81,285.67,245.73,293.28,259.73,282.68,317.11,352.04,473.22
52083:36.70,38.65,41.58,39.71,37.41,37.72,43.43,35.57,39.14,38.95,44.84,53.11,58.09,66.06
52110:97.73,109.65,117.97,129.66,129.65,145.21,173.59,185.29,206.06,201.82,234.69,248.96,236.09,274.32
52203:60.03,87.76,68.25,57.65,51.46,63.87,73.80,77.39,72.97,78.56,96.03,148.22,127.71,139.65
52207:52.79,57.44,62.45,69.94,77.63,87.67,77.56,69.96,74.12,77.86,92.90,119.99,113.72,122.40
52210:44.92,42.64,40.64,45.10,51.20,59.73,53.60,51.74,61.74,60.11,76.55,102.09,111.63,114.38
52215:63.55,65.88,70.30,77.65,78.98,90.63,97.22,127.13,119.11,101.11,135.21,173.00,199.42,224.68
52224:39.24,34.74,39.75,50.87,57.75,62.14,53.61,54.11,51.91,46.98,64.55,84.16,89.23,99.33
52227:80.36,92.99,101.50,108.41,121.23,137.72,142.49,149.63,155.91,148.02,174.44,213.14,244.99,267.04
52233:31.57,50.55,35.50,33.62,36.00,38.65,41.45,44.88,41.75,42.29,48.89,60.39,63.72,68.79
52240:90.83,102.05,99.07,109.91,118.02,148.26,126.44,142.54,195.50,187.17,219.87,215.05,239.31,287.28
52250:65.49,61.52,71.58,138.34,126.12,154.71,128.15,130.71,134.25,160.21,133.38,173.10,220.37,293.31
52254:31.13,28.15,32.49,36.40,51.04,46.93,61.07,84.25,65.40,56.69,70.05,88.78,85.84,92.91
52256:31.87,36.74,38.17,40.41,42.73,46.18,60.38,68.98,53.69,118.01,88.96,122.41,118.34,208.07
52258:41.56,42.82,51.69,57.34,63.83,73.24,94.58,51.77,91.39,87.92,104.57,139.85,126.59,147.39
52260:63.06,63.51,82.09,80.32,89.75,88.88,95.56,109.62,117.58,114.14,143.99,197.82,193.40,232.56
52287:19.56,23.42,29.30,30.07,33.34,34.26,42.40,50.54,54.10,56.72,67.03,67.35,88.45,106.59
52317:79.64,91.05,100.09,107.59,123.47,144.00,144.64,160.29,157.10,161.43,185.30,223.20,258.43,285.07
52320:55.42,58.23,64.03,68.89,75.82,78.94,86.59,104.57,112.24,109.05,136.78,162.24,173.78,197.72
52323:31.43,34.81,47.34,54.24,58.19,67.85,80.90,94.12,75.91,62.23,86.63,95.59,110.86,111.65
52352:58.02,47.47,54.67,55.61,66.29,72.13,73.95,77.41,82.78,69.41,81.34,88.06,100.66,104.17
52354:37.58,36.64,55.91,43.52,45.27,49.24,55.07,56.05,57.36,62.38,74.02,83.98,97.83,103.80
52356:666.07,708.66,820.25,933.02,963.53,1094.91,1194.57,1266.52,1321.83,1261.94,1496.04,1680.77,1861.14,2107.29
52378:47.58,50.24,57.67,59.71,64.15,69.56,81.26,79.47,85.68,84.07,103.28,123.96,137.60,156.77
52381:64.02,59.48,64.50,68.12,64.98,66.67,82.51,81.13,82.28,86.08,106.35,154.85,160.94,140.02
52385:29.62,34.82,24.67,24.07,23.73,28.04,33.35,30.14,32.62,37.62,35.51,42.19,46.03,55.85
52390:17.63,21.32,23.50,25.04,23.80,29.51,29.78,27.40,26.60,26.67,28.84,33.82,41.79,45.97
52399:129.09,146.10,154.23,161.67,173.17,205.65,233.71,235.83,224.59,228.40,270.11,338.64,353.42,381.60
52405:33.84,40.55,44.58,49.60,49.24,50.65,58.35,60.87,69.34,65.20,63.01,80.00,99.50,120.34
52411:38.54,38.29,44.50,47.87,54.05,58.03,63.02,71.32,72.80,76.97,99.31,127.27,120.81,134.55
52418:44.80,60.37,56.05,56.90,62.28,64.76,63.05,67.74,66.24,55.17,62.42,76.13,86.38,87.59
52427:43.22,60.82,103.05,123.29,132.71,164.24,96.71,66.79,71.85,73.50,67.07,80.90,99.32,114.44
52435:25.12,25.89,28.47,30.57,32.19,38.91,43.63,41.32,45.54,46.55,58.09,71.71,76.33,91.67
52473:22.69,26.79,30.16,30.55,31.84,32.57,34.61,36.74,37.59,36.22,40.93,48.49,59.32,64.93
52480:30.63,25.75,29.37,32.47,32.05,32.61,37.65,35.23,36.10,39.35,44.36,41.15,41.10,41.56
52490:57.19,53.44,59.88,61.47,66.52,81.14,88.12,85.90,93.03,82.22,93.74,108.36,139.79,167.24
52506:34.62,38.97,42.55,64.16,78.70,83.79,57.15,60.14,62.73,58.52,67.46,88.82,84.22,94.98
52520:33.17,34.33,34.93,37.35,41.82,50.58,58.71,53.92,45.42,43.18,49.56,65.09,85.25,79.40
52540:41.75,45.15,53.06,52.88,54.42,57.34,61.64,66.39,62.03,65.42,77.05,96.30,110.90,126.12
52560:55.79,59.66,67.95,74.87,86.01,81.97,82.19,89.99,133.54,251.15,288.26,281.57,397.30,391.24
52565:21.79,19.71,21.55,24.20,26.86,28.07,30.11,26.62,27.42,28.62,33.30,44.07,42.82,46.00
52573:40.36,40.06,43.14,43.13,47.38,50.50,58.14,63.83,59.02,61.38,78.60,95.24,108.78,130.90
52585:86.36,107.47,106.16,100.59,148.13,194.35,196.10,195.12,188.23,152.51,190.68,234.83,238.65,271.30
52612:48.28,48.83,45.24,55.98,57.94,61.41,70.68,80.69,87.12,82.48,119.03,147.55,187.87,205.53
52621:31.78,87.83,127.08,90.06,90.38,97.49,59.48,52.86,51.87,45.66,135.06,204.71,223.33,116.59
52678:129.11,133.28,129.23,140.55,143.92,164.35,173.99,195.54,168.48,177.07,203.09,242.94,320.78,381.04
52683:88.32,91.90,104.74,110.27,116.22,120.34,130.49,129.28,162.71,158.55,173.12,226.32,259.03,255.80
52685:35.22,33.00,45.59,50.13,45.26,61.92,55.08,60.13,55.66,56.61,63.59,75.95,104.15,82.75
52687:76.82,85.93,95.89,98.25,96.43,110.21,144.64,146.86,140.15,147.30,177.88,243.98,238.68,258.17
52693:48.75,53.79,66.89,70.07,78.78,81.85,87.08,93.95,102.75,106.66,118.00,148.29,191.49,178.41
52694:20.54,22.08,25.89,23.96,33.21,40.60,47.91,64.14,67.32,69.63,76.62,120.25,95.62,93.68
52696:69.30,144.21,75.59,40.10,146.84,231.22,88.94,52.04,114.55,126.01,129.45,166.20,168.12,134.09
52699:33.05,30.94,36.21,38.27,42.56,47.47,52.41,53.92,43.81,46.59,58.06,71.29,75.78,82.46
52720:44.80,46.89,54.18,66.21,61.74,85.57,62.84,69.21,65.96,57.46,67.08,84.48,92.14,103.72
52786:74.87,77.30,86.97,89.94,107.11,103.74,108.04,138.35,148.27,146.65,175.59,227.80,213.59,202.84
52788:56.83,65.08,91.14,83.48,89.00,74.19,91.63,78.02,91.65,93.68,106.23,153.91,166.85,174.96
52835:905.84,946.08,999.09,1085.97,1334.78,1643.74,1397.71,1525.24,1923.68,1782.21,2043.70,2419.66,2663.86,3061.93
52838:256.79,295.09,307.88,338.25,345.27,394.91,393.29,386.97,270.27,371.05,409.12,454.96,533.03,675.17
52885:58.12,51.32,52.62,60.14,62.08,84.64,83.16,87.93,90.21,95.37,124.35,156.80,175.97,194.08
""")
SNAP["va_estr2024"] = (2024, """
52001:259.480,816.402,7920.848,8996.730,36.428
52019:222.825,15.330,63.434,301.588,1.221
52022:21.306,4.747,65.823,91.877,0.372
52036:33.722,4.847,54.779,93.348,0.378
52051:88.425,7.318,46.845,142.588,0.577
52079:127.030,19.055,327.139,473.224,1.916
52083:7.940,3.429,54.693,66.062,0.267
52110:96.434,14.206,163.683,274.323,1.111
52203:87.747,7.166,44.737,139.649,0.565
52207:52.293,6.412,63.693,122.399,0.496
52210:67.010,5.875,41.493,114.378,0.463
52215:101.492,11.564,111.619,224.676,0.910
52224:37.104,5.153,57.075,99.332,0.402
52227:75.629,14.064,177.349,267.042,1.081
52233:13.935,3.556,51.302,68.793,0.279
52240:114.642,14.715,157.920,287.277,1.163
52250:158.375,13.704,121.228,293.307,1.188
52254:46.560,4.807,41.540,92.907,0.376
52256:141.244,10.677,56.144,208.066,0.842
52258:58.152,7.655,81.582,147.388,0.597
52260:102.244,11.941,118.373,232.558,0.942
52287:53.869,5.485,47.238,106.592,0.432
52317:51.692,90.575,142.803,285.070,1.154
52320:82.892,10.140,104.691,197.724,0.801
52323:54.974,5.745,50.926,111.645,0.452
52352:48.040,5.363,50.768,104.171,0.422
52354:37.965,5.355,60.483,103.803,0.420
52356:275.989,107.186,1724.115,2107.290,8.532
52378:31.314,8.213,117.239,156.766,0.635
52381:75.024,7.214,57.785,140.022,0.567
52385:12.556,2.912,40.384,55.851,0.226
52390:3.033,2.417,40.517,45.968,0.186
52399:122.694,19.761,239.140,381.595,1.545
52405:50.170,6.206,63.960,120.336,0.487
52411:63.676,6.943,63.937,134.555,0.545
52418:24.582,4.559,58.446,87.587,0.355
52427:9.369,5.756,99.311,114.436,0.463
52435:33.842,4.754,53.075,91.671,0.371
52473:5.466,3.446,56.022,64.934,0.263
52480:9.603,2.165,29.789,41.557,0.168
52490:40.496,8.412,118.329,167.238,0.677
52506:50.689,4.896,39.399,94.983,0.385
52520:14.885,3.994,60.517,79.396,0.321
52540:32.104,6.503,87.509,126.115,0.511
52560:304.383,19.846,67.014,391.243,1.584
52565:12.176,2.402,31.418,45.997,0.186
52573:50.321,6.723,73.860,130.903,0.530
52585:130.155,16.861,124.286,271.302,1.099
52612:63.300,10.647,131.585,205.532,0.832
52621:56.938,4.036,55.619,116.593,0.472
52678:157.874,19.654,203.508,381.037,1.543
52683:90.206,13.219,152.376,255.801,1.036
52685:27.528,4.313,50.913,82.753,0.335
52687:147.829,13.294,97.047,258.170,1.045
52693:63.142,9.231,106.039,178.412,0.722
52694:53.162,4.823,35.699,93.684,0.379
52696:60.240,5.219,68.633,134.092,0.543
52699:14.327,4.317,63.821,82.465,0.334
52720:46.619,16.809,40.294,103.722,0.420
52786:70.870,10.515,121.457,202.842,0.821
52788:87.747,9.588,77.629,174.965,0.708
52835:484.072,208.846,2369.009,3061.927,12.398
52838:264.244,35.510,375.415,675.169,2.734
52885:118.221,9.954,65.905,194.080,0.786
""")
SNAP["hom"] = (2003, """
52001:160,116,102,123,90,118,114,92,123,87,102,56,58,64,53,50,53,58,49,41,41,32,42
52019:2,1,1,1,,,1,1,,,,4,1,,1,,,,,1,2,,
52022:1,,1,1,,2,2,3,1,,1,1,1,,1,3,,,2,,,3,2
52036:4,4,2,11,2,1,4,2,1,6,1,2,,2,,,3,1,1,3,4,2,1
52051:,2,2,1,1,,3,,3,3,2,1,,1,,1,,1,2,1,1,,
52079:9,10,26,34,35,32,34,50,22,24,19,34,20,24,19,34,29,35,36,23,23,18,11
52083:,,4,,1,1,,3,1,2,1,1,5,,,,1,,2,1,,2,1
52110:5,5,1,4,3,12,4,2,4,4,4,,2,2,4,1,1,7,3,3,4,6,2
52203:,5,,2,5,4,5,7,13,4,5,3,4,2,,,1,3,6,4,,1,2
52207:6,1,6,2,2,3,2,2,1,1,2,3,4,,1,,1,,,,2,2,6
52210:3,1,1,4,,,,1,3,2,4,1,,4,,,6,,,,,,
52215:5,7,16,15,2,4,1,1,2,3,3,2,8,2,2,1,3,,,2,2,5,4
52224:1,1,3,1,,1,1,2,1,3,1,,1,1,,1,1,2,4,1,3,3,2
52227:4,6,10,4,6,4,2,1,,2,4,6,1,3,4,3,3,3,5,9,,3,3
52233:1,6,14,16,12,7,6,5,4,2,3,8,5,,5,2,15,9,7,3,5,7,2
52240:4,2,,1,4,4,3,3,1,2,1,2,1,1,1,,2,1,1,2,1,1,1
52250:8,9,7,10,12,10,7,17,11,11,5,10,7,8,16,14,11,7,15,10,9,6,3
52254:1,4,6,7,5,4,,3,1,,3,1,4,1,6,2,7,2,1,1,5,1,4
52256:4,4,11,12,12,7,7,5,3,5,3,5,5,6,9,19,8,4,7,10,8,4,9
52258:2,1,7,3,2,4,3,3,4,1,5,2,1,,1,2,,,1,1,,1,1
52260:3,2,3,3,4,3,4,4,2,3,3,2,4,3,1,,4,1,5,4,3,3,1
52287:,1,1,1,2,3,1,,1,3,,,1,,1,1,,1,,,,,
52317:,3,1,1,5,4,,3,2,2,,3,4,1,2,2,1,1,1,4,1,,1
52320:3,2,3,1,1,3,1,3,3,3,,,5,,2,1,2,1,,1,,1,
52323:1,1,2,3,,4,3,,2,1,1,,,1,1,,,1,,,1,,
52352:2,3,1,3,,,2,,2,,1,,3,2,1,3,,,,2,1,1,
52354:3,1,2,1,1,3,,,,2,,,2,1,1,,,,,,,1,1
52356:37,23,36,42,59,37,25,28,38,42,29,33,25,22,23,35,33,42,47,47,51,38,35
52378:3,5,19,2,2,3,,2,8,2,3,2,5,,,2,2,,1,2,3,3,2
52381:2,3,7,8,3,2,2,3,7,2,3,2,3,,,2,1,2,2,1,,1,1
52385:2,3,3,3,,3,,3,1,,2,,1,,,,1,3,3,1,1,2,3
52390:,2,2,,8,3,1,2,,2,2,2,,2,4,2,3,1,3,5,,4,1
52399:9,11,8,4,12,7,10,7,9,22,22,17,10,12,3,6,6,6,5,10,12,11,13
52405:1,5,11,11,13,6,3,11,7,11,12,6,4,8,5,9,10,21,18,6,10,4,2
52411:2,8,16,9,17,10,4,6,,6,5,9,,11,1,2,3,2,3,3,3,4,5
52418:4,5,5,7,4,1,4,,1,3,3,2,3,,3,1,2,,3,3,1,6,7
52427:3,3,3,2,1,3,3,,4,2,1,2,2,1,13,6,7,4,3,7,4,2,2
52435:3,4,8,11,3,3,6,5,,10,2,1,,4,2,6,9,3,14,10,11,3,4
52473:,4,3,1,3,4,3,,3,,,3,1,2,4,1,2,8,2,,1,,1
52480:,,1,4,,2,1,,,,1,,,2,,1,,,,,,,
52490:3,10,20,18,12,8,10,2,3,12,12,5,10,13,35,31,16,25,26,15,7,7,5
52506:,3,,,,,,1,1,,,,1,,,,,,,,2,,
52520:4,4,5,3,3,7,11,1,6,3,3,4,3,11,5,9,2,2,6,3,3,,
52540:5,13,12,33,25,5,13,12,7,20,17,23,24,14,30,25,14,18,17,14,14,22,13
52560:2,1,1,6,1,2,6,4,1,2,3,6,3,3,1,2,4,5,1,1,1,2,4
52565:,,3,1,1,1,2,1,3,3,2,1,2,4,1,4,3,,4,1,2,1,2
52573:5,1,3,1,,3,1,1,2,1,1,2,1,2,1,2,1,,,,,1,2
52585:3,8,5,1,1,5,2,3,4,12,5,3,4,2,3,8,1,,4,3,12,5,2
52612:16,5,11,15,10,7,9,3,3,7,2,7,9,7,6,12,10,11,15,15,12,17,16
52621:,,,1,4,4,8,4,3,4,10,3,1,2,8,5,5,11,10,6,8,1,
52678:21,22,22,20,22,31,27,20,7,23,29,21,30,18,22,42,31,36,33,29,29,12,14
52683:7,3,1,9,8,2,5,6,2,7,2,3,2,3,5,1,2,4,2,6,6,4,
52685:,2,,,1,,,,1,,1,,2,1,,4,1,,,2,,,
52687:2,3,4,5,11,8,4,2,4,3,1,4,3,,2,4,2,1,2,3,3,7,2
52693:7,5,5,3,3,3,2,4,1,3,2,,4,1,1,4,4,4,5,2,9,5,1
52694:,,1,3,1,,1,1,1,,,,1,1,,,,,,,1,1,1
52696:,2,18,1,2,2,1,,1,1,3,5,,1,4,5,15,5,3,5,2,6,2
52699:1,3,7,6,9,11,3,13,3,7,3,6,4,5,2,5,3,1,6,3,5,,3
52720:,,1,,,2,,,,1,,,1,,3,,,1,,,2,,
52786:7,6,12,17,19,11,8,14,14,10,10,7,4,6,5,9,5,3,7,4,12,19,13
52788:7,1,1,2,,1,1,1,1,1,1,3,,4,1,2,3,2,,,,1,
52835:110,89,205,210,252,231,240,219,209,240,202,141,126,144,203,239,216,202,171,194,90,58,40
52838:10,9,16,10,16,16,4,12,10,13,5,4,4,5,4,4,2,3,3,5,11,6,3
52885:3,3,1,3,1,1,1,1,2,2,2,1,1,,1,1,,,2,,2,2,1
""")
SNAP["sec"] = (2003, """
52001:16,14,17,12,13,1,1,3,7,,2,1,,,,,,1,,2,3,3,3
52019:,,,,,,,,1,,,,,,,1,,,,,,,
52036:,,1,1,,1,,,,,,,,,,,,,,,,,
52079:1,4,6,,,,,1,,,,2,1,3,1,,,2,,2,6,4,5
52110:5,,1,,,,,,1,,,,,,,,,,,,,,
52203:,,,,,1,,,,1,,,,,,,,,,,,,
52207:1,,,,,,,,,,,,,,,,,,,,,,
52210:,,,,,,2,,,3,,,,,,,,,,,,,
52215:,,,,,,,,,1,,1,,,,,1,,,,,,
52224:1,,,,,,,,,,,,,,1,,,,,,,,
52227:1,,1,,,,,,1,,,,,1,,,,,,,,2,
52233:3,,,2,,,,,,,,,,,,,,,,,2,1,2
52240:,2,,,,,1,,2,,,,,,,,,,,,,,
52250:1,,,1,,3,,1,,,,,,,,1,,,,,,,1
52254:,,,,1,,,,,,,,,,,,,,,,,,
52256:,,,,2,,,,,,,,,1,,,,,,,,,
52258:1,,,,,,,,,,,,,,,,,,,,,,
52260:1,,,,,2,,,,,,,,,,,,,,,,,
52287:1,,,,,,,,,,,,,,,,,,,,,,
52317:,,,,4,,2,,1,1,,,,,,,,,,,,1,
52320:,,,,,1,,,,3,,,,,,,,,,,,1,
52352:,,,,,,1,,,,,,,,,,,,,,,,
52354:1,,,1,,,,,,,,,,,,,,,,,,,
52356:1,7,3,4,1,,,2,2,5,1,,2,,2,4,,3,3,4,1,6,3
52378:,,,,,,,,,2,,,,,,,,,,,,,
52381:,,3,,,,,,,,,,,,,,,,,,,,
52385:,,,,,,1,,,,,,,,1,,,,,,,,
52399:,,2,1,,,2,1,,,,,1,,,,2,,,,,,
52405:,,,,1,,,,,,,,1,1,,,,,,,,,
52411:8,,,,1,,,,,,,,,,,,,,,,,,
52418:3,,1,,2,,,,1,,,,,,,,,,,,2,,
52427:,,,,,,,,,,,,,,1,,1,,,,,,
52435:2,1,,,,,,2,3,,,,,,,,,,,,,,
52473:1,,,,,,,,,,,,,,,,,,,,,,1
52480:,,,,,,,,1,,,,,,,,,,,,,,
52490:,,2,,,,2,,,,,,,,,,1,,,1,,,1
52520:,,,1,,,,2,,,,,,,,,,,,,,,
52540:,,,,1,1,1,,1,,,,1,,,,,,,,1,1,1
52560:,,,,1,,,,,,,,,,,1,,,,,,,
52565:,,,,,1,,,,,,,,,,,1,,,,,,
52573:4,6,,,,,,,,,,,,,,,,,,,,,
52585:,2,1,,,,,1,1,,,,1,,1,1,,,,,,1,1
52612:,7,,,,1,,,3,,,,1,,,,,,,,,1,
52621:,,,1,4,,,,,,,,,,1,,,,,,,,
52678:1,,2,4,1,,2,,,,2,,,1,,,,,,,3,,
52683:,,,,,2,,,,,,,,,,,,,,,,,
52685:1,,,,,,,,,,,,,,,,,,,,,,
52687:,,,,,1,,,,,,,,,,,,,,,,,1
52693:,,,,,,,,,,,,,,,1,,,,,,,1
52696:1,,1,,,,,,1,,,,,,,,,1,,,,,
52699:,,,,1,,1,,,1,,,,,,,,,,,,,
52720:,,1,,,,1,,,,,1,,,,,,,,,,,
52786:,,1,,,,,,,,,1,,,,,,,,,,,
52788:5,2,,,,,,,2,,,,,,,,,,,,,1,
52835:11,3,18,4,1,1,5,3,2,,1,5,,,5,3,,2,1,3,9,4,6
52838:,,,,,2,,2,2,3,,,,1,,1,,,,1,3,4,
52885:,,,1,,,,,,,,,,,,,,,,,,,
""")
SNAP["vif"] = (2010, """
52001:48,827,988,671,483,1179,1414,2038,1992,2283,1475,1623,2170,1970,2151,1990
52019:,2,6,12,6,1,8,5,2,5,3,5,5,6,10,5
52022:,1,1,1,1,3,7,4,6,5,3,6,8,9,4,7
52036:1,1,3,2,,4,1,2,3,,5,16,12,8,12,13
52051:,4,1,,,,3,3,15,10,6,3,5,5,9,6
52079:,4,3,5,2,1,14,14,18,17,17,19,38,39,30,50
52083:,5,2,1,2,5,4,17,2,,,2,4,8,8,6
52110:6,8,11,10,7,9,11,23,25,27,21,18,40,36,30,21
52203:6,4,1,1,3,,6,2,2,1,2,2,5,1,1,2
52207:1,2,4,2,4,9,2,8,6,8,5,6,12,18,13,8
52210:1,,2,,,,6,2,1,4,10,8,5,2,4,19
52215:2,2,3,2,6,,4,4,4,4,3,1,5,8,31,9
52224:2,1,,,,,4,1,2,4,18,30,20,10,,5
52227:1,1,6,,,,8,3,18,12,4,21,12,5,13,22
52233:,,,2,,,5,4,3,4,8,9,3,4,7,7
52240:,2,1,7,2,3,13,20,21,16,21,35,41,26,31,38
52250:,1,,1,1,3,3,5,2,6,8,15,15,9,14,7
52254:1,2,,,,,1,3,2,5,4,5,1,,3,7
52256:,2,1,2,1,5,2,1,8,5,2,2,6,4,6,3
52258:,2,1,4,5,3,1,13,4,3,3,11,4,36,22,20
52260:2,,,,1,1,4,12,15,16,6,22,10,19,25,24
52287:2,1,,,,1,,3,,3,3,9,3,2,1,3
52317:,8,7,9,,2,9,4,4,3,1,8,10,6,22,15
52320:5,2,8,,8,5,3,1,8,6,12,7,13,14,9,13
52323:,,2,1,,1,,1,4,3,1,2,2,5,4,4
52352:,1,1,1,,2,1,3,1,3,2,12,3,8,6,9
52354:2,2,2,,3,1,7,4,5,7,8,9,5,6,6,4
52356:107,133,90,45,93,159,138,274,156,260,169,207,255,199,249,323
52378:1,5,16,1,,7,8,12,7,7,12,11,16,15,22,7
52381:1,,1,1,1,2,13,3,4,8,5,15,9,3,15,13
52385:,,,,1,1,,4,4,1,2,4,12,1,8,20
52390:,,,,1,,,1,,2,,,1,2,1,
52399:5,11,18,11,,3,17,28,31,75,47,35,33,59,40,49
52405:,,2,1,1,2,1,9,9,9,8,10,7,3,14,9
52411:1,,2,,,3,4,8,2,1,10,6,1,1,3,2
52418:4,1,,1,,,,3,1,11,5,17,17,7,8,5
52427:,1,,,,,1,5,1,3,,1,3,8,4,2
52435:,,3,3,4,2,4,5,5,1,5,10,5,4,10,15
52473:,,,3,,,2,2,1,,,,,1,1,2
52480:,,3,1,1,3,2,9,5,2,4,1,2,1,10,8
52490:,,,,1,,,1,,1,,6,2,4,,2
52506:,3,,,1,5,2,3,3,2,1,5,7,4,5,3
52520:,,2,2,3,,1,3,4,2,2,5,2,4,1,2
52540:,5,6,5,6,4,6,10,17,12,11,17,9,13,12,5
52560:1,4,2,20,1,4,13,10,11,16,12,20,28,14,18,20
52565:,1,,,,,2,,,,,,5,,4,4
52573:,5,1,2,,,6,4,9,11,8,2,3,7,4,6
52585:,1,2,,,3,7,3,4,14,10,11,6,25,20,20
52612:2,,3,3,6,6,10,4,9,16,19,10,11,22,16,10
52621:,1,,,,,,2,1,,,,1,1,1,3
52678:,9,3,8,8,10,13,6,5,15,15,23,18,16,11,16
52683:4,9,6,11,8,5,8,21,19,8,25,18,35,26,30,34
52685:4,5,,,1,5,13,4,3,1,1,1,2,6,,5
52687:,2,1,2,,,1,5,6,9,3,10,8,13,15,25
52693:2,5,2,2,,4,,2,3,4,6,4,7,5,9,5
52694:4,4,,,,,,3,5,7,3,9,10,9,13,6
52696:1,,,2,,,,2,,,1,3,4,1,3,
52699:,,,1,,2,2,,3,13,2,13,3,7,5,8
52720:2,3,3,3,2,3,4,1,1,4,2,5,3,4,6,5
52786:3,6,5,1,3,6,11,15,9,12,7,9,13,16,12,11
52788:2,7,3,3,3,4,12,11,6,14,17,13,20,18,19,18
52835:42,39,87,145,188,93,146,189,148,213,123,173,227,300,223,229
52838:48,43,45,10,38,34,30,29,39,67,43,53,60,53,42,33
52885:1,1,,,,4,2,13,7,11,6,10,11,10,12,16
""")
SNAP["cob"] = (2011, """
52001:87.5,85.8,85,87.58,82.88,81.29,80.92,104.76,105.07,105.66,104.34,100.24,98.84,96.42
52019:36.6,34.7,34.2,89.44,31.58,30.11,28.78,86.63,89.16,88.03,87.69,78.18,75.65,73.15
52022:128.9,119.8,122.5,91.27,128.36,130.62,135.24,111.86,114.33,110.7,111.54,104.87,102.03,102.21
52036:91.9,88.8,89.5,88.4,86.94,85.35,85.17,87.66,89.53,86.66,84.5,76.43,71.67,71.38
52051:101.1,101.3,103.3,84.93,95.67,91.24,92.31,79.19,79.16,78.34,77.91,71.16,69.26,64.81
52079:118.9,97,94.3,79.44,89.6,88.92,87.35,64.73,61.87,59.74,57.84,55.91,55.85,54.56
52083:84.1,83.1,82.2,88.64,76.47,75.27,71.78,92.8,95.31,95.43,93.72,87.02,86.29,82.44
52110:77.9,73.1,74,88.89,74.3,70.43,66.11,79.55,80.96,81.61,82.34,80.18,77.81,75.12
52203:74.3,71.2,72.3,73.45,69.67,67.01,64.12,92.86,91.02,90.5,91.76,82.49,80.86,75.6
52207:97.7,96.1,95.5,82.45,91.86,90.15,89.72,66.97,66.58,62.91,62.03,59.31,55.97,54.32
52210:53.1,50.4,49.8,86.74,48.88,46.02,44.55,60.54,62.71,61.53,62.99,57.58,52.38,52.89
52215:103.6,102.8,103.3,88.08,100.26,98.99,97.43,85.32,83.63,82.97,80.93,76.31,74.9,75.04
52224:67.9,65.6,65,87.83,62.27,61.68,60.35,66.69,67.24,67.45,67.59,62.26,62.55,58.1
52227:75.6,74.4,74.9,85.75,73.14,70.81,69.52,83.75,84.2,85.09,85.3,82.77,81.08,79.46
52233:54.4,48.4,47,87.17,38.8,40.42,39.15,122.7,132.36,130.78,135.51,134.61,127.64,112.33
52240:78.1,77.1,78.1,84.06,78.68,78.23,76.2,81.14,81.03,81.69,82.82,80.26,82.4,80.04
52250:88,77.7,74.7,79.6,67.31,67.84,63.32,105.27,101.6,97.6,96.98,94.29,86.21,80.46
52254:87.6,82,79.8,85.26,78.67,75.69,74.66,83.99,82.11,78.35,74.86,65.43,64.32,62.33
52256:59.6,54.9,56.1,89.29,56.76,56.82,53.99,50.53,49.15,49.93,51.72,48.47,44.84,42.21
52258:90.1,87.6,90,86.99,88.5,87.85,86.85,90.93,88.52,85.45,85.3,80.22,77.69,74.15
52260:89.8,90,91.8,72.15,88.86,88.19,86.22,86.21,85.58,87.84,86.96,79.29,76.11,73.22
52287:82.5,81.3,82.3,89.69,79.75,77.86,76.07,72.03,70.78,70.3,68.98,63.97,63.69,64.04
52317:89.7,90.6,96.3,86.26,98.95,99.45,100.95,88.34,87.25,85.79,87.13,83.99,84.22,81.05
52320:85.8,81.4,80.6,86.64,79.11,75.66,75,81.37,80.67,79.28,78.94,72.15,71.66,69.81
52323:106.9,102.5,106.2,88.34,102.67,105.1,102.03,99.72,97.92,98.18,95.52,91.34,93.24,90.59
52352:87.3,87.6,86.2,92.22,79.75,77.72,77.53,91.15,89,87.77,86.44,83.16,81.99,75.62
52354:97.5,95.8,98.4,91.01,95.18,96.76,93.32,89.07,88.25,88.96,85.63,80.59,79.52,77.94
52356:76.7,78.9,77.2,88.33,76.41,74.64,73.93,104.51,106.71,108.28,108.53,105.63,104.12,99.77
52378:86.7,84.6,83.5,69.14,82.27,78.06,77.07,88.22,88.51,88.29,88.71,83.35,80.13,76.95
52381:79.7,78.9,84.2,87.03,80.9,75.08,73.58,87.64,86.32,86.64,87.52,81.92,79.64,78.12
52385:66.2,62.7,60.9,80.81,63.81,64.8,65.41,67.07,71.59,72.34,74.55,70.37,71.05,72.77
52390:71.4,59.8,52.3,81.38,46.44,44.78,42.06,83.43,80.1,79.73,79.68,76.25,71.94,68.98
52399:94.8,98.8,101,71.89,98.77,96.78,96.85,90.97,92.33,93.46,93.88,90.52,88.23,86.66
52405:55.8,53.4,53.2,87.12,49.1,47.9,46.13,78.85,78.73,84.23,81.96,80.04,77.96,72.58
52411:88.2,80.7,82.8,87.09,81.5,77.58,76.84,88.77,88.28,86.38,82.91,77.51,72.85,68.59
52418:35,34,31.8,87.07,,27.87,26.72,95.26,95.03,97.9,96.48,90.85,85.57,80.31
52427:62.9,54.4,52.9,84.9,50.84,47.7,40.4,35.71,36.02,33.93,31.47,29.16,30.54,29.41
52435:73,71.9,71.7,82.31,65.27,67.61,70.64,82.32,84.19,83.93,83.9,78.6,76.77,74.77
52473:58.8,57.6,50.3,74.61,38.69,35.3,34.42,56.66,51.63,53.11,53.92,53.96,52.62,51.47
52480:63.8,65.8,61.3,86.49,60.62,61.66,59.26,74.93,74.01,71.16,71.43,64.88,62.86,63.03
52490:91.6,62.8,66.1,75.62,63.49,64.15,65.33,82.27,80.29,83.03,74.99,73.76,71.04,66.77
52506:64.5,63.5,66.2,91.87,62.65,62.1,61.03,84.18,82.69,82.15,81.03,75.41,75.89,71.42
52520:49.7,46.4,46.6,74.29,45.14,44.75,41.99,48.66,47.56,47.84,48.91,46.78,45.24,42.36
52540:76.6,71.9,72.7,84.66,65.62,67.4,63.33,112.22,115.54,121.62,117.69,126.39,122.08,114.06
52560:85.1,80.8,87,84.23,91.38,94.22,98.74,105.35,108.43,110.73,111.49,102.15,103.38,100.64
52565:,,,86.13,,25.69,24.52,72.19,69.47,69.35,69.89,64.31,65.13,63.24
52573:92,90.4,93.4,90.67,91.05,89.3,89.57,91.13,92.5,92.03,92.8,85.93,83.02,80.97
52585:87.4,87.1,92.2,79.89,88.25,88.2,87.1,106.78,106.86,105.59,105.43,98.82,94.13,93.34
52612:77.3,77.3,78,84.9,80.03,77.32,76.76,76.19,73.2,72.46,73.9,70.09,66.76,66.06
52621:85.7,76.6,76.6,81.18,64.17,57,55.47,87.56,87.99,80.9,80.67,77.69,76.81,70.75
52678:50.6,46.8,46.7,82.46,44.07,42.96,41.23,84.59,86.05,90.12,86.87,80.93,80.77,78.93
52683:69.7,67.8,67.9,88.77,68.61,65.25,62.37,88.76,90.66,92.17,92.99,85.61,83.58,81.19
52685:37.9,35.3,34.7,87.77,32.43,32.14,31.4,75.94,75.45,77.41,74.76,70.71,68.44,68.9
52687:81.1,80.7,80.2,89.31,78.56,76.53,73.84,92.67,89.36,86.88,86.64,82.09,77.37,72.91
52693:73.8,72,73.4,82.27,69.46,67.09,66.05,82.57,83.8,86.46,86.6,81.1,78.88,76.93
52694:65.2,62.2,66.3,91.09,66.84,63.97,58.11,77.74,75.66,76.53,77.03,70.53,64.94,65.69
52696:61.2,60.7,72.5,84.74,74.32,70.94,70.75,74.56,69.97,67,67.47,62.97,56.62,55.22
52699:,,,70.28,,20.73,19.41,67.52,66.37,63.87,64.26,64.37,63.79,61.55
52720:82.5,80.8,79.8,90,77.18,77.31,75.83,79.08,79.4,76.48,78.39,74.09,69.54,66.35
52786:91,90.7,88.9,85.48,81.43,77.16,72.93,97.28,98.98,97.6,95.12,91.22,88.85,85.59
52788:79.2,85.1,84.4,86.88,82.34,79.6,76.89,61.98,61.01,62.28,64.44,59.04,57.86,57.17
52835:94.1,96.6,89.1,79.6,84.21,77.47,78.97,68.72,67.16,68.46,69.01,69.22,65.1,66.1
52838:90.1,87.2,90.9,81.33,88.78,87.57,86.97,89.24,88.88,89.44,87.38,82.52,81,79.57
52885:81.8,79.4,80,86.24,79.72,76.12,73.95,84.24,83.27,82.15,83.22,79.14,75.04,74.07
""")
SNAP["des"] = (2011, """
52001:1.86,1.51,1.28,0.98,1.9,1.84,1.24,1.66,1.57,0.7,1.23,2.15,2.11,2.1
52019:7.54,1.95,4.43,2.48,0.61,1.48,1.56,1.2,2.87,0.28,3.57,3.33,2.26,1.72
52022:5.8,1.51,1.87,2.17,1.72,0.97,2.47,1.72,2.9,0.21,2.01,4.08,1.9,1.32
52036:5.36,1.87,2.48,1.62,0.37,0.47,0.57,0.34,0.61,0.65,1.45,3.19,1.69,1.05
52051:,0.24,4.36,2.8,2.16,1.05,2.91,2.83,1.02,0.33,1.25,3.73,1.29,1.27
52079:,8.59,2.01,0.78,2.74,5.88,3.39,3.09,2.08,2.39,1.85,3.72,1.71,4.81
52083:,1.71,5.33,4.97,2.67,2.02,0.39,1.83,1.75,0.31,2.06,1.95,1.53,1.75
52110:,2.93,3.38,3.12,0.45,0.33,0.7,0.36,0.45,1.15,2.43,2.57,2.09,2.16
52203:,1.34,6.6,4.67,1.48,2.12,1.4,1.97,0.87,0.91,4.56,2.7,4.34,3.38
52207:,0.19,6.14,3.73,0.54,1.02,0.06,0.44,0.71,1.01,2.04,2.19,1.71,3.29
52210:0.39,0.74,0.31,1.74,0.33,0.47,0.49,0.25,0.12,0.88,2.99,2.14,0.6,1.49
52215:,0.81,5.41,2.64,0.31,0.11,0.94,0.94,1.7,0.68,3.2,2.77,1.53,1.48
52224:,0.75,1.73,1.71,0.37,0.22,0.54,0.49,1.24,0.76,4.43,2.11,1.37,1.48
52227:,0.78,4.14,2.48,0.37,0.26,0.74,0.55,0.24,0.5,1.73,1.03,1.2,0.86
52233:,2.76,2.85,4.26,0.19,0.69,2.03,1.45,3.32,3.67,7.71,5.11,5.67,4.72
52240:,3.13,4.42,5.05,0.98,5.79,2.01,2.56,2.01,1.85,1.93,2.68,3.2,2.55
52250:,2.21,2.22,2.92,1.04,3.64,4.42,1.74,2.27,6.88,2.52,2.44,1.87,2.09
52254:,,5.59,1.94,0.52,0.36,0,0.19,1.81,0.32,4.71,2.95,0.67,0.41
52256:7.48,2.52,4.7,4.79,0.96,2.61,3.7,3.4,2.03,2.33,8.26,6.8,2.91,2.43
52258:8.23,2.13,2.62,3.94,1.92,2.24,2.03,2.48,1.49,0.71,1.54,1.39,1.71,1.52
52260:5.08,0.98,3.69,4.39,2.19,1.78,1.79,1.4,1,0.67,2.86,1.05,0.89,1.69
52287:7.08,3.04,4.69,1.87,0.7,0.18,1.33,1.08,0.92,0.21,2.65,1.63,1.32,0.73
52317:6.32,0.68,4.36,2.04,0.26,0.77,0.79,0.28,0.73,0.3,1.03,0.8,1.05,0.71
52320:,1.62,4.19,3.87,1.72,1.26,1.03,0.93,0.49,0.19,3,2.09,2.24,0.15
52323:11.28,0.38,2.37,1.95,1.54,0.56,0.67,0.26,0.53,0.27,1.4,2.09,0.79,1.73
52352:7.65,0.3,1.84,3.11,0.48,0.92,0.85,0.43,0.68,1.1,2.16,1.94,1.84,1.9
52354:6.02,0.19,6.05,4.11,0.74,1.81,0.83,1.07,0.47,0.96,1.8,1.06,1.19,0.44
52356:8.18,2.17,1.35,4.13,1.15,0.87,0.81,0.84,1.47,1.18,2.08,2.56,2.04,2.48
52378:,0.61,3.29,2.57,0.46,1.69,1.48,1.44,0.78,0.39,1.22,2.64,2.28,1.52
52381:10.92,1.03,3.09,2.49,0.3,0,0.48,0.29,0.89,0.53,1.04,2.12,1.16,1.71
52385:,1.87,2.76,5.32,1.14,2.85,4.11,0.11,0.54,0.64,2.4,0.91,1.47,2.58
52390:,2.49,5.11,2.61,0.09,0.05,0,0.76,0.21,1.35,0.42,2.11,1.7,3.6
52399:,2.62,3.78,4.95,0.23,0.19,0.35,0.52,1.01,0.57,1.73,3.31,2.06,1.59
52405:,0.81,4.54,3.8,0.34,0.6,1.91,1.45,1.73,0.73,1.67,4.6,2.74,3.73
52411:8.1,0.21,6.62,3.26,0.63,0.7,0.72,0.87,1.96,1.82,4.59,5.32,2.91,2.37
52418:,5.61,2.74,2.51,1.63,2.03,1.97,3.42,0.75,2.96,3.75,2.01,1.83,2.61
52427:,0.06,7.88,4.63,0.41,3.62,1.91,0.26,0.16,2.41,2.67,5.78,2.24,3.61
52435:5.23,1.16,3.71,2.62,0.13,1.3,1.02,0.52,3.45,1.21,6.18,4.35,3.97,2.88
52473:,0.48,0.98,4.59,,0.05,0.27,0.15,0.12,2.16,0.82,2.58,1.98,1.23
52480:4.99,5.71,5.32,1.02,2.23,1.02,0.47,1.16,2.39,0.55,2.66,0.82,0.22,0.65
52490:3.15,0.98,6.19,2.61,0.4,1.17,0.69,1.11,0.74,7.02,1.52,2.31,1.97,1.44
52506:,1.01,2.63,1.26,0.71,0.09,0.18,0.58,0.61,0,0.74,0.57,1.15,0.73
52520:,0.28,3.26,5.1,,1.47,0.93,0.96,2.15,2.14,0.63,1.79,1.67,1.72
52540:8.19,1.21,2.42,1.47,0.43,1.76,1.27,0.3,1.48,4.12,5.22,6.27,3.39,3.66
52560:,0.83,2.25,2.67,0.74,0.53,0.34,0.98,0.35,0.5,2.02,1.67,1.07,1.32
52565:7.41,,1.78,2.57,1.1,0.66,0.79,1.11,0.52,1.51,1.88,0.75,0.44,3.52
52573:,1.43,6.62,2.81,0.18,1.33,2.32,0.41,1.42,0.43,1.45,1.46,2,2.06
52585:3.66,0.33,0.6,2.74,0.09,1.76,1.23,1.96,1,0.13,0.57,1.28,0.67,1.55
52612:,0.36,3.51,2.73,0.53,0.37,1.09,0.34,1.9,1.54,3.68,2.98,2.93,2.55
52621:4.49,0.93,2.95,0.54,0.6,2.53,0.46,0.48,1.77,2.82,3.51,1.01,2.3,1.07
52678:9.97,2.16,3.17,3.74,0.77,1.09,0.57,0.95,0.97,1.28,3.88,2.66,2.92,2.43
52683:,2.84,4.18,3.2,1.81,2.07,1.47,1.91,2.02,0.43,4.16,3.04,1.68,2.15
52685:,0.36,6.8,5.44,0.23,1.36,0.47,1.71,0.65,0.49,3.98,2.02,1.7,2.19
52687:10.05,1.53,3.5,2.62,1.16,1.32,1.11,0.88,1.19,1.72,1.43,1.84,0.95,2.33
52693:8.19,2.17,3.61,3.71,1.47,2.54,3.33,1.69,3.09,0.41,0.46,1.58,1.82,1.4
52694:10.04,3.27,5.35,4.06,3.49,4.25,2.04,3.4,1.72,0.2,6.46,4.65,2.3,3.4
52696:5.35,1.03,8.11,4.23,0.66,1.12,0.83,0.57,1.46,1.41,2.05,6.2,2.17,1.71
52699:6.57,3.11,4.41,3.32,0.85,0.94,2.16,0.8,2.11,0.64,5.63,3.8,3.01,2.79
52720:4.94,2.92,3.06,3.8,2.43,1.32,1.47,0.56,0.87,0.61,1.4,1.35,1.35,0.6
52786:,1.69,4.15,4.42,2.92,1.9,1.91,1.69,1.97,1.46,2.87,2.71,2.02,1.8
52788:,1.11,3.48,2.97,0.45,2.09,0.52,0.69,0.42,0.71,1.54,1.44,0.94,0.81
52835:5.64,1.9,2.66,4.46,1.38,1.44,1.44,1.56,1.68,3.28,2.66,4.32,2.81,3.83
52838:12.29,0.15,2.96,2.45,0.53,1.38,1.64,0.88,1.18,0.55,2.3,1.48,1.49,1.59
52885:,0.74,3.7,2.62,0.73,1.12,1.39,1.66,1.25,0.25,0.69,2.45,0.91,1.29
""")
SNAP["coca"] = (2001, """
52036:,,,,43,,17,2,3,,,,,3,21,24.25,45.6,24.63,16.31,14.89,56.07,57.73,39.96,39.29
52079:713.7,2187,2767,1469,1920,1460,1586,3080,2928,3433,3193,1815,1511,1330,2453.49,3359.37,4590.5,3516.29,3138.09,2569.39,3463.17,3773.06,4367.78,4661.69
52110:,,,,,,,,,,,4,,,,,,,,,,,,
52207:,,,,5,,,,,,,,,,,,,,,,,,,
52210:2,,,,,,,,,,,,,,,,,,,,,,,
52215:1,,,,,,,,,,,,,,,,,,,,,,,
52227:,,,,,2,,,,,,,,,,,,,,,,,,
52233:3,140,301,127.2,329,483,452,250,451,221,194,97,115,107,209.49,527.3,666.8,778.23,684.38,504.04,1387.76,1211.68,1164.3,1448.57
52250:984.49,798,699,649,741,741,1728,2202,1130,748,1080,702,1020,1263,1417.79,2819.91,4630.67,5147.73,5318.32,4674.02,8952.35,8694.67,9257.95,8799.73
52254:,,,,,,91,,19,86,,,1,23,34.9,51.17,97.31,55.8,50.42,36.62,79.38,72.56,65.99,70.41
52256:28.23,102,230,221,508,372,434,273,290,253,203,169,127,133,244.55,573.94,765.36,842.49,782.2,659.08,1576.82,1463.36,1470.12,1623.34
52260:,,,,7,,13,2,4,65,,,1,20,114.28,97.62,176.28,98.48,60.07,47.69,115.58,98.87,50.87,29.89
52520:37.42,45,16,107,153,192,501,407,189,189,207,59,61,66,91.8,157.38,258.1,304.75,347.51,316.37,501.53,537.65,563.88,508.28
52356:1130.45,350,212,520,629,357,123,215,192,139,247,162,370,664,887.49,1132.06,1273.67,928.49,1204.24,967.25,1282.11,1815.79,1974.54,2031.66
52381:,,,,,,,,,,,,,3,30.06,51.43,83.95,39.87,22.73,14.3,40.87,55.72,35.47,1.23
52385:,12,5.88,,1,4,,7,35,24,3,5,3,28,53.35,83.82,146.45,142.47,103.92,86.54,142.44,139.41,130.8,112.81
52390:15,29,1.89,94,27,75,184,164,465,139,63,31,41,78,120.36,119.83,292.3,280.36,279.54,263.19,661.19,527.11,619.75,583.25
52405:10,,41,40,58,,185,66,24,36,35,7,2,11,39.73,212.79,279.18,290.17,272.01,273.54,642.48,580.08,618.59,554.34
52411:,,,,43,,22,5,11,96,15,100,52,122,262.52,284.66,558.06,504.71,419.55,368.25,568.55,544.84,503.47,500.66
52418:,,,,,1,81,2,18,103,33,26,55,93,166.25,177.57,364.39,294.95,261.89,202.48,446.07,386.42,339.76,335.64
52427:1693.61,2398,3532,2175,2139,1002,2593,2240,1323,1207,1563,494,478,586,861.96,1273.22,1716.95,2023.63,2148.19,2123.03,3363.19,3747.99,4003.32,4443.13
52435:,,0.07,,,,1,3,,,,,,,,,1.16,18.12,16.32,13.21,20.81,18.01,23.48,20.04
52473:33.97,119,55,289,38,34,188,140,129,84,222,76,115,118,159.05,239.9,218.44,227.25,199.71,249.87,474.07,376.23,429,455.89
52490:14,690,506,575,517,870,1972,1286,1452,612,1104,712,719,1445,2173.01,2572.72,3355.53,3504.58,3561.9,2898.08,6040.57,4994.15,5530.87,5360.95
52540:15,29,215,236,212,545,773,221,389,235,202,165,301,199,326.09,733.27,960.41,936.4,794.31,646.18,1471.86,1291.86,1368.41,1692.49
52573:1,1,,,,,,,,,,,,,,,,,,,,,,
52612:8,23,15.92,93,1,52,53,6,67,75,68,61,106,93,125.81,333,784.16,808.56,640.93,565.27,839.1,810.06,846.59,806.58
52621:1048.21,2361,3509,2409,2265,1011,2896,2336,1539,1585,2058,460,858,1147,1938.22,2404.27,2733.71,2852.94,2990.16,2940.45,3059.39,4869.69,5407.83,5949.63
52678:,5,8.94,,7,46,24,120,281,531,551,226,336,402,742.71,1394.6,869.33,856.85,701.62,576.36,773.87,676.78,757.91,784.19
52693:,,3.91,,,1,,,,,,,,,,,,,,,,,,
52683:,,,,15,11,,,,,,,,1,4.64,8.28,16.13,8.82,7,7.34,22.59,33.95,16.01,6.08
52696:232.7,258,274,345,213,1303,700,706,802,615,587,294,279,368,283.68,785.28,530.17,560.34,486.34,426.76,1595.08,1571.38,1650.11,1680.56
52699:,,,,,,,14,4,11,10,3,14,19,33.02,61.79,803.08,809.55,626.34,474.26,829.93,677.54,753.49,747.08
52835:1421.36,5585,5234,4806,4004,7045,5642,5865,4682,5464,5593,5065,6612,8963,16960.24,23147.95,19516.93,16046.85,11830.26,8832.92,18109.11,20719.9,22999.56,31300.41
""")
SNAP["pi"] = (2005, """
52001:98.71,98.94,99.08,98.87,99.1,99.32,99.32,99.59,99.59,99.67,99.68,99.72,99.77,99.69,99.72,99.76
52019:94.23,91.11,100,89.66,90.32,96.88,100,92.86,100,100,100,100,100,100,100,92.31
52022:62.07,81.25,100,69.23,82.35,93.75,76.92,90.91,100,100,50,100,100,100,100,
52036:37.7,40.54,85.19,86.11,90,92.86,88.89,100,91.67,90,100,100,60,100,100,100
52051:85,87.1,80.77,84.38,81.25,100,90,100,100,93.75,100,100,100,100,100,50
52079:90.2,87.65,90.77,88.74,86.45,92.15,90.22,96.48,89.39,97.71,99.01,96.49,100,35.27,98.88,65.48
52083:71.43,80.65,100,100,100,100,94.74,100,100,100,100,90.91,100,90.91,100,100
52110:50.18,51.12,73.51,91.95,77.87,96.55,91.04,93.33,95.08,93.75,90.32,93.22,96.55,87.5,93.75,88.57
52203:65.88,80,90.24,94.44,92.16,96,100,100,80,89.47,93.75,100,83.33,87.5,100,83.33
52207:82.05,83.05,86.54,88.89,96.43,92.5,89.47,100,100,100,94.12,100,100,75,100,100
52210:60,80.77,78.05,48.39,43.75,26.09,90.91,93.55,88.89,100,100,100,100,100,100,83.33
52215:64.23,56.64,64.13,51.22,41.86,63.54,69.81,77.92,82.69,92,86.44,84.38,89.29,87.5,100,87.1
52224:48.6,53.68,60.29,45.33,59.32,96,48,74.07,76.92,73.33,75,83.33,80,100,,100
52227:70.66,75.93,67.65,75.1,79.13,75.68,81.9,89.92,95.83,93.23,92.17,89,91.57,77.94,89.47,88.14
52233:88.46,85.71,79.55,83.33,94.34,77.55,75.68,69.23,73.53,76,82.76,84.21,83.87,81.82,72.73,77.78
52240:49.6,76.19,74.24,86.67,93.41,77.78,92.11,87.8,96.97,93.75,81.25,91.67,96,86.36,100,88.89
52250:68.7,69.33,70.9,58.21,59.44,52.62,57.41,75.57,94.44,80.8,62.5,52.59,51.47,66.87,80.13,60.76
52254:8.57,11.76,11.11,18.42,53.85,87.5,71.43,90,100,90,100,100,100,100,100,100
52256:73.68,50,94.67,92.16,100,95.35,100,93.33,100,97.37,94.44,100,83.33,80,100,100
52258:89.26,90.72,92.56,80.45,94.87,88.51,84.29,89.66,74.47,85.51,93.48,87.88,87.5,88.24,91.3,93.75
52260:60.25,62.04,66.67,64.37,86.57,92.86,94.29,91.89,92.31,97.44,96.55,100,100,100,100,100
52287:50.85,71.43,72.34,83.33,100,93.33,94.74,77.78,100,87.5,100,100,100,85.71,75,83.33
52317:61.21,89.38,83.84,90.53,86.21,95.08,89.58,97.37,88.89,95.24,94.44,90,91.43,75,75,90.91
52320:72.16,78.33,73.44,84,87.72,93.55,94.44,86.11,87.5,81.82,69.23,88.24,100,100,100,80
52323:100,90.63,96.55,93.33,90.91,93.75,100,50,71.43,90,100,100,100,,100,75
52352:93.22,98.15,95.65,87.5,95.24,94.44,89.66,90.91,90.48,92,90.48,94.44,96.55,95.24,85.71,100
52354:81.82,78.57,81.82,92.31,96,93.33,100,100,100,100,83.33,100,60,100,100,100
52356:98.41,98.71,98.77,99.16,99.43,99.59,98.32,99.17,99.05,99.63,99.8,99.52,99.75,99.53,99.71,99.59
52378:55.9,93.69,92.94,93.55,95,96.72,94.92,93.33,97.37,91.3,95.45,100,100,100,85.71,96.55
52381:98.57,96.49,89.19,100,91.67,94.44,85.71,88.89,100,100,100,100,90.91,100,100,100
52385:76.47,92.59,88.24,100,88.89,100,100,95.65,86.96,93.33,100,90,100,100,100,100
52390:66.67,38.96,40,88.46,90.38,68.66,93.48,65.38,90,95.45,95.24,100,100,11.76,90.48,88.89
52399:98.06,99.32,99.03,99.63,99.57,98.97,99.5,99.34,99.86,99.55,99.84,100,99.58,99.85,99.36,99.88
52405:48.5,50.41,60.66,67.48,96.88,97.22,79.31,90.32,94.44,93.75,92.86,86.67,72.73,84.21,92.31,66.67
52411:94.85,97.4,91.14,88,97.3,94.74,100,100,100,100,100,100,92.31,100,100,100
52418:91.53,92.55,92.41,88.71,77.5,97.96,97.06,93.1,91.89,95.83,95.45,100,100,94.12,100,96
52427:98.04,94.9,100,83.02,89.47,94.03,71.43,100,97.3,92.59,,100,94.87,46.38,90.7,83.61
52435:92.73,90.24,92.59,92.86,85.71,94.44,77.78,100,95.65,83.33,88.24,88.24,100,91.3,100,66.67
52473:90.91,75.53,60.74,78.99,74.07,75,71.15,61.36,71.01,68.18,80,79.55,71.11,69.77,61.22,90
52480:50,,83.33,100,81.82,70,100,100,100,100,100,100,100,100,100,83.33
52490:97.18,98.47,92.78,95.96,82.46,92.9,88.3,92.2,97.48,98.63,91.41,95.76,86.92,79.41,88.08,74.9
52506:60.34,73.08,90.24,96.43,94.12,94.74,93.75,92.31,90,100,100,100,100,100,100,100
52520:96.15,81.48,97.56,87.5,96.77,96.3,89.83,84.09,96.3,100,100,100,85.71,75,95,95
52540:92.94,68.6,76.47,80.88,96.34,90.41,93.48,83.33,82.35,79.63,75.86,76.47,67.74,84.21,90,82.67
52560:93.02,86.27,87.5,93.1,87.04,95.24,88.46,90.91,80,89.74,88.46,88.89,90,100,83.33,93.75
52565:72.37,66,91.49,92.68,92.68,96.88,90.32,76.92,100,93.75,63.64,66.67,100,81.82,93.33,95
52573:64.52,78.26,73.53,74.36,90,68.42,86.36,91.18,100,100,91.67,100,100,,,100
52585:87.64,86.84,90.41,91.78,93.06,88.89,97.96,95.83,97.56,95.45,91.3,80,100,100,66.67,83.33
52612:26.67,45.6,39.68,35.58,67.68,73.74,90.32,99.18,88.89,96.21,89.47,80.47,69.35,69.86,69.42,58.41
52621:71.6,62.5,65.12,92.5,80.88,87.01,86.54,97.44,96.72,95.92,100,100,100,75.71,100,95.16
52678:96.38,95.2,98.49,99.2,98.8,98.24,98.63,97.83,99.37,99.71,99.63,100,98.48,87.69,91.67,88
52683:52.04,69.27,65.19,68.38,77.12,100,97.22,96.15,100,100,100,93.1,93.75,89.47,91.67,88.89
52685:93.88,98.33,90.24,95.83,97.5,95.24,93.75,90.48,92.86,60,,81.82,100,100,100,100
52687:85.71,95.92,90.72,95.12,88.06,93.94,100,100,100,95.74,91.67,94.12,94.44,88.24,100,95.83
52693:91.41,93.53,97.87,92.54,97.67,98.88,95.71,95.52,94.44,100,84.62,100,83.33,88.24,100,100
52694:86.54,90.32,86.21,97.22,97.14,95.24,96.3,90.48,90.91,100,100,100,,,,50
52696:64.71,72.22,89.36,88.24,100,96.15,100,100,94.44,89.66,100,100,97.56,27.69,100,57.89
52699:87.23,68.25,56.14,60,73.81,76.6,77.5,70.83,71.43,90.32,92.86,86.67,79.17,75,92.31,57.14
52786:58.86,58.05,50.42,58.96,75.82,70.31,80,92.59,73.53,78.13,93.33,85.71,91.67,83.33,100,88.89
52788:56.14,62.12,67.8,65.28,86.67,92,81.82,94.12,100,76.92,100,85.71,50,100,100,100
52835:96.55,99.45,99.57,99.45,99.55,99.55,99.69,99.47,99.32,99.42,99.67,99.38,99.43,95.37,98.93,97.06
52838:85.11,92.72,92.04,97.21,98.65,100,97.73,98.81,98.1,98.96,99.26,98.75,97.45,85.37,98.95,98.72
52885:79.63,80,93.1,89.47,89.66,90.91,78.57,100,100,100,100,92.31,83.33,100,50,50
""")
SNAP["mdm"] = (2016, """
52001:65.9,48.76,57.51,67.17,59.53
52019:33.63,40.29,34.95,55.32,59.4
52022:47.18,50.47,47.86,31.8,34.31
52036:48.11,44.68,31.1,45.54,43.96
52051:45.13,48.96,44.89,47.33,29.67
52079:43.95,46.92,39.27,46.43,47.07
52083:53.53,44.42,48.07,52.6,46.99
52110:47.55,51.07,52.89,39.8,50.95
52203:44.91,50.55,45.94,56.47,53.25
52207:48.26,53.6,48.57,56.27,45.91
52210:56.3,50.74,47.13,58.9,55.74
52215:36.59,43.56,34.95,43.74,47.19
52224:45.61,46.54,47.17,50.21,28.95
52227:43.75,43.01,41.72,46.55,42.94
52233:41.96,42,46.64,55.37,47.58
52240:51.71,55.6,52.91,63.93,65.08
52250:50.63,39.16,29.72,21.82,45.09
52254:49.7,45.95,48.87,43.85,47.54
52256:44.93,43.33,38.95,48.41,44.99
52258:38.67,40.76,44.5,55.75,44.8
52260:36.55,49.07,47.31,57.07,47.04
52287:48.53,37.44,48.01,49.02,31.24
52317:47.56,47.4,47,52.31,49.14
52320:45.12,45.22,43.1,48.13,49.41
52323:41.18,51.73,53.94,55.9,58.12
52352:52.68,52.93,47.48,57.04,30.77
52354:42.44,50.78,52.66,56.65,46.73
52356:49.95,45.49,40.79,63.56,36.98
52378:47.37,57,50.95,55.97,46.86
52381:46.38,47.13,42.2,50.88,51.62
52385:47.64,41.74,44.16,40.71,36.66
52390:25.76,29.12,33.6,34.94,42.34
52399:43.24,36.23,45.27,51.32,54.09
52405:37.8,41.56,41,50.58,45.62
52411:48.09,55,48.99,59.21,57.44
52418:43.94,42.04,45.15,58.98,47.12
52427:27.71,42.52,38.67,48.42,44.35
52435:41.61,43.22,46.04,52.41,46.43
52473:32.58,38.82,39.55,41.11,30.35
52480:49.3,52.18,45.49,58.83,48.86
52490:32.09,44.24,40.39,43.03,45.6
52506:42.47,44.3,44.7,56.74,29.81
52520:24.33,29.95,37.5,53.34,54.4
52540:34.79,45.82,39.3,51.97,57
52560:47.23,48.44,47.55,44.82,48.31
52565:39.5,41.99,42.09,51.69,46.55
52573:49.22,50.14,40.24,52.15,30.92
52585:49.52,50.33,41.23,54.78,48.82
52612:40.29,49.08,35.08,41.23,39.33
52621:35.51,37.7,33.27,41.03,36.76
52678:49.23,49.9,46.87,54,30.58
52683:46.42,43.29,45.53,49.98,50.85
52685:34.29,45.95,51.14,58.99,49.21
52687:42.78,35.52,42.76,39.7,43.65
52693:47.32,49.95,49.72,53.32,50.64
52694:39.22,44.67,39.85,44.72,45.53
52696:24.39,35.83,37.29,54.61,40.97
52699:38.66,34.24,43.4,46.79,41.44
52720:50.5,47.43,41.41,53.65,27.21
52786:47.21,47.11,42.91,52.05,50.14
52788:44.2,54.36,50.25,54.67,56.04
52835:41.13,33.48,32.12,45.71,44.56
52838:51.65,46.34,39.23,43.91,53.77
52885:41.58,35.53,33.36,45.83,41.31
""")
SNAP["idf_transf"] = (2005, """
52001:67.85,67.61,71.59,72.52,68.02,37.38,59.75,59.91,66.43,68.11,68.91,60.51,61.1,59.66,68.65,69.59,50.54,69.34
52019:72.11,78.49,83.04,89.81,83.03,92.83,82.56,89.67,84.1,92.64,68.27,91.57,83.95,87.39,90.29,94.49,85.5,86.63
52022:76.62,77.62,82.06,93.36,89.14,93.7,91.3,93.36,95.03,82.79,56.03,85.94,92.09,86.19,92.54,89.89,92.93,90.17
52036:94.03,97.9,96.98,97.82,96.05,90.43,89.19,85.91,86,88.84,90.55,82.27,73.97,85.61,90.74,84.03,88.21,54.22
52051:79.57,95.88,91.4,90.97,78.34,78.91,79.68,85.8,90.97,84.98,90.55,85.63,73.05,88.05,93.74,91.68,87.03,77.01
52079:74.32,80.18,76.41,83.22,76.91,87.29,90.48,91.12,97.26,90.31,94.2,93.73,91.36,87.17,88.57,89.69,89.07,87.18
52083:62.48,75.26,78.96,79.51,87.98,89.79,70.22,84.47,81.66,74.68,69.96,86.48,57.08,56.45,84.78,90.38,84.59,88.31
52110:76.77,75.69,77.03,87.85,89.6,92.29,90.1,94.78,84.13,72.87,71.94,80.52,84.45,82.9,86.64,90.33,84.27,81.73
52203:71.85,78.09,80.32,91.41,86.98,80.5,84.85,83.97,89.41,88.05,90.18,77.66,83.95,75.19,89.43,93.83,86.41,81.61
52207:84.79,85.81,89.63,85.78,92.14,94.84,90.53,93.14,94.56,86.13,87.61,87.71,76.99,81.84,89.16,92.8,91.69,88.59
52210:95.86,72.78,91.16,95.86,93.22,94.26,92.48,94.3,90.38,90.89,61.07,91.59,75.5,80.03,88.25,88.96,82.43,62.99
52215:95.43,96.49,96.09,82.11,89.47,85.57,94.11,87.55,92.03,75.44,70.22,88.32,79.97,85.73,88.82,89.49,82.38,89.82
52224:75.74,78.8,93.79,95.16,96.87,82.15,93.99,90.75,95.93,92.12,87.68,92.2,93.88,92.45,91.77,92.87,84.19,87.39
52227:89.6,94.32,90.72,94.19,88.24,90.28,81.89,87.28,92.2,88.57,88.53,89.04,90.61,84.33,90.68,92.56,81.29,92.08
52233:76.96,78.54,80.29,91.06,91.06,95.51,94.54,90.38,88.57,85,81.6,62.85,60.47,59.16,77.61,95.49,84.31,71.15
52240:64.06,62.26,66.55,72.9,71.92,58.63,78.23,82.99,88.35,89.95,55.07,77.91,76.96,74.56,71.88,75.89,71.95,70.93
52250:72.74,76.07,79.18,75.82,74.01,73.56,81.09,94.86,98.06,93.45,84.75,93.52,96.73,93.03,95.68,91.3,92.47,90.19
52254:91.52,88.48,80.13,81.56,84.81,70.02,81.34,85.58,88.89,68.64,88.87,89.05,63.29,72.22,90.65,90.81,84.48,57.68
52256:80.73,86.36,82.84,93.98,92.1,97.56,85.23,94.68,97.8,90.31,52.86,83.75,81.35,76.28,83.67,94.97,87.1,90.31
52258:64.98,79.66,71.03,88.32,92.73,86.46,75.84,92.04,90.97,89.65,65.18,79.36,76.33,88.97,90.12,92.95,86.38,91.18
52260:70.06,73.13,73.72,87.44,84.26,88.04,93.44,93.65,94.26,93.33,88.39,85.28,81.52,83.52,79.5,85.67,77.96,84.33
52287:79.87,71.24,91.52,93.64,94.16,90.83,90.46,94.22,79.57,68.98,70.75,75.33,87.73,77.35,82.04,89.54,81.43,74
52317:84.59,82.33,72.19,73.24,84.46,91.91,90.49,87.73,89.81,90.97,92.33,87.7,86.3,76.82,85.46,94.39,75.02,89.67
52320:90.9,80.59,94.25,90.23,88.67,81.22,83.65,87.7,81.91,74.49,61.2,84.53,89.82,84.46,92.48,92.02,86.79,83.48
52323:76.76,90.73,88.2,90.34,81.8,89.35,91.32,93.81,77.98,75.03,81.7,67.63,68.74,66.36,84.99,92.83,88.47,87.24
52352:88.68,94.82,96.2,94.44,94.02,94.71,87.48,91.38,86.84,83.9,84.12,84.34,87.23,83.68,78.54,61.93,68.62,75.35
52354:84.87,64.47,80.55,72.92,77.45,76.46,79.22,82.23,94.53,86.48,58.26,62.13,56.14,76.9,83.84,85.15,32.3,42.24
52356:43.23,43.46,48.96,64.82,72.96,50.74,79.76,82.74,84.17,81.71,82.9,81.07,80.13,77.61,79.89,83.86,82.52,79.58
52378:83.47,86.1,79.71,88.92,84.25,85.85,62.86,92.08,89.51,84.8,91.28,86.56,77.64,78.75,82.7,90.87,77.13,77.24
52381:63.73,77.74,61.46,89.13,79.69,93.92,90.66,91.74,87.51,81.34,72.89,87.81,44.48,61.96,91.39,92.63,88.96,67.36
52385:71.4,76.02,80.18,91.27,94.35,90.95,88.05,92.68,95.02,52.4,67.45,75.48,85.21,54.29,88.12,92.11,79.68,80.13
52390:83.79,60.34,84.87,85.9,91,95.03,89.81,96.98,95.37,88.84,70.85,70.34,97.77,89.67,92.25,91.46,78.47,91.65
52399:82.73,85.44,81.54,84.42,81.57,75.87,86.21,86.42,85.49,77.88,87.51,84.84,72.28,73.63,84.88,84.11,84.56,69.52
52405:67.23,81.82,71.09,88.64,87.55,94.59,87.87,94.39,93.43,91.82,74.52,88.56,89.27,85.93,89.35,92,87.42,85.29
52411:91.13,88.77,47.36,88.58,91.65,87.46,89.73,87.9,86.48,91.3,89.7,68.7,82.98,82.86,91.58,95.69,83.34,73.97
52418:59.25,69.12,71.29,94.02,90.67,94.39,86.27,87.84,86.52,87.64,91.67,89.09,62.24,81.47,78.55,92.67,87.48,84.46
52427:78.3,91.58,46.57,83.19,81.54,78.85,94.34,93.98,92.83,89.4,89.52,88.51,91.72,88.16,88.79,89.67,91.67,84.17
52435:83.82,94.68,95.71,92.84,93.97,91.39,84.75,92.59,93.99,79.61,89,79.39,90.93,88.15,89.32,92.93,86.95,91.36
52473:98.61,93.77,95.06,95.62,86.47,94.15,96.38,97.48,98.69,94.15,83.19,80.24,90.41,89.04,83.88,95.95,88.52,92.57
52480:84.71,56.21,82.25,81.57,86.61,85.03,77.06,90.77,87.73,68.53,90.26,80.62,81.14,84.64,81.4,83.65,68.8,53.7
52490:72.87,58.69,65.25,86.01,80.08,73.51,92.97,95.32,91.32,93.75,81.2,73.61,79.49,85.7,93.52,89.8,87.64,90.66
52506:85.29,93.59,87.41,81.31,88.17,91.22,90.17,93.02,60.3,62.1,90.14,65.98,63.21,76.36,87.57,78.89,86.57,67.09
52520:71.69,67.67,91.24,80.13,94.45,88.46,91.48,92.93,98.92,96.57,76.5,93.32,81.6,90.99,89.91,87.89,92.55,84.59
52540:74.99,78.17,85.82,92.63,88.97,92.66,93.67,89.31,85.86,88.34,92.56,91.24,93.99,87.17,85.77,94.31,79.75,76.25
52560:93.6,94.72,92.62,91.23,96.93,91.13,95.25,87.44,86.63,85.25,79.51,88.26,78,80.5,92.09,91.72,83.15,90.69
52565:90.65,82.09,90.65,87.56,94.16,97.42,98.73,95.52,90.85,62.53,83.97,87.17,80.61,87.19,88.39,94.04,92.6,89.73
52573:84.04,79.05,73.34,83.88,74.51,88.76,49.53,59.57,79.39,52.16,79.47,83.29,63.04,75.82,81.19,87.8,77.5,83.1
52585:83.56,81.36,90.02,91.44,94.95,94.37,92.28,91.16,86.64,89.57,93.51,87.24,75.96,82.19,87.28,88.59,86.65,83.1
52612:70.56,69.03,80.1,89.19,85.67,90.1,90.15,67.67,91.36,91.11,58.78,79.3,87.68,89.18,90.4,92.87,94.16,92.18
52621:80.27,75.1,73.62,94.63,92.32,97.84,84.92,93.47,93.73,94.4,91.49,95.21,90,92.52,91.89,92.72,81.4,86.06
52678:78.38,75.67,82.45,85.7,88.94,82.91,72.65,84.21,83.4,85.27,86.15,82.29,83.44,77.7,83.59,82.72,41.08,85.78
52683:89.8,87.85,89.6,88.62,70.52,73.71,74.97,88.98,94.08,91.13,88.62,76.36,75.18,79.83,86.51,80.14,87.44,90.67
52685:79.15,75.55,68.64,76.42,77.29,83.11,81.59,93.36,88.26,61.78,65.13,77.11,92.34,86.14,89.84,89.6,87.6,83.49
52687:55.26,72.61,56.07,89.94,91.86,73.98,87.77,94.85,96.49,94.5,95.01,90.03,82.61,86.57,92.09,93.28,86.41,91.38
52693:74.27,83.38,73.2,88.39,82.34,87.36,81.62,78.84,72.3,90.72,88.03,81.93,81.37,64.95,86.23,92.53,87.08,74.64
52694:77.46,75.25,95.37,95.59,92.32,86.76,88.8,88.13,86.12,64.12,45.85,72.91,82.26,78.39,86.97,82.57,90.45,90.64
52696:85.82,72.08,80.6,93.79,88.85,83.39,91.63,86.59,91.27,91.08,82.2,91.7,87.63,86.37,86.75,89.95,94.67,78.75
52699:82.05,82.18,88.48,95.27,90.02,91.56,89.38,86.28,86.76,89.57,76.18,56.7,87.53,83.05,77.02,90.77,80.37,86.11
52720:90.07,93.05,89.06,94.74,94.85,88.78,87.55,83.09,88.15,80.73,55.94,81.16,82.28,87.3,89.78,89.09,89.51,91.8
52786:63.51,70.91,65.38,85.83,88.76,90.09,91.07,84.91,85.52,69.62,89.66,83.7,88.91,84.16,84.27,86.84,90.12,78.33
52788:67.97,71.19,85.04,86.86,88.59,86.58,88.04,84.64,64.11,66.56,72.7,86.57,73.75,67.64,72.67,92.45,79.71,80.8
52835:85.69,81.52,76.72,77.65,92.2,58.77,93.23,94.46,93.07,88.01,86.43,86.56,92.75,91.99,90.31,91.33,87.1,86.37
52838:73.05,73.57,73.06,77.65,53.24,81.16,69.87,78.55,38.1,87.71,89.2,87.77,87.45,27.86,90.45,86.2,91.05,89.25
52885:70.12,75.76,85.29,92.45,93.18,93.47,82.51,93.71,94.81,74.21,79.25,88.87,88.67,84.99,90.91,95.17,77.21,88.15
""")
SNAP["idf_propios"] = (2005, """
52001:19.59,20.45,20.3,20.72,19.07,98.28,53.2,47.29,46.24,69.9,69.83,74.6,76.66,76.79,79.17,74.14,85.61,85.54
52019:3.72,3.9,5.05,4.76,6.31,29.87,26.26,22.46,15.4,33.82,35.63,31.92,20.37,21.7,31.73,26.9,37.12,38.63
52022:4.34,3.75,1.78,2.31,3.27,20.94,24.04,17.75,12.69,22.9,39.07,22.46,26.06,18.65,28.19,23.59,28.09,34.52
52036:2.13,1.89,1.75,1.47,1.5,22.6,14.03,14.28,24.58,31.86,33.76,28.24,29.77,28.12,28.52,29.49,27.39,31.68
52051:3.81,3.07,7.86,5.02,6.59,36.38,30.21,19.86,22.63,30.7,40.13,38.65,32.21,18.45,16.6,11.37,18.61,30.87
52079:24.24,19.82,10.25,12.08,12.79,67.18,60.96,49.69,23.33,61,48.76,42.9,58.69,64.62,63.9,46.66,51.69,42.29
52083:5.69,4.49,5.22,4.29,7.09,43.85,35.86,29.92,28.21,45.38,38.97,33.17,29.78,39.26,40.02,36.5,35.4,41.87
52110:8.63,7.11,7.72,7.06,6.85,41.56,32.91,24.25,38.76,43.14,62.04,46.43,50.25,56.15,59.01,43.61,48.32,55.23
52203:2.92,2.96,4.56,4.6,3.24,24.6,24.87,16.39,16.76,5.66,24.51,26.26,24.29,28.01,34.82,28.99,28.25,47.29
52207:1.55,7.95,5.2,1.78,4.1,21.57,24.44,26.79,25.81,25.62,29.65,31.14,29.93,39.58,32.79,21.22,30.25,42.34
52210:1.24,0.71,2.27,2.55,2.31,15.51,15.85,11.11,16.62,24.89,32.32,28.07,28.99,21.69,37.93,34.74,51.43,65.26
52215:2.69,3.05,2.09,3.31,2.26,20.11,24.15,19.52,27.45,38.11,41.32,39.58,29.15,35.92,41.65,44.72,42.23,41.4
52224:5.39,2.64,3.45,2.27,1.17,61.14,10.94,17.85,23.25,19.99,17.49,25.83,22.08,22.89,33.16,24.64,50.86,51.51
52227:3.96,3.98,4.94,4.26,4.28,47.19,50.9,46.41,48.56,54.24,57.63,44.48,55.42,58.56,52.51,43.31,42.7,65.65
52233:5.82,6.28,3.84,3.1,4.5,18.35,9.27,10.9,13.71,23.39,36.99,21.57,19.43,30.46,37.58,11.84,36.73,43.71
52240:17.23,16.34,18.03,16.05,15.44,66.15,46.42,55.28,54.25,63.27,67.96,52.19,55.04,63.49,62.48,71.93,61.87,61.55
52250:26.91,23.47,19.79,20.15,19.51,77.29,14.09,25.33,13.72,40.02,46.02,23.01,10.55,21.48,17.6,26.67,37.33,34.64
52254:8.28,8.06,7.21,5.19,4.08,32.82,43.21,27.28,35.14,41.59,28.07,21.55,37.18,36.53,32.13,23.12,44.08,43.92
52256:3.75,2.67,2.66,2.68,4.76,10.16,4.97,4.48,8.51,14.8,31.44,33.71,20.45,15.81,22.58,11.23,26.57,35.48
52258:9.87,5.12,5.85,5.54,6.67,37.41,32.47,32.55,15.19,24.89,33.57,29.04,26.4,39.69,36.57,34.02,42.39,35.59
52260:7.89,7.82,7.79,6.76,5.56,46.81,27.74,22.46,21.54,27.77,33.48,34.15,31.98,37.97,60.27,47.44,70.26,42.05
52287:2.2,1.79,2.37,2.52,2.58,28.06,19.93,12.37,17.96,18.59,17.69,16.51,23.73,28.3,29.47,25.05,31.96,45.51
52317:13.46,9.02,8.33,5.18,6.81,42.98,40.96,50.86,36.46,37.67,42.55,36.17,38.16,42.42,60.04,40.93,51.23,48.21
52320:7.69,3.57,4.12,4.14,7.02,39.74,29.03,24.33,27.09,33.97,43.94,32.16,30.61,33.04,40.37,30.6,37.15,40.96
52323:8.09,6.58,7.59,7.81,5.5,40.2,37.11,22.96,44.34,34.63,34.34,24.64,33.99,44.01,42.92,25.69,40.73,48.21
52352:9.67,4.11,3.52,4.66,3.7,21.25,21.43,16.75,19.18,32.13,32.91,32.23,28.17,27.57,39.28,73.54,64.05,62.36
52354:14.92,17.09,15.02,13.74,17.78,48.46,52.99,52.11,29.05,39.09,53.47,28.27,39.17,39.26,33.42,52.16,44.31,69.84
52356:26.25,24.4,24.97,23.26,21.37,85.27,77.5,78.93,80.62,84.42,83.17,77.23,79.67,78.3,85,84.35,82.53,75.05
52378:9.45,9.8,7.47,6.68,6.25,37.24,35.79,28.96,27.42,37.75,31.27,31.31,51.51,39.09,43.58,28.2,38.37,43.91
52381:4.44,5.16,2.65,4.34,3.79,27.76,29.66,27.01,24.7,32.6,44.82,32.14,34.39,39.76,31.55,24.13,30.66,30.25
52385:4.19,5.95,4.97,4.17,4.07,24.92,24.29,11.57,12.65,21.88,36.44,30.83,17.39,22.56,22.69,29.14,48.37,26.28
52390:1.6,4.82,0,1.54,4.3,8.61,10.68,6,20.55,2.85,35.56,17.2,12.7,20.88,26.51,28.89,20.53,25.01
52399:12.58,11.6,10.95,11.21,8.84,69.48,63.26,51.64,51.04,57.64,63.19,54.07,50.7,51.25,63.16,62.99,62.71,64.45
52405:11.01,8.92,7.4,8.61,10.16,12.67,35.11,19.42,25.43,29.45,42.75,35.2,30.21,35.77,41.75,27.56,42.58,48.34
52411:6.64,5.16,20.27,4.09,3.77,29,25.67,24.21,27.46,30.62,27.08,15.24,24.9,37.15,24.49,23.29,32.52,53.37
52418:5.57,5.16,5.49,3.32,3.5,21.08,19.5,13.02,24.72,34.53,37.19,24.06,32.3,36.8,27.43,21.52,40.14,45.99
52427:4.52,5.93,0,4.07,2.34,13.69,9.85,12,23.73,20.69,36.4,21.92,20.87,31.24,44.05,26.12,37.42,30.23
52435:5.81,4.29,3.38,3.7,2.11,26.08,25.6,27.52,17.73,45.88,41.08,23.5,33.89,37.81,43.87,25.1,27.19,40.91
52473:1.39,5,4.71,4.38,5.4,7.43,16.54,6.11,5.45,16.24,29.97,4.61,13.1,15.64,50.17,16.83,18,19.5
52480:13.18,10.89,12.24,11.68,11.08,40.67,23.75,21.85,39.49,27.09,29.28,13.51,30.24,27.82,30.93,19.95,23.49,31.12
52490:10.28,16.81,13.12,7.12,6.64,53.34,7.91,30.34,42.56,36.72,43.33,37.27,45.73,52.71,38.79,40.31,40.99,32.3
52506:3.01,2.98,2.98,3.36,2.55,28.29,27.84,17.44,40.08,36.21,36.04,21.66,30.86,31.12,30.43,21.39,33.13,69.49
52520:12.45,10.37,8.76,4.25,3.56,19.28,9.98,8.86,3.93,12.57,12.03,6.64,12.72,18.93,32.67,19.72,19.85,31.04
52540:8.09,8.32,6.49,6.41,9.89,40.79,35.17,35.5,25.37,50.65,39.66,27.31,33.17,36.66,43.19,38.76,59.7,70.69
52560:4.46,2.63,3.37,2.72,1.04,19.88,17.82,15.8,19.42,29.88,37.35,26.08,36.89,22.42,27.64,19.88,34.02,47.65
52565:0.24,0.95,0.24,0.89,0.53,6.45,5.06,5.86,12,12.19,21.44,25.6,15.46,17.5,18.18,19.4,25.45,30.86
52573:7.07,6.89,8.41,8.67,7.71,42.99,43.2,58.5,45.75,61.52,62.48,47.98,54.85,47.79,53.67,51.47,53.69,45.94
52585:13.15,8.95,8.05,7.36,4.44,33.41,38.21,32.35,34.01,47.25,48.38,51.95,48.25,49.84,47.82,45.87,51.98,43.01
52612:14.48,18.85,17.72,8.8,13.57,54.55,49.29,47.14,43.56,45.4,26.02,45.2,43.33,41.32,42.49,41.24,32.46,34.81
52621:4.15,2.83,4.8,5.37,4.51,13.8,10.75,15.62,14.03,14,18.83,0.48,17.38,17.26,42.25,32.45,39.68,47.15
52678:19.81,11.74,11.04,10.4,6.07,65.31,52.98,38.85,43.44,45.94,47.58,41.41,38.78,44.22,47.95,47.98,49.27,50.92
52683:9.08,10.6,7.49,8.53,6.66,55.03,42.93,42.01,41.33,49.27,62.69,54.91,49.48,51.45,58.13,48.07,57,61.29
52685:3.11,4.79,6.06,4.31,4.45,33.29,26.7,29.82,27.63,35.83,20.1,30.98,25.73,29.13,27.68,18.83,25.51,40.44
52687:4.38,2.94,1.61,3.7,2.28,22.06,15.08,14.58,27.41,32.98,45.02,39.52,34.87,38.19,35.75,30.63,39.4,37.9
52693:8.24,7.93,7.24,7.83,7.36,43.39,37.37,31,36.59,36.58,45.49,30.44,44.27,52.14,44.69,30.97,44.54,56.13
52694:8.96,1.97,2.69,3.93,6.69,15.37,24.28,32.67,36.93,22.73,50.75,26.96,16.27,38.07,34.56,23.7,29.37,27.75
52696:5.53,23.08,13.44,5.7,4.21,20.12,15.32,36.44,35.41,18.51,27.51,22.97,21.13,34.85,31.12,29.33,20.19,33.46
52699:10.46,17.75,8.49,3.62,6.82,28.19,26.86,19.37,24.54,39.4,38.47,41.58,29.05,39.86,68.06,31.84,29.25,42.89
52720:2.11,5.79,4.63,4.88,4.14,39.21,31.57,32.28,30.36,32.58,34.63,39.67,36.82,34.69,40.95,33.32,31.32,31.26
52786:11.34,10.13,11.83,12.34,10.22,46.07,41.02,31.38,46.39,19.63,44.51,35.82,45.11,50.21,49.82,36.99,52.51,67.02
52788:13.92,11.25,14.44,11.12,8.95,42.56,26.24,25.68,27.59,41.21,36.29,30.48,17.84,35.01,51.68,52.72,59.29,54.2
52835:13.63,10.44,9.69,5.62,5.09,78.82,79.78,58.73,82.11,81.82,83.96,80.94,69.44,66.59,67.29,71.86,82.55,84.13
52838:21.1,18.58,16.65,12.59,7.67,73.61,62.16,58.43,74.54,57.91,60.32,49.04,46.09,2.82,64.05,62.57,54.78,58.96
52885:8.27,7,8.6,6.66,6.01,27.77,33.72,16.06,21.68,35.93,33.98,18.31,14.52,25,30.25,22.06,45.2,41.57
""")
SNAP["idf_inversion"] = (2005, """
52001:89.56,90.55,89.8,89.61,88.89,89.05,88.31,87.31,84.2,89.61,90.31,89.17,89.41,89.6,89.67,89.3,89.24,89.47
52019:89.17,89.77,89.48,85.22,89.21,89.96,86.31,85.28,92.79,90.41,93.3,88.83,88.44,88.59,91.18,92.98,88.82,88.09
52022:87.28,79,89.49,86.38,90.17,87.76,86.42,87.27,87.5,88.82,92.93,91.63,92.28,91.95,92.36,91.64,91.62,92.41
52036:89.22,86.76,88.63,87.39,90.07,89.35,86.68,92.28,88.88,92.05,91.9,90.7,92.61,90.81,88.8,89.2,91.12,95.77
52051:85.23,77.07,86.63,89.88,89.92,90.57,89.26,88.24,88.96,90.02,91.48,92.02,88.97,86.53,85.55,86.67,89.12,91.52
52079:86.2,79.52,88.11,85.39,89.51,88.69,88.12,90.66,92.47,94.16,96.95,94.78,93.78,94.37,94.05,93.98,94.47,94.69
52083:90.34,88.76,90.56,84.62,88.4,91.39,90.48,85.1,90.68,91.35,92.96,89.17,92.34,91.33,93.36,88.29,89.95,87.85
52110:87.59,85.73,88.49,90.13,89.98,90.02,90.94,90.97,94.75,94.22,96.04,95.23,95.3,93.78,93.22,93.56,93.23,94.06
52203:91.98,90.75,89.24,87.69,89.55,90.74,88.7,88.52,92.08,91.53,91.33,88.89,88.47,91.99,91.8,91.71,91.24,93.51
52207:85.48,86.6,90.59,88.43,87.57,87.67,88.69,91.76,92.98,92.91,89.94,92.62,93.76,90.45,89,90.99,88.15,91.69
52210:91.09,76.86,92.15,87.73,89.16,88.85,86.13,88.03,91.16,90.94,93.25,87.72,91.77,91.34,89.23,89.47,60.11,96.22
52215:91.11,89.49,87.66,88.87,91.39,88.56,87.44,90.27,91.6,93.09,93.7,89.55,91.23,92.19,94.5,93.33,93.47,93.41
52224:86.31,83.27,87.73,84.96,89.2,88.31,85.51,92.88,95,94.32,94.68,91.91,89.7,92.58,89.97,92.91,92.25,92.93
52227:92.8,92.57,94,94.86,95.23,94.59,0,95.23,96.25,96.43,97.88,96.13,96.34,96.66,96.64,96.35,96.6,94.79
52233:88.61,88.74,89.01,85.39,90.7,88.97,86.41,88.37,90.98,91.23,93.91,91.47,89.59,91.26,89.53,90.18,92.99,94.25
52240:86.28,87.15,85.07,83.35,82.97,87.45,85.21,83.28,88.33,90.32,90.18,86.68,86.36,84.28,88.43,90.77,94.62,87.1
52250:79.44,80.52,78.19,82.29,87.11,84.36,81.99,93.96,94.7,96.19,96.08,96.03,95.27,94.57,93.93,74.79,94.06,92.01
52254:84.96,81.25,88.42,86.17,90.99,91.29,84.8,87.77,92.19,92.39,91.93,88.86,92.15,90.88,85,90.26,89.74,95.57
52256:86.42,87.94,88.17,89.16,90.16,88.82,88.59,88.78,93.43,93.77,95.49,91.09,91,89.98,90.51,88.91,92.55,92.15
52258:88.95,91.5,93.44,88.54,92.07,91.86,90.24,90.88,92.95,93.49,94.92,93.41,95.34,93.52,93.82,95.75,93.92,94.06
52260:89.82,87.4,85.78,81.13,84.97,89.47,86.1,88.04,90.8,92.62,90.63,92.04,92.82,91.89,92.62,88.94,89.96,92.1
52287:91.22,89.4,83.79,84.14,86.63,89.46,84.06,85.48,89.52,91.64,88.26,90.99,90.23,90.89,90.09,91.24,93.92,90.76
52317:87.81,86.7,89.41,90.28,93.54,90.55,92.43,91.2,92.12,93.17,92.52,92.02,93.57,94.16,94.37,94.1,93.54,70.87
52320:90.86,88.87,90.09,90.76,91.98,89.75,89.51,91.89,93.05,93.25,92.21,89.33,91.03,91.96,93.17,90.75,82.68,91.58
52323:85.65,85.66,88.69,84.07,87.66,89.43,92.14,91.43,88.54,88.18,89.21,86.06,88.51,89.63,87.89,90.98,91.98,68.54
52352:87.33,87.35,89.08,85.83,87.69,87.48,0,84.82,89.58,91.4,90.91,88.56,90.13,90.89,90.63,89.51,92.73,91.12
52354:79.59,69.03,85.79,88.63,86.57,89.45,83.05,86.07,95.69,94.99,95.32,89.62,90.86,88.53,88.15,89.24,96.49,95
52356:79.41,80.64,82.37,75.22,84.81,89.85,90.41,89.2,89.23,89.44,90.2,88.64,88.01,87.62,88.21,89.33,90.89,89.99
52378:85.09,82.31,85.57,86.86,88.84,88.71,92.01,91.94,95.25,94.23,94.23,93.86,92.62,94.6,93.16,92.88,92.92,93.56
52381:91.98,94.2,92.7,91.12,90.45,89.72,93.17,88.8,90.59,91.04,93.04,90.4,92.78,93.24,91.77,91.09,91.9,94.09
52385:89.88,88.25,89.72,83.3,87.43,88.39,88.18,86.7,89.14,90.56,92.15,89.61,89.2,92.11,90.68,89.39,88.22,89.27
52390:89.51,89.24,88.27,84.24,81.92,83.73,87.44,91.05,94.61,92.53,95.23,94.06,92.69,86.67,87.66,90.8,83.44,90.88
52399:83.64,88.67,90.66,89.01,91.3,91.16,87.96,90.99,93.36,95.02,96.43,92.83,93.69,94.35,94.24,94.55,94.92,96.25
52405:86.6,84.27,88.56,88.31,91.65,89.91,85.99,86.97,88.68,90.62,92.55,90.13,91.11,90,92.46,89.94,89.98,93.58
52411:87.45,87.05,74.1,85.33,90.43,89.54,85.85,89.32,91,88.49,88.09,88.76,92.79,91.95,91.52,92,94.05,95.57
52418:89.22,88.53,89.72,86.17,88.9,87.3,88.22,87.99,91.42,92.35,94.23,93.75,94.7,93.2,93.24,92.03,93.33,93.98
52427:83.75,92.02,78.31,78.78,80.92,81.57,85.29,86.42,86.77,90.57,95.86,91.1,91.64,91.39,91.8,90.43,93.3,92.02
52435:85.66,91.16,87.33,88.3,92.78,89.29,87.19,88.67,89.11,91.17,91.34,90.64,92.34,91.97,90.53,88.98,91.28,91.18
52473:77.61,81.85,80.94,87.29,83.29,88.11,97.77,91.29,86.84,90.46,88.54,90.91,89.44,89.34,89.92,85.23,88.98,85.09
52480:79.5,87.14,82.18,79.64,76.78,78.66,81.21,83.54,89.84,89.26,88.12,83.74,90.65,86.29,86.32,85.77,85.39,93.36
52490:87.7,88.83,64.91,89.52,91.08,89.24,80.88,87.92,91.08,92.62,94.27,94.99,95.48,95.78,94.35,93.1,94.96,95.76
52506:90.37,91.52,85.91,87.56,91.12,88.53,87.87,89.29,92.62,94.05,93.33,88.49,92.93,89.25,89.83,90.91,91.55,96.08
52520:83.99,54.32,87.73,89.59,86.02,87.69,86.08,83.23,95.51,84.74,89.11,83.14,87.84,86.27,89.66,89.74,89.87,91.13
52540:89.37,88.78,88.84,87.51,89.33,90.15,91.27,92.69,94.22,94.48,94.35,92.21,94.5,92.21,92.46,94.44,92.23,92.39
52560:90.16,89.23,89.96,89.84,89.85,90.41,89.28,91.11,94.26,93.52,94.49,92.71,94.26,94.1,93.72,93.49,94.14,93.47
52565:91.29,92.26,91.29,92.84,91.37,90.82,88.78,88.87,89.07,90.19,94.95,92.37,90.94,91.05,90.47,88.92,89.61,91.77
52573:89.52,90.89,90.22,87,89.02,88.43,89.32,92.63,92.46,94.79,93.74,92.76,91.32,92.7,92.89,90.87,90.83,91.59
52585:83.07,88.34,87.57,88.5,91.8,92.35,93.93,88.51,96.14,95.14,95.2,94.08,93.63,93.82,93.19,92.54,91.5,91.58
52612:88.73,89.51,89.56,89.45,89.64,92.77,92.8,94.52,93.73,91.8,94.72,90.62,91.97,91.58,92.51,93.33,93.14,93.49
52621:86.95,92.44,91.01,87.92,77.28,89.43,90.52,89.02,92.38,91.44,89.75,88.64,87.34,82.97,90.44,91.45,93.57,94.72
52678:91.41,91.49,91.22,90.26,92.52,90.92,91.06,92.03,94.33,94.88,94.3,94.21,93.01,94.11,94.45,93.64,93.54,94.32
52683:89.98,88.83,89.84,89.71,91.43,93.28,91.74,89.84,93.25,95.17,95.4,92.4,92.88,94.34,94.81,92.64,91.91,93.29
52685:90.55,91.55,90.86,87.36,89.85,87.15,90.92,92.87,90.62,93.15,93.48,88.11,87.56,91.39,89.26,90.4,93.63,93.14
52687:92.63,66.43,87.67,90.11,89.09,90.39,91.02,92.31,96.58,97.16,97.09,95.83,95.39,95.72,95.98,95.42,95,96.24
52693:91.55,90.47,92.24,89.49,90.74,90.64,84.26,90,93.84,94.22,96.16,93.77,92.96,93.38,94.19,92.45,94.57,92.63
52694:86.6,85.66,89.84,86.47,89.37,88.45,81.61,90.41,88.36,91.94,93.91,88.26,92.78,91.01,89.14,90.8,89.67,89.31
52696:82.55,80.3,73.27,92.56,93.18,94.42,92.41,93.87,95.96,94.37,96,93.33,90.12,90.19,88.5,87.35,93.24,93.76
52699:80.86,63.65,84.96,88.89,89.85,90.3,88.48,89.04,91.35,92.46,94.04,90.36,93.02,92.64,92.55,90.75,90.35,91.43
52720:87.88,87.46,86.89,80.37,85.39,90.2,85.85,89.81,87.48,90.4,94.09,91.47,90.29,90.56,88.91,89.44,89.37,91.47
52786:90.18,89.91,89.58,88.04,88.9,89.67,87.03,89.23,93.1,90.12,94.35,93.47,93.37,93.42,93.18,91.63,93.54,93.75
52788:89.22,90.17,85.87,85.86,88.19,86.61,86.66,89.05,92.05,93.46,89.34,86.22,86.85,91.95,89.53,89.36,86.67,90.45
52835:85.66,91.99,95.1,94.61,95.73,94.4,95.41,95.97,94.73,95.08,92.17,94.77,94.25,94.32,94.23,94.13,95.03,94.27
52838:87.54,83.96,82.44,86.79,89.08,92.3,90.67,90.09,92.76,91.57,93.2,91.09,91.49,93.14,93.72,93.23,95.22,93.84
52885:89.62,88.91,90.4,86.12,84.68,87.44,90.72,88.41,93.46,93.14,93.48,91.5,89.7,92.15,92.4,87.04,89.56,89.22
""")
SNAP["idf_idf"] = (2005, """
52001:66.74,68.22,70.9,71.04,65.87,84.06,75.14,74.52,69.92,76.19,75.95,76.07,75.81,76.85,75.21,74.25,78.95,76.02
52019:62.96,63.22,59,54.85,56.78,58.58,60.43,57.97,59.39,61.24,67.32,59.71,59.29,57.47,59.23,59.64,61.77,58.61
52022:63.53,61.55,66.66,58.14,58.16,57.53,59.93,56.28,55.4,59.87,70.44,59.4,61.31,59.41,61.57,58.43,62.42,60.78
52036:52.83,50.4,53.58,50.41,55.7,58.67,57.82,62.46,62.96,63.74,65.22,62.93,65.01,60.25,59.05,61.37,60.06,65.74
52051:60.37,47.81,56.67,61.12,60.01,66.83,65.95,62.18,62.99,63.28,64.93,66,64.16,56.42,55.32,56.6,57.18,62.23
52079:66.35,62.53,61.78,58.43,62.19,68.01,61.69,62.56,55.2,68.91,65.56,64.87,67.17,70.45,71.06,67.94,63.33,66.38
52083:67.84,64.46,65.87,57.34,57.49,62.73,64.12,59.28,62.08,69.91,68.72,62.14,65.99,68.35,63.79,60.67,59.93,61.55
52110:64.51,62.92,67.41,65.53,58.5,64.85,65.18,58.83,66.73,69.45,74.36,66.88,67.57,68.82,68.91,63.47,66.07,68.04
52203:66.23,65.02,64.3,63.2,60.11,64.79,63.96,60.1,62.08,65.97,62.66,59.53,59.24,64.82,63.57,62.17,61.27,67.77
52207:52.08,58.24,66.69,61.74,57.4,59.45,62.06,62.43,65.52,64.88,62.31,65.06,65.1,65.09,62.14,60.87,58.55,65.18
52210:54.81,58.3,56.11,59.03,58.19,61.17,58.68,58.8,63.35,64.14,70.45,60.16,66.59,62.98,65.47,64.39,54.27,78.32
52215:57.59,55.38,53.55,68.92,55.84,61.39,58.35,61.5,59.01,67.91,69.32,63.03,62.67,63.2,67.89,68.75,66.23,65.72
52224:64.16,55,53.93,49.49,51.7,70.24,54.51,58.55,63.01,63.71,62.74,60.69,58.85,59.92,61.26,61.24,69.18,69
52227:57.04,58.49,65.05,57.04,59.9,64.29,53.46,65.67,68.62,70.87,73,64.01,68.61,70.12,68.6,65.61,66.23,69.12
52233:65.18,64.01,68.74,65.21,61.14,61.94,58.37,59.99,61.48,63.8,68.61,66.07,65.85,68.61,67.65,60.31,69.19,71.03
52240:67.72,67.75,71.45,64.39,59.65,72.56,65.27,65.46,65.82,68.99,74.61,63.82,66.86,68.54,72.53,74.98,72.68,71.54
52250:64.75,63.87,62.17,67.38,64.04,72.86,57.52,64.17,58.4,66.67,70.82,65.06,60.09,64.19,60.16,61.67,67.48,65.1
52254:57.38,54.65,65.82,60.08,57.07,65.26,66.45,60.98,65.6,71.01,65.13,60.54,68.81,66.04,56.18,57.94,65.68,69.78
52256:62.03,61.16,66.92,61.34,60.58,58.66,60.83,55.8,59.69,61.25,72.38,65.48,62.93,62.66,63.55,59.13,62.75,64.29
52258:66.28,63.03,71.39,55.95,59.16,62.84,66.89,62.79,60,60.6,69.31,62.7,63.99,66.16,65.63,66.33,68.31,65.84
52260:65.68,63.38,48.63,37.52,53.88,61.93,55.89,56.14,58.71,60.44,64.03,63.29,65.03,65.79,73.1,66.29,72.97,66.96
52287:65.38,66.48,64.96,51.81,54.93,62.8,59.94,57.98,62.36,64.02,62.31,62.05,61.96,64.65,63.89,63.39,69.5,67
52317:62.72,56,63.37,60.91,59.16,59.88,63.48,67.04,61.85,65.4,64.32,62.29,63.89,66.93,70.2,62.92,68.07,60.12
52320:58.85,55.08,59.71,63.35,61.12,66.18,62.8,62.98,64.43,66.57,69.82,58.99,62.75,62.51,65.07,60.72,61.19,63.07
52323:60.08,58.09,55.21,57.33,57.44,64.23,64.38,57.61,66,57.01,66.77,62.07,63.73,65.52,62.79,61.77,66.21,63.25
52352:55.68,53.08,57.42,56.69,56.08,57.84,43.89,57.43,60.68,64.11,63.95,61.97,60.74,63.53,67.59,80.16,76.62,75.11
52354:58.45,55.66,63.13,69.37,66.13,71.04,69.12,68.66,64.98,69.42,75.25,64.79,68.67,65.92,63.16,69.37,75.46,82
52356:71.76,71.36,74.46,63.29,60.02,73.15,69.45,68.04,65.68,71.03,69.85,66.65,68.18,68.76,68.2,68.47,68.23,70.63
52378:57.17,53.59,52.91,57.65,58.01,63.17,68.81,62.66,63.33,66.93,64.96,65.78,70.93,71.19,68.02,63.99,67.19,67.38
52381:69.35,67.6,73.03,68.15,60.35,60.15,65.21,61.36,61.16,64.92,70.51,63.05,70.9,70.76,63.73,62.08,64.74,68.72
52385:64.88,64.5,67.92,58.26,57.98,60.54,62.47,58.56,58.23,66.78,68.54,65.43,59.99,66.4,61.26,61.35,68.31,62.32
52390:62.65,66.1,51.33,59.65,37.33,52.27,59.19,61.44,65.12,64.78,73.17,67.58,62.16,61.29,60.33,63.58,62.25,62.63
52399:55.13,58.84,63.06,62.11,60.31,68.83,64.89,63.61,65.5,71.43,71.56,65.25,69.47,70.21,69.79,71.1,71.13,75.77
52405:66.12,57.85,71.25,65.68,62.38,59.48,63.99,58.16,60.31,61.91,68.05,63.06,62.47,64.28,66.63,63.52,65.72,70
52411:58.1,52,57.7,43.35,55.82,59.18,59.1,59.56,59.76,58.55,58.9,57.38,61.61,63.87,60.97,61.27,65.77,73.06
52418:68.94,66.15,70,54.41,57.05,59.16,59.96,59.47,63.29,65.45,67.87,63.51,71.11,67.84,68.95,63.54,67.91,70.82
52427:56.66,62.83,39.84,64.04,59,57.88,55,54.69,56.96,60.55,65.44,61.25,61.71,64.13,65.1,61.13,65.82,64.09
52435:55.94,57.19,55.99,57.05,54.31,58.6,60.14,61.18,58.99,69.8,67.49,62.71,64.1,64.55,64.68,60.31,60.86,63.11
52473:51.91,49.84,61.35,57.78,57.99,53.14,69.19,59.49,57.79,61.31,63.77,58.4,55.2,55.46,68.95,56.83,61.7,57.9
52480:58.33,64.19,64.81,59.89,55.51,60.76,62.62,60.55,65.86,68.73,60.34,62.08,66.3,61.95,63.58,62.52,65.33,72.07
52490:66.01,71.07,57.94,68.07,62.8,66.14,57.08,52.93,62.84,62.78,67.46,69.38,69.23,71.72,65.39,66.22,69.16,67.79
52506:58.48,54.3,53.29,63.38,56.69,61.67,62.54,62.33,74.1,73.72,68,62.66,68.74,61.38,60.03,63.54,64.6,78.63
52520:65.79,58.92,67.36,64.67,54.79,58.86,53.95,53.45,54.95,55.31,57.91,49.6,56.5,55.97,61.44,59.74,60.5,66.32
52540:64.33,62.09,64.88,52.85,61.3,64.17,62.64,65.62,65.1,70.09,67.79,61.49,63.88,64.91,68.26,65.67,72.66,75.68
52560:55.65,54.96,61.35,60.55,54.15,59.06,57.62,58.69,61.37,62.89,65.99,60.83,66.68,62.57,62.8,61.19,65.18,65.77
52565:62.25,65.62,67.21,68.65,60.61,61.53,59.96,60.95,61.36,65.36,66.1,64.24,61.85,61.48,61.23,60.14,61.39,62.7
52573:62.17,61.68,66.49,62.77,58.11,63.07,69.7,75.42,68.66,78.05,73.47,68.14,73,68.8,69.42,66.26,67.95,65.63
52585:59.52,59.28,60.11,50.33,56.46,60.27,65.08,61.42,65.54,68.34,66.47,68.18,68.83,67.89,66.63,66.43,65.07,66.17
52612:67.48,67.89,67.99,63.02,64.06,69,68.16,71.85,65.55,64.67,57.16,65.15,64.31,62.51,63.68,66.64,64.8,67.21
52621:63.05,65.46,69.76,53.12,51.22,53.45,61.12,57.56,58.79,38.9,58.08,51.46,46.51,53.58,62.45,61.98,68.38,70.54
52678:67.2,66.11,64.94,62.25,58.34,67.87,69.99,66.03,68.29,68.24,68.36,66.07,64.76,67.41,68.17,69.06,75.77,68.9
52683:61.82,58.51,61.58,63.88,62.38,71.06,68.78,61.93,64.17,67.13,71.99,65.58,65.29,68.3,67.9,64.33,65.09,68.09
52685:65.31,65.26,70.31,64.76,60.88,62.75,65.85,64.74,64.3,70.95,63.8,64.34,57.91,60.73,60.98,62.01,63.13,67.89
52687:64.23,46.63,72.22,65.45,57.44,63.4,60.15,61.36,63.89,66.86,69.12,67.11,67.83,66.68,66,63.97,67.02,65.08
52693:63.5,59.75,67.72,64.23,61.3,63.6,55.18,63.38,66.64,64.67,68.99,66.16,68.22,71.27,66.8,62.15,66.08,69.18
52694:60.67,59.49,58.03,55.19,56.73,54.94,57.72,64.47,65.15,68.19,76.96,64.66,62.78,66.98,64.2,63.82,46.22,60.93
52696:47.64,64.56,53.6,67.91,63.29,67.85,64.05,70.59,70.45,66.19,69.78,65.16,61.35,66.37,63.93,65.62,64.85,69.58
52699:61.24,45.53,61.43,63.9,61.51,64.53,64.64,60.4,62.13,65.38,69.11,70.64,63.54,66.86,75.38,64.58,65.38,68.49
52720:58.54,52.44,55.51,49.93,53.35,61.35,60.3,65.57,59.85,63.77,70.32,64.15,63.08,62.22,63.14,65.2,62.98,64.25
52786:68.64,67.44,64.58,66.05,60.08,65.5,64.09,66.47,69.13,69.51,66.85,65.91,66.15,69.54,69.46,65.49,67.76,73.47
52788:68.73,67.02,64.94,65.72,61.45,64.55,61.47,63.78,67.21,70.26,61.97,59.78,62.59,67.33,67.12,67.73,69.5,69.58
52835:61.71,63.65,67.7,62.2,60.74,63.97,58.31,67.96,66.41,73.46,50.28,67.39,67.34,67.08,67.83,66.74,73.09,71.64
52838:61.58,60.34,65.25,64.86,65.38,70.85,69.36,64.42,81.49,62.81,65.09,58.4,60.65,77.38,68.16,68.09,68.13,68.92
52885:65.93,65.11,62.52,57.41,49.66,55.2,65.83,56.73,61.57,67.2,66.29,59.32,60.45,62.04,60.56,54.91,65.75,62.55
""")

# PIB departamental de Nariño por ramas (DANE, Cuentas departamentales base 2015, serie 2005-2025pr)
PIB_ANIOS = list(range(2005, 2026))
PIB_DEP = {
    ("corr", "A"): ("Agricultura, ganadería, caza, silvicultura y pesca", [939.24, 1107.27, 1087.1, 1100.74, 1095.74, 1153.09, 1298.36, 1361.06, 1438.15, 1558.18, 1767.48, 2067.85, 2072.74, 2229.08, 2328.37, 2612.18, 3153.49, 4194.96, 4522.58, 5184.81, 5851.87]),
    ("corr", "B"): ("Explotación de minas y canteras", [30.46, 39.68, 49.93, 44.78, 60.92, 101.27, 126.84, 276.31, 219.89, 322.07, 486.15, 777.73, 263.73, 147.13, 169.88, 142.99, 145.12, 189.04, 211.93, 217.06, 243.05]),
    ("corr", "C"): ("Industrias manufactureras", [359.19, 402.84, 442.47, 404.03, 384.77, 366.14, 381.69, 394, 401.28, 336.22, 355.42, 369.33, 365.18, 376.46, 386.05, 358.56, 422.55, 506.01, 521.91, 525.05, 568.58]),
    ("corr", "D+E"): ("Electricidad, gas, agua y saneamiento", [121.41, 125.28, 130.15, 133.42, 139.08, 149.14, 158.19, 153.52, 149.85, 147.65, 153.74, 167.37, 182.14, 200.97, 220.22, 235.02, 261.76, 305.67, 363.77, 409.39, 402.34]),
    ("corr", "F"): ("Construcción", [291.26, 332, 375.08, 405.22, 551.07, 508.84, 603.92, 690.45, 927.82, 1032.87, 1182.8, 1456.08, 1361.49, 1384.85, 1436.41, 1119.72, 1115.86, 1214.9, 1207.12, 1231.38, 1122.44]),
    ("corr", "G+H+I"): ("Comercio, transporte, alojamiento y comida", [1241.04, 1345.22, 1485.3, 1524.18, 1567.89, 1635.75, 1771.59, 1809.15, 1950.97, 2025.48, 2275.59, 2607.43, 2785.73, 2926.37, 3153.06, 2978, 3861.29, 4698.26, 5098.76, 5469.68, 6029.53]),
    ("corr", "J"): ("Información y comunicaciones", [193.6, 239.32, 262.52, 263.21, 254.99, 227.84, 226.25, 232.16, 230.51, 226.76, 219.49, 237.24, 250.95, 249.29, 256.83, 244.62, 280.9, 307.79, 317.91, 323.96, 330.68]),
    ("corr", "K"): ("Actividades financieras y de seguros", [122.11, 125.87, 150.17, 178.97, 197.12, 214.53, 239.6, 269.56, 294.68, 312.15, 341.74, 339.18, 386.36, 422.7, 464.82, 483.59, 518.32, 550.54, 607.3, 689.33, 756.68]),
    ("corr", "L"): ("Actividades inmobiliarias", [260.3, 310.97, 356.86, 415.65, 477.52, 540.03, 612.64, 692.64, 773.78, 933.22, 982.58, 1036.92, 1085.13, 1169.79, 1255.52, 1295.21, 1350.28, 1427.07, 1539.79, 1664.77, 1756.53]),
    ("corr", "M+N"): ("Actividades profesionales y de apoyo", [130.39, 138.5, 165.47, 194.51, 222.93, 242.21, 275.75, 309.71, 344.96, 405.6, 426.48, 456.96, 488.06, 512.87, 525.61, 515.8, 574.63, 665.65, 723.54, 760.37, 804.75]),
    ("corr", "O+P+Q"): ("Administración pública, educación y salud", [1108.61, 1358.74, 1503.29, 1718.98, 1893.76, 1963.72, 2156.82, 2410.78, 2640.01, 2822.33, 3119.16, 3419.72, 3723.06, 4049.06, 4419, 4578.11, 5083.46, 5514.01, 6337.46, 7245.02, 7995.87]),
    ("corr", "R+S+T"): ("Actividades artísticas y otros servicios", [118.67, 135.79, 151.47, 170.08, 196.62, 202.92, 224.42, 241.46, 270.74, 297.3, 302.69, 315.8, 352.54, 369.88, 422.31, 373.93, 493.2, 699.49, 840.23, 976.68, 1134.07]),
    ("corr", "VAB"): ("Valor agregado bruto", [4916.29, 5661.47, 6159.79, 6553.76, 7042.43, 7305.49, 8076.07, 8840.79, 9642.64, 10419.8, 11613.3, 13251.6, 13317.1, 14038.5, 15038.1, 14937.7, 17260.9, 20273.4, 22292.3, 24697.5, 26996.4]),
    ("corr", "IMP"): ("Impuestos", [252.9, 327.57, 356.87, 361.58, 375.58, 398.12, 476.68, 501.87, 506.28, 571.4, 616.41, 641.37, 744.71, 796.46, 869.33, 764.61, 965.16, 1313.84, 1362.1, 1432.93, 1596.62]),
    ("corr", "PIB"): ("PIB departamental", [5169.19, 5989.03, 6516.66, 6915.34, 7418.01, 7703.61, 8552.74, 9342.66, 10148.9, 10991.2, 12229.7, 13893, 14061.8, 14834.9, 15907.4, 15702.4, 18226, 21587.2, 23654.4, 26130.4, 28593]),
    ("const", "A"): ("Agricultura, ganadería, caza, silvicultura y pesca", [1481.29, 1657.59, 1569.44, 1415.17, 1336.46, 1358.5, 1448.23, 1571.01, 1726.85, 1726.85, 1767.48, 1729.65, 1841.11, 1887.15, 1915.78, 1996.15, 2045.09, 2000.67, 2000.92, 2084.72, 2155.95]),
    ("const", "B"): ("Explotación de minas y canteras", [68.39, 70.83, 83.05, 73.28, 95.26, 136.78, 134.34, 285.78, 261.36, 376.16, 486.15, 644.74, 226.48, 120.27, 118.68, 78.93, 73.03, 80.25, 84.28, 77.49, 68.97]),
    ("const", "C"): ("Industrias manufactureras", [296.9, 335.9, 360.71, 322.6, 302.22, 307.54, 326.15, 331.46, 336.78, 345.64, 355.42, 354.36, 355.41, 361.11, 366.08, 328.61, 346.51, 363.89, 353.83, 348.61, 364.57]),
    ("const", "D+E"): ("Electricidad, gas, agua y saneamiento", [164.07, 165.34, 164.07, 165.34, 164.07, 167.86, 169.12, 160.29, 155.24, 157.76, 153.74, 152.03, 155.16, 158.98, 160.47, 157.52, 161, 161.66, 163.63, 165.7, 167.99]),
    ("const", "F"): ("Construcción", [611.85, 634.22, 658.18, 623.03, 770.01, 683.74, 752.43, 771.6, 960.11, 1019.22, 1182.8, 1336.14, 1158.55, 1146.98, 1154.1, 903.76, 888.29, 912.64, 834.06, 716.44, 615.15]),
    ("const", "G+H+I"): ("Comercio, transporte, alojamiento y comida", [1600.61, 1678.45, 1774.06, 1794.36, 1776.52, 1843.87, 1972.62, 1999.62, 2079.53, 2180.33, 2275.59, 2372.02, 2404.04, 2443.33, 2524.92, 2289.87, 2817.9, 3085.78, 2940.27, 2989.61, 3088.8]),
    ("const", "J"): ("Información y comunicaciones", [117.43, 156.51, 186.51, 198.96, 198.26, 190.35, 201.09, 216.63, 219.96, 229.84, 219.49, 224.79, 222.23, 216.28, 217.14, 204.58, 236.59, 260.6, 261.42, 258.98, 259.41]),
    ("const", "K"): ("Actividades financieras y de seguros", [158.46, 171.47, 195.12, 211.67, 219.95, 223.5, 245.97, 267.25, 289.72, 315.74, 341.74, 350.67, 370, 384.96, 407.4, 416.58, 429.73, 451.41, 488.9, 495.36, 509.67]),
    ("const", "L"): ("Actividades inmobiliarias", [744.01, 770.16, 793.41, 828.29, 851.54, 874.79, 898.04, 924.2, 941.63, 961.98, 982.58, 1008.42, 1030.28, 1073.88, 1110.27, 1124.54, 1155.29, 1182.74, 1192.24, 1215.33, 1233.02]),
    ("const", "M+N"): ("Actividades profesionales y de apoyo", [291.2, 282.69, 303.12, 321.86, 335.48, 332.07, 355.91, 371.24, 388.27, 422.33, 426.48, 428.98, 440.78, 447.87, 441.49, 426, 457.67, 481.57, 479.82, 477.65, 483.06]),
    ("const", "O+P+Q"): ("Administración pública, educación y salud", [1763.12, 2060.4, 2171.09, 2326.05, 2436.74, 2414.6, 2515.8, 2662.86, 2790.95, 2928.52, 3119.16, 3220.91, 3319.3, 3474.58, 3665.69, 3709.87, 4056.79, 4079.23, 4262.07, 4441.61, 4637.84]),
    ("const", "R+S+T"): ("Actividades artísticas y otros servicios", [214.13, 232.35, 241.46, 249.06, 271.84, 258.17, 273.36, 280.95, 296.13, 299.17, 302.69, 307.91, 324.11, 330.85, 364.53, 315.4, 412.4, 526.47, 583.11, 630.2, 691.66]),
    ("const", "VAB"): ("Valor agregado bruto", [7475.23, 8223.78, 8555.16, 8562.56, 8759.31, 8768.19, 9285.97, 9814.1, 10454.7, 10963.6, 11613.3, 12130.6, 11807.5, 11997.8, 12394, 11884.5, 13011.1, 13498.8, 13533.3, 13807, 14175.5]),
    ("const", "IMP"): ("Impuestos", [385.57, 456.92, 481.2, 469.06, 479.69, 491.83, 544.96, 564.69, 584.43, 605.68, 616.41, 629.52, 635.23, 646.23, 671.03, 632.91, 737.89, 850.27, 821.07, 826.78, 847.01]),
    ("const", "PIB"): ("PIB departamental", [7862.35, 8681.62, 9037.19, 9031.26, 9238.67, 9259.41, 9828.31, 10376.5, 11037.2, 11569.1, 12229.7, 12760.1, 12441.3, 12642.6, 13063.7, 12515.4, 13745.2, 14344, 14348.4, 14627.7, 15016.3]),
}

# GEIH - Pasto A.M.: promedio anual de trimestres móviles (TD, TGP, TO), DANE anex-GEIH-ago2026
GEIH_PASTO = {
    2007: (14.18, 66.53, 57.11),
    2008: (14.02, 65.87, 56.63),
    2009: (17.11, 68.68, 56.93),
    2010: (16.02, 69.59, 58.44),
    2011: (13.40, 69.38, 60.10),
    2012: (12.51, 69.53, 60.83),
    2013: (10.84, 69.38, 61.86),
    2014: (10.56, 69.26, 61.95),
    2015: (9.96, 68.13, 61.34),
    2016: (9.45, 69.26, 62.72),
    2017: (9.71, 68.46, 61.82),
    2018: (8.94, 63.70, 57.98),
    2019: (10.83, 64.48, 57.50),
    2020: (17.60, 61.48, 50.71),
    2021: (13.38, 63.86, 55.32),
    2022: (11.71, 66.95, 59.10),
    2023: (10.57, 69.19, 61.88),
    2024: (11.00, 69.50, 61.86),
    2025: (9.32, 69.33, 62.86),
}
INFORMALIDAD_PASTO = {2021: 54.70, 2022: 55.41, 2023: 54.74, 2024: 54.25, 2025: 56.54}
IPC_NACIONAL = {2005: 4.84, 2006: 4.48, 2007: 5.69, 2008: 7.68, 2009: 2.01, 2010: 3.16, 2011: 3.73, 2012: 2.44, 2013: 1.93,
                2014: 3.66, 2015: 6.77, 2016: 5.75, 2017: 4.09, 2018: 3.18, 2019: 3.80, 2020: 1.62, 2021: 5.62, 2022: 13.12,
                2023: 9.28, 2024: 5.20, 2025: 5.10}
POBREZA_MON = {  # DANE pobreza monetaria departamental (actualización metodológica GEIH 2018)
    'pobreza_monetaria': {2021: 41.8, 2022: 40.8, 2023: 38.8, 2024: 39.2, 2025: 33.4},
    'pobreza_extrema': {2021: 11.4, 2022: 13.0, 2023: 12.3, 2024: 15.3, 2025: 10.1},
    'gini': {2021: 0.514, 2022: 0.496, 2023: 0.507, 2024: 0.512, 2025: 0.486},
    'ingreso_pc': {2021: 533354, 2022: 581376, 2023: 686853, 2024: 718852, 2025: 783314},
}
IPM_DEP = {2018: (33.1, 22.0, 41.7), 2019: (23.2, 18.4, 26.9), 2020: (27.3, 15.0, 36.8), 2021: (22.1, 13.4, 28.9),
           2022: (17.6, 12.7, 21.4), 2023: (16.6, 11.6, 20.5), 2024: (18.1, 10.0, 24.5), 2025: (13.2, 8.2, 17.2)}
RECURSOS_DNP = {2010: 525, 2011: 631, 2012: 999, 2013: 1642, 2014: 1371, 2015: 1631, 2016: 1132, 2017: 1320, 2018: 1096,
                2019: 2022, 2020: 1741, 2021: 2775, 2022: 3764, 2023: 3846, 2024: 1171, 2025: 2063}
CTEI_DNP = {2010: 0.7, 2011: 1.1, 2012: 7.0, 2013: 85.4, 2014: 3.9, 2015: 5.7, 2016: 2.0, 2017: 37.0, 2018: 0.2,
            2019: 76.5, 2020: 2.4, 2021: 66.9, 2022: 3.6, 2023: 2.2, 2024: 16.9, 2025: 2.3}
IDC_NARINO = [(2023, 4.57, 19), (2024, 3.78, 21), (2025, None, 20)]

# Geometría municipal MGN-DANE 2018 de Nariño (respaldo embebido, comprimido zlib+base64)
GEO_RESPALDO_B64 = (
    "eNqdXMuOXDcO/Zdeewp6P7INMLsBZm94ESQ9gQFPOvB0FkHgfx+St0Sp6khRop3Nq3slUnwcPqr/eHn//dfXl+9e/vn6w/tvX1+/f/vy5fXH98"
    "9vv7x8ePnPRfvfy3cf/3haR08//0T/jS4VT//59evbr69f3z/z4j9efhye/PDynTX2lr59ePn59e2/r+9ff+cl98/9++3L7z/LZj++vX396fMv"
    "P7zLfh8//iPnW0j5g7355D99uP4fnWeCye5O8Tk6ojhv2ppoklCSL0rx8hmbbftOMVE+XNt3+k6fPn379uHP2I1LduPFboo39/e5TbfqnaVDRG"
    "Pi/VTGViKEGlMjZJt4iY2hURJLJEbl1thrSXbXksfvbrnLS+7yxZ0L9WZPLtP5wsdIsZ3U5otgTW2UkPleYr9NG6Kc3WV9qwS+3xBKk5LzkTkm"
    "5VCtMDaLmHL7souFRRmDV0qqTEnJKaUfcCOmmMxCTNcTEpMv5eZPxGQLqaK5JW/aFftCGk0Ul7Jqq6lEycE3jiNdOhGiakqs3jLFhUYhgwhM8b"
    "UJLsbMb5Vg1TBs9bym2LaV9/Jho0vYsPg0NVm9kX7inX7VpbOozVlYe6tH5mOMkwu9n50oJWS5UBWcIYuXNd1+sglMyaGxY5yYVLZev+Mjfye7"
    "khpl2GurK3GpK3eH4esJx3R/2bO52FIbNzEX5sZm08wlOcdrnNMbTVZMypWqa6xnU3A1qxMdvry90rC80nDxF+OZ+0ffhu6vWGY4lFTXHgO8yv"
    "Dh3e3llcJeT/j2ojlziDbW/GjFNie260S616zNFTFIVxrHwcQiRluSRrN0mbFTNQiWv1w0vEWx2VJjHiOguVWnHjL4xO6hFPXPztX4RLHWiXtI"
    "be+Rh62i1KWi1LuiBHOmKajBEy2PEk1dyGoJSdSJtEkptTLFqEFlZy+CvpTrtVWXXImiTq6o/EtIgi9ytUoRNxOS1y8nU3iNbpWCeBlyuHVilz"
    "s9XcKS2GCJdfWWj9xMjaIrtesX+QWmZI0kqT4pmMjfsGwaITvRyRSVvZxYt2vyDwzzTkGx27D3Tr9yWemXPGFkZuLNHIkgir8PdDnqIS3rF0GP"
    "MtgYY1NVJnrEuuPUF6O/nugtaAEoCupSyUEQUBnWOH4pVj1N9pcXtIouUwhCcaql9/ARXK0KETrjG/k7s8KO1xOJ7fUWTuSPMN8TwHmMaz4J6H"
    "PGFk0OBPTZatXJZYn/tsMkY+UztrtKyB/GzXcysCtgeD0hGQR/kh3w0Q3bTw116cLBy0eKlLzE+H7DHCooodBw0j+75S0ueWtAxoQz/w0BC2Ma"
    "xj2MjRg/EU0jfgWIiygYkfJw4o3cjLELuV1PJEGup4ZhjWTEUW+Y8rMr8HU5XfkRp0CKmkoWR+SUIM7LJLUd46tQerZAjs2K0y+Kpkn0ojtOoZ"
    "aVCyB4rADBF6YU1yGNyfFxDWXmooPJ6iVRzsq7h6BJkImCbJ3/E3tHn+CEUcoHH23ZD3t3Ae4u0q4AzPVEsr5DpPuc6FsjqQuBMs2yrISBEHxc"
    "Yt8JPu4f3nHn3Io7ecKuKx+iMwz0CAZKED3xuUOvKG+Z6ieAYees3CoruZ4w2MxnsH1yLjh7o5AVNm6iZN9kZxqQCTTzd1R9xw/vLsun1WXJE8"
    "Y65TCphGrZrKIGUROwDqCh4bs77uLSY0bbkNxZFJ3ki2BXWGHCnHL8zo6bZYHUtAJpsLdy5jbCVUHTu3qu/k2T6KsUVrsjGT6zYcYuAY5tACf5"
    "dAayJ3LHuwG/aHyokmtFrXfWIvpa76kfF3D8laEpeDJO7s8OpdXnmIhhcxJabc2PhWQsRo5sbSG0X0Lou6qkI1WZ1sJQeVAznuplj9/ZcEMAdc"
    "HN9YSLyfGsSDqJ9BDYIfQP7+yyabNyr9cTvodwZrKhJlY80+uys/Ta8D2YoZobi6CxrPyO39lwk93qHq4nkpjFWzwK7c8FkxTE1IzCtAkzwDDm"
    "/dlEgYTdYnOSbHUApFibGU6zk0lZ3fD1hHXTh7N6yaSzAN0H7FB459Jj98eX+Bh0vHBHRQx9JwYpXifN4L279i42TvocW6GUpVDuFRRny5lzR4"
    "wf6KuiGEFz+iSe0nbnjhn8BPVDZjDJHobddz44LFP40KwlpEO3hX0pCBeTkAJhZ5L1VeldBar2r/Vp2H0nhLiEzzH0Ws4RwAS1Dl64GaJ8KE7S"
    "ll6YDQyWmZuoa4Kg0li0dIbm0Xfa8luW/JZW20iHfamnti5RnJTZHihSTAyxN5ikMOgboEYMgzgHsdAULz2mmn+rPUzZy0JM1xNxEIe2ga0rKS"
    "qzN9fyAoZBjC4QgDBEYdkfWwPYPoBG2njiHRSyq4zmesL25ONZuJkYC4w3TJI6yM+woI1Fbx/8I0Kf2OVwnJ06LZsWRZsWxh1KBaJLoLM+qkqQ"
    "JZaqhqvy8Cz+PMeocaedGvgVw9cTrkqkehZgJ50qREy1SBisGkmqlfTQZI1I9L40KaraC1WYxfMExRST/hb0wLBPNp5wIyi/7OX41suhaY2zTK"
    "hEMeTk1QNSg1NCpXN17aEnwzmQaj9lVJh1zaYUxvPsxFJWbuR6Im7kFJsApsCUapV1DX0ZHNGCIS4jLttr13uCXf56UdYtR3FcG8Uht35YXAcI"
    "hUcFboBdnDVDhw0ICLH/cJadSJZDXK4NcVEz8TB9RdCOxXso8GMTAGcfcLYA5w9wRmEyxwB9sitEURXbriPBX/fhxO/KBm1rc8bDUI55MJbOsf"
    "yMhWRw85NQAAn2uPlOBstRDt9GOWxwZxVaGwSZpNxrrTiiNRnjwtLVU91zMlwIA4g4ozicZieUZZnF9zJLOkQzz8AEoMsELCOgxnkxKNtDZX/Y"
    "eoduzBLdmNYgtubMFVMTig9ao+1JvtQ+ildUEqxh11uKotMrI6Q0KT8Glpq6X2Xo78jyfe80UrrtqJ4QdZzUU0yjNVRzUxfXj7NVC79UizZBZg"
    "6nUp6b+ZN+Pwzm4OxO/8qOlbhqEV5PiJVizuqIEyf97MeRW+AECotYbR032rIbluzeiyDFHtrzJBcBAWClGNNfsHrMaYattgynJcOphbZ82KvC"
    "4RQYUoQhi8nIMow1w+QzDkfjADWOhVhCEEwxmulZekgUQucadngFDYfoV6zn7/rs1C/UxFz61H2HY5Wkrq9y4LyXzygDdOW8j7cdMkbembKGPl"
    "/n5bxRnV2qMo1BlZ51z3nSl8a++/Oc3sRjoFfpd7ntwy+xqLujpWoPm0ATmANICLrudPG8pBiVZKXLErndkQIVuP3FX777+0LZsIwjNWdUOGKK"
    "4RlFaphJj+fbickvG39ex4zjGaBKkqCUnqaKm7QyV6gqWNlHdIB1T1qS0bJ0MhcIM6ZrjpU1SQE7aRVDBZqk0skI0mrevGdQNJollD6iQr0Kfo"
    "u0qU+HSHOWFE7XdB62ldy0rOTefRg13g9T5Gc4gYgDUcmdkjumxB4N9nFCEBxG1U2HIlhLSQr8NZjuHAXxVdN/+nSVZch0K4KkbfkhLssPseXa"
    "pxO2UFqczdw+j6fiCCuOueIobElSJh863+UyAK3K3D0lt+zUk0cJtXSG3seUqnGkVGdSH91WhMuyInyvcBHUOeuwTGwM7HBiq2jPYPPoF7ANgy"
    "Xhyd2i6J6lixeAl4QXWZ2XJlDq0/nXbHTRrI+8uphWzwyzF5ug0BAmXmo3K7DsF8agI7/hdMwB+rvPPa6J/OGOwL1jBADvgg5oPMxuFN+uEoXr"
    "iRT2T4skz4EWgzFRsvR/k66owh/VoTSiU4FSMt+kUd9JCYFGPFyjhKsV20oRRDFSAQ0uOVU4iV7B2D8bxoeBfSigY5F9UogfON8NneXlrGq+V2"
    "hoQ3fmXyb+E30sSOFZUijNqcThVvDm8Hb9VYm3FPjuFPKqVxmjNoo0+LQWUniWT/YO/R1ykkwpbYm/KlHB3su/tHUSVfNVj0e/lBVRhNwOQ8BD"
    "jNYVXXP1crO/ZzqswvHBHRfJ8mRN6MonxSnKNlRpouW9SB/C0rmB/5u4yOE+t/BqWW6PWm6v5sSyC+dTgeos3MFtLNNcIVGIoO0pAjBEcT3rp/"
    "yBCU4zGMI/hQs45Gs0chQrBZz+axgnClKr7SEySJHHdbhR/EUZfo1EQZO/nHvFxXP5iOpBHTpn2b2bQuBaN60pWrmQtglRUrBjeZ+56I1GHmtx"
    "Mnq6Lkxh8QoLXABaAQEiSkQkOUGbiNuvTjtdiCofNY+Y4jQXr4a5MiXoFVcrUs7qrC2hZ+bTmmZ39EGWYGic85rEUqZygDoBuiZWntS/Q1V9ph"
    "TTrHVUsG2Je1nNrS2sU+Jaj/QcGCSvzNdvurFTj42P6gd2an2UAd21cBO7X0EZgJxmsuzH2aHWZTofWjpviylng/WoUAhkJ1ANPN6zV0TPOfOu"
    "6IEnXjrZOOZyDDTSdeasd5AvfbZ5fbmoAM9WAIYysyW0t1GEu6tc/rI5tF8253R0k6SZ5NlEM1skJWfGTpqcZRMT6Z+47ex0TYkilOo1ItOPtH"
    "hNVDFF7p7zW1mjOI9Wkp1Yjf2Rf+DFMcMpJYosQ3XtIocD7sS09AOh+QFrjD+T08TsQXvo5+VFFKHYtaBQmCBwvBNwH+Bh0AmNJ94lRst+WGz9"
    "MPrnSU1rqhlOKOQwlGKzfxRujDKxQTNduqZkgQHZtTWJf0LFbzVpZy7ycszX2l/mlj9tTqG5vcR/MoLWFPUCVI6Oj3eEqjsysUuo3Grw43oiDV"
    "f6QdMR7EJ9Qp2beDX0fOgd0YMCFqY5fcHLqQnTV2lYkC6remf5GUguqoY0ZGFHxFK4xiAYJhu/vn/QEdSjURjbP2iQln/QoLVLKCKf/WaOOjpR"
    "oIrWXqrNTKHuSNKsKwuwTKbHCDF76v7YMWAyz4qgJyAWgC6CYQTMCKoReE+w+SN8R4g/TwMKv0UJiiYxWfBySkY3HwS2HWNdzh22MTwa77OrTu"
    "a/fvvy/nl9e3d1lIHLmrSF8JcUdHjrE9E+LgMaBL1JYHz2QOilZp5MlMzbqg7Rye4+2zoJsCLqT9/+DysqN/4="
)



# -----------------------------------------------------------------------------
# 8. TRAZABILIDAD DE FUENTES OFICIALES
# -----------------------------------------------------------------------------
FUENTES_META = {
    "pob": ("Población municipal (proyecciones 2005-2017 y 2018-2042, CNPV 2018)", "DANE", "https://www.dane.gov.co/index.php/estadisticas-por-tema/demografia-y-poblacion/proyecciones-de-poblacion"),
    "ipm2018": ("IPM municipal y privaciones, Censo Nacional de Población y Vivienda 2018", "DANE", "https://www.dane.gov.co/index.php/estadisticas-por-tema/pobreza-y-condiciones-de-vida/pobreza-y-desigualdad/medida-de-pobreza-multidimensional-de-fuente-censal"),
    "va": ("Valor agregado por municipio 2011-2024p y por grandes actividades", "DANE", "https://www.dane.gov.co/index.php/estadisticas-por-tema/cuentas-nacionales/cuentas-nacionales-departamentales"),
    "pib": ("PIB departamental de Nariño por ramas 2005-2025pr (base 2015)", "DANE", "https://www.dane.gov.co/index.php/estadisticas-por-tema/cuentas-nacionales/cuentas-nacionales-departamentales"),
    "geih": ("Mercado laboral GEIH: TD, TGP y TO de Pasto A.M. 2007-2025", "DANE", "https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/empleo-y-desempleo"),
    "informal": ("Informalidad laboral GEIH-EISS, Pasto A.M. 2021-2025", "DANE", "https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/empleo-informal-y-seguridad-social"),
    "ipc": ("IPC nacional, variación anual diciembre-diciembre", "DANE", "https://www.dane.gov.co/index.php/estadisticas-por-tema/precios-y-costos/indice-de-precios-al-consumidor-ipc"),
    "pm": ("Pobreza monetaria, extrema y Gini de Nariño 2021-2025", "DANE", "https://www.dane.gov.co/index.php/estadisticas-por-tema/pobreza-y-condiciones-de-vida/pobreza-monetaria"),
    "ipmdep": ("IPM departamental de Nariño 2018-2025 (ECV)", "DANE", "https://www.dane.gov.co/index.php/estadisticas-por-tema/pobreza-y-condiciones-de-vida/pobreza-multidimensional"),
    "hom": ("Homicidios por municipio (víctimas)", "MinDefensa / Policía", "https://www.datos.gov.co/resource/m8fd-ahd9.json"),
    "sec": ("Secuestros por municipio", "MinDefensa", "https://www.datos.gov.co/resource/d7zw-hpf4.json"),
    "vif": ("Violencia intrafamiliar por municipio (denuncias)", "Policía Nacional", "https://www.datos.gov.co/resource/vuyt-mqpw.json"),
    "coca": ("Detección de cultivos de coca por municipio 2001-2024", "MinJusticia / UNODC-SIMCI", "https://www.datos.gov.co/resource/acs4-3wgp.json"),
    "edu": ("Cobertura neta y deserción por municipio 2011-2024", "MinEducación", "https://www.datos.gov.co/resource/nudc-7mev.json"),
    "salud": ("Partos institucionales por municipio 2005-2020", "MinSalud", "https://www.datos.gov.co/resource/4e4i-ua65.json"),
    "mdm": ("Medición del Desempeño Municipal 2016-2020", "DNP", "https://www.datos.gov.co/resource/nkjx-rsq7.json"),
    "idf": ("Índice de Desempeño Fiscal municipal 2005-2022", "DNP", "https://www.dnp.gov.co/LaEntidad_/subdireccion-general-descentralizacion-desarrollo-territorial/direccion-descentralizacion-fortalecimiento-fiscal/Paginas/informacion-fiscal-y-financiera.aspx"),
    "dnp": ("Inversión pagada en proyectos y sector CTeI (MapaInversiones)", "DNP", "https://www.datos.gov.co/resource/wc86-9j4a.json"),
    "idc": ("Índice Departamental de Competitividad (puntaje y puesto)", "Consejo Privado de Competitividad", "https://compite.com.co/indice-departamental-de-competitividad/"),
    "geo": ("Límites municipales MGN 2018 (64 polígonos de Nariño)", "DANE (MGN)", CONFIG["geojson_url"]),
}
ESTADO = {k: "snap" for k in FUENTES_META}
AUDITORIA = []


def registrar(tema, hallazgo, accion, severidad="info"):
    AUDITORIA.append(dict(tema=tema, hallazgo=hallazgo, accion=accion, severidad=severidad))


# -----------------------------------------------------------------------------
# 9. PARSEO DE LA INSTANTÁNEA Y CONSULTAS EN VIVO (SODA · datos.gov.co)
# -----------------------------------------------------------------------------
def parse_wide(clave):
    """Convierte un bloque 'codigo:v1,v2,...' en DataFrame codigo × año (NaN = sin registro)."""
    y0, txt = SNAP[clave]
    filas = {}
    for linea in txt.strip().splitlines():
        cod, vals = linea.split(":")
        filas[cod.strip()] = [float(v) if v.strip() not in ("", "nan") else np.nan for v in vals.split(",")]
    n = max(len(v) for v in filas.values())
    df = pd.DataFrame.from_dict({k: v + [np.nan] * (n - len(v)) for k, v in filas.items()}, orient="index",
                                columns=list(range(y0, y0 + n)))
    df.index.name = "codigo"
    return df.reindex([c for c in CODIGOS if c in df.index] + [c for c in df.index if c not in CODIGOS])


SODA = "https://www.datos.gov.co/resource/{}.json"


def soda(dataset, params, timeout=None):
    r = requests.get(SODA.format(dataset), params=params, timeout=timeout or CONFIG["timeout_api"])
    r.raise_for_status()
    js = r.json()
    if not isinstance(js, list):
        raise ValueError(str(js)[:200])
    return pd.DataFrame(js)


def a_wide(df, col_cod, col_anio, col_val, agg="sum"):
    d = df.copy()
    d["codigo"] = [codigo_municipio(codigo=c) for c in d[col_cod]]
    d["anio"] = pd.to_numeric(d[col_anio], errors="coerce")
    d["valor"] = pd.to_numeric(d[col_val], errors="coerce")
    d = d.dropna(subset=["codigo", "anio", "valor"])
    d["anio"] = d["anio"].astype(int)
    return d.pivot_table(index="codigo", columns="anio", values="valor", aggfunc=agg)


def api_conteos(dataset):
    df = soda(dataset, {"$select": "cod_muni as c, date_extract_y(fecha_hecho) as y, sum(cantidad) as n",
                        "$where": "cod_depto='52'", "$group": "c, y", "$limit": 50000})
    return a_wide(df, "c", "y", "n")


def api_vif():
    df = soda("vuyt-mqpw", {"$select": "codigo_dane, fecha_hecho, cantidad", "$where": "departamento='NARIÑO'",
                            "$limit": 300000}, timeout=60)
    df["y"] = df["fecha_hecho"].astype(str).str.extract(r"(\d{4})")[0]
    df["cantidad"] = pd.to_numeric(df.get("cantidad"), errors="coerce").fillna(1)
    return a_wide(df, "codigo_dane", "y", "cantidad")


def api_coca():
    df = soda("acs4-3wgp", {"$where": "coddepto='52'", "$limit": 500})
    anios = sorted(int(c[1:]) for c in df.columns if c.startswith("_") and c[1:].isdigit())
    df["codigo"] = [codigo_municipio(codigo=c) for c in df["codmpio"]]
    w = df.dropna(subset=["codigo"]).set_index("codigo")[[f"_{a}" for a in anios]].apply(pd.to_numeric, errors="coerce")
    w.columns = anios
    return w.groupby(level=0).sum(min_count=1)


def api_edu():
    df = soda("nudc-7mev", {"$select": "a_o, c_digo_municipio, cobertura_neta, deserci_n",
                            "$where": "c_digo_departamento='52'", "$limit": 5000})
    return {"cob": a_wide(df, "c_digo_municipio", "a_o", "cobertura_neta", "mean"),
            "des": a_wide(df, "c_digo_municipio", "a_o", "deserci_n", "mean")}


UMBRAL_MUNIS = {"hom": 40, "sec": 25, "vif": 40, "coca": 20, "cob": 55, "des": 55}


def validar_y_fusionar(clave_snap, w_api, nombre_fuente, umbral_munis=None):
    """Fusiona la serie en vivo con la instantánea: la API manda donde hay dato; se conserva la instantánea en el resto."""
    base = parse_wide(clave_snap)
    umbral_munis = umbral_munis or UMBRAL_MUNIS.get(clave_snap, 40)
    if w_api is None or w_api.empty or w_api.shape[0] < umbral_munis:
        raise ValueError("respuesta incompleta")
    comunes = [a for a in base.columns if a in w_api.columns]
    if comunes:
        a = max(comunes)
        sb, sa = np.nansum(base[a].values), np.nansum(w_api[a].reindex(base.index).values)
        if sb > 0 and not (0.4 <= sa / sb <= 2.5):
            raise ValueError(f"magnitud inconsistente en {a}: API {sa:,.0f} vs instantánea {sb:,.0f}")
    anios = sorted(set(base.columns) | set(w_api.columns))
    filas = list(base.index) + [c for c in w_api.index if c not in base.index]
    out = base.reindex(index=filas, columns=anios).copy()
    wa = w_api.reindex(index=filas, columns=anios)
    out = wa.combine_first(out)
    return out


def refrescar_en_vivo():
    """Consulta en paralelo las APIs oficiales; si fallan, la instantánea verificada sostiene la plataforma."""
    vivos = {}
    if not CONFIG.get("usar_api", True):
        return vivos
    try:
        requests.get(SODA.format("acs4-3wgp"), params={"$limit": 1}, timeout=8).raise_for_status()
    except Exception as e:
        registrar("Conectividad", f"datos.gov.co no respondió ({type(e).__name__}).",
                  "Se usa la instantánea oficial verificada del " + CONFIG["fecha_instantanea"] + ".", "aviso")
        return vivos
    tareas = {"hom": lambda: api_conteos("m8fd-ahd9"), "sec": lambda: api_conteos("d7zw-hpf4"),
              "vif": api_vif, "coca": api_coca, "edu": api_edu}
    with ThreadPoolExecutor(max_workers=5) as ex:
        fut = {k: ex.submit(f) for k, f in tareas.items()}
        for k, f in fut.items():
            try:
                res = f.result(timeout=90)
                if k == "edu":
                    vivos["cob"] = validar_y_fusionar("cob", res["cob"], "edu")
                    vivos["des"] = validar_y_fusionar("des", res["des"], "edu")
                else:
                    vivos[k] = validar_y_fusionar(k, res, k)
                ESTADO["edu" if k == "edu" else k] = "live"
                print(f"  ✓ {FUENTES_META['edu' if k == 'edu' else k][0]}: API en vivo")
            except Exception as e:
                registrar("Ingesta API", f"{FUENTES_META['edu' if k == 'edu' else k][0]}: {type(e).__name__}: {str(e)[:120]}",
                          "Se conserva la instantánea oficial verificada.", "aviso")
                print(f"  · {k}: instantánea ({type(e).__name__})")
    return vivos


# -----------------------------------------------------------------------------
# 10. CARTOGRAFÍA OFICIAL MGN-DANE Y MATRICES DE PESOS ESPACIALES
# -----------------------------------------------------------------------------
def _features_narino(gj):
    feats = {}
    for f in gj.get("features", []):
        pr = f.get("properties", {}) or {}
        cod = str(pr.get("MPIO_CCNCT") or pr.get("MPIO_CDPMP") or pr.get("c") or f.get("id") or "").strip()
        dpto = str(pr.get("DPTO_CCDGO") or cod[:2]).zfill(2)
        if dpto == "52" and cod in COD_A_MUN:
            area = pr.get("MPIO_NAREA") or pr.get("a")
            feats[cod] = (f["geometry"], float(area) if area else None)
    return feats


def cargar_geometria():
    feats = {}
    try:
        r = requests.get(CONFIG["geojson_url"], timeout=60)
        r.raise_for_status()
        feats = _features_narino(r.json())
        if len(feats) == 64:
            ESTADO["geo"] = "live"
            print("  ✓ GeoJSON MGN-DANE descargado (64 municipios)")
    except Exception as e:
        print(f"  · GeoJSON en línea no disponible ({type(e).__name__}); se usa la geometría oficial embebida")
    if len(feats) != 64:
        gj = json.loads(zlib.decompress(base64.b64decode("".join(GEO_RESPALDO_B64))).decode("utf-8"))
        feats = _features_narino(gj)
        ESTADO["geo"] = "snap"
    geoms, anillos, filas = {}, {}, []
    for cod in CODIGOS:
        g, area = feats[cod]
        shp = shape(g).buffer(0)
        geoms[cod] = shp
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        anillos[cod] = [np.asarray(p[0], float) for p in polys if p and len(p[0]) > 2]
        rp = shp.representative_point()
        area_km2 = area if area else shp.area * (111.32 ** 2)
        filas.append((cod, rp.x, rp.y, shp.centroid.x, shp.centroid.y, area_km2))
    cen = pd.DataFrame(filas, columns=["codigo", "lon_lab", "lat_lab", "lon", "lat", "area_km2"])
    gj_out = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": c, "properties": {"municipio": COD_A_MUN[c]}, "geometry": feats[c][0]} for c in CODIGOS]}
    return geoms, anillos, cen, gj_out


def coords_km(cen):
    lat0 = np.deg2rad(cen.lat.mean())
    return np.column_stack([cen.lon.values * 111.32 * np.cos(lat0), cen.lat.values * 110.57])


def construir_W(tipo, k=4):
    """Matriz binaria de pesos (orden CODIGOS). Contigüidad sobre fronteras reales del MGN."""
    n = len(CODIGOS)
    X = coords_km(CENTROS)
    D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(D, np.inf)
    W = np.zeros((n, n))
    polys = [GEOMS[c] for c in CODIGOS]
    if tipo.startswith("Contigüidad"):
        reina = "Queen" in tipo
        if HAY_PYSAL:
            w = (libpysal.weights.Queen if reina else libpysal.weights.Rook).from_iterable(polys)
            for i, vec in w.neighbors.items():
                W[i, list(vec)] = 1.0
        else:
            for i in range(n):
                for j in range(i + 1, n):
                    inter = polys[i].intersection(polys[j])
                    if (not inter.is_empty) and (reina or inter.length > 0):
                        W[i, j] = W[j, i] = 1.0
    elif tipo.startswith("K vecinos"):
        idx = np.argsort(D, axis=1)[:, :int(k)]
        for i in range(n):
            W[i, idx[i]] = 1.0
    else:
        umbral = np.max(np.min(D, axis=1)) * 1.05
        W = np.where(D <= umbral, 1.0 / D, 0.0)
    np.fill_diagonal(W, 0)
    for i in range(n):
        if W[i].sum() == 0:
            W[i, np.argmin(D[i])] = 1.0
    return W


@functools.lru_cache(maxsize=24)
def matriz_pesos(tipo, k=4):
    return construir_W(tipo, k)


def moran_global(y, W, perms=999, seed=7):
    y = np.asarray(y, float)
    Wr = W / W.sum(1, keepdims=True)
    if HAY_PYSAL:
        w = libpysal.weights.full2W(W, ids=list(range(len(y))))
        w.transform = "r"
        mi = Moran(y, w, permutations=perms)
        np.random.seed(seed)
        ml = Moran_Local(y, w, permutations=perms, seed=seed)
        try:
            gc = Geary(y, w, permutations=perms)
            geary = (gc.C, gc.p_sim)
        except Exception:
            geary = (np.nan, np.nan)
        return dict(I=mi.I, EI=mi.EI, VI=mi.VI_norm, z=mi.z_norm, p_norm=mi.p_norm, p_sim=mi.p_sim, z_sim=mi.z_sim,
                    geary=geary, Ii=ml.Is, q=ml.q, p_loc=ml.p_sim, motor=f"PySAL/esda {libpysal.__version__}")
    n = len(y)
    z = (y - y.mean()) / y.std()
    I = float(z @ Wr @ z / (z @ z))
    rng = np.random.default_rng(seed)
    sims = np.array([(lambda zz: zz @ Wr @ zz / (zz @ zz))(rng.permutation(z)) for _ in range(perms)])
    EI = -1 / (n - 1)
    lag = Wr @ z
    q = np.where((z > 0) & (lag > 0), 1, np.where((z < 0) & (lag > 0), 2, np.where((z < 0) & (lag < 0), 3, 4)))
    Ii = z * lag
    p_loc = np.array([(np.sum(np.abs([z[i] * (Wr[i] @ np.insert(rng.permutation(np.delete(z, i)), i, 0)) for _ in range(199)]) >= abs(Ii[i])) + 1) / 200 for i in range(n)])
    return dict(I=I, EI=EI, VI=sims.var(), z=(I - EI) / sims.std(), p_norm=2 * (1 - sps.norm.cdf(abs((I - EI) / sims.std()))),
                p_sim=(np.sum(np.abs(sims - EI) >= abs(I - EI)) + 1) / (perms + 1), z_sim=(I - sims.mean()) / sims.std(),
                geary=(np.nan, np.nan), Ii=Ii, q=q, p_loc=p_loc, motor="Implementación propia (numpy)")


# -----------------------------------------------------------------------------
# 11. AUDITORÍA DE CALIDAD E IMPUTACIÓN TÉCNICA DOCUMENTADA (PCHIP)
# -----------------------------------------------------------------------------
def detectar_anios_anomalos(w, nombre_serie, umbral=3.0, min_frac=0.4, min_salto=8.0):
    """Detecta años en que la mayoría de municipios se desvía bruscamente del promedio de sus años vecinos."""
    anomalos = []
    cols = list(w.columns)
    dif_tipica = np.nanmedian(np.abs(np.diff(w.values, axis=1)))
    for i in range(1, len(cols) - 1):
        a, b, c = w[cols[i - 1]], w[cols[i]], w[cols[i + 1]]
        # Pico aislado: el año se aleja de AMBOS vecinos en la misma dirección (no confunde rupturas de nivel)
        mismo_signo = np.sign(b - a) == np.sign(b - c)
        dev = pd.concat([(b - a).abs(), (b - c).abs()], axis=1).min(axis=1).where(mismo_signo, 0.0)
        if dev.notna().sum() < 20:
            continue
        frac = (dev > min_salto).mean()
        score = np.nanmedian(dev) / max(dif_tipica, 1e-9)
        if score > umbral and frac > min_frac:
            anomalos.append(cols[i])
            registrar(f"Calidad · {nombre_serie}",
                      f"Año {cols[i]}: {frac:.0%} de los municipios se aparta más de {min_salto:g} unidades del promedio de "
                      f"{cols[i - 1]} y {cols[i + 1]} (puntaje de ruptura {score:.1f}).",
                      "Se trata como dato atípico de fuente y se reemplaza por interpolación PCHIP (marcada como imputación).",
                      "corrección")
    return anomalos


def imputar_pchip(w):
    """Interpolación monótona por tramos (PCHIP) solo en huecos interiores; nunca extrapola."""
    out = w.copy()
    mask = pd.DataFrame(False, index=w.index, columns=w.columns)
    cols = np.array(w.columns, dtype=float)
    for cod in w.index:
        s = w.loc[cod].values.astype(float)
        ok = ~np.isnan(s)
        if ok.sum() >= 3:
            xs = cols[ok]
            hueco = (~ok) & (cols > xs.min()) & (cols < xs.max())
            if hueco.any():
                f = PchipInterpolator(xs, s[ok])
                vals = f(cols[hueco])
                out.loc[cod, w.columns[hueco]] = vals
                mask.loc[cod, w.columns[hueco]] = True
    return out, mask


def deflactor_vab():
    corr = np.array(PIB_DEP[("corr", "VAB")][1])
    const = np.array(PIB_DEP[("const", "VAB")][1])
    return dict(zip(PIB_ANIOS, corr / const))


# -----------------------------------------------------------------------------
# 12. CONSTRUCCIÓN DEL PANEL MUNICIPAL, CORTE CENSAL Y SERIES DEPARTAMENTALES
# -----------------------------------------------------------------------------
def construir_base():
    print("▸ Cargando matriz empírica oficial y refrescando APIs de datos.gov.co…")
    vivos = refrescar_en_vivo()
    W = {k: (vivos[k] if k in vivos else parse_wide(k)) for k in
         ["pob", "hom", "sec", "vif", "coca", "cob", "des", "pi", "mdm", "va_corr",
          "idf_transf", "idf_propios", "idf_inversion", "idf_idf"]}
    imp_flags = {}

    # --- Reglas de calidad detectadas en la auditoría ---
    W["vif"] = W["vif"].drop(columns=[c for c in W["vif"].columns if c < 2011], errors="ignore")
    registrar("Cobertura temporal · VIF", "El registro de 2010 está incompleto (inicio del sistema de reporte).",
              "La serie se analiza desde 2011.", "corrección")
    hoy = datetime.now().year
    for k in ("hom", "sec", "vif"):
        W[k] = W[k].drop(columns=[c for c in W[k].columns if c >= hoy], errors="ignore")
    registrar("Cobertura temporal · seguridad", f"El año {hoy} está en curso.", "Se excluye para no sesgar tasas anuales.", "corrección")
    W["idf_propios"] = W["idf_propios"].drop(columns=[c for c in W["idf_propios"].columns if c < 2010], errors="ignore")
    registrar("Ruptura metodológica · recursos propios (DNP)",
              "Antes de 2010 el indicador se expresa sobre ingresos totales y desde 2010 sobre ingresos corrientes (salto de nivel).",
              "Se usa solo 2010-2022 para no mezclar definiciones.", "corrección")
    ceros = int((W["idf_inversion"] == 0).sum().sum())
    W["idf_inversion"] = W["idf_inversion"].replace(0, np.nan)
    if ceros:
        registrar("Calidad · magnitud de la inversión (DNP)", f"{ceros} registros con valor 0 %, incompatible con la ejecución presupuestal municipal.",
                  "Se tratan como faltantes y se imputan si son huecos interiores.", "corrección")
    sobre100 = int((W["cob"] > 100).sum().sum())
    registrar("Interpretación · cobertura neta (MEN)", f"{sobre100} observaciones superan 100 % por matrícula de estudiantes de otros municipios.",
              "Se conservan (es el dato oficial) y se advierte en la interpretación.", "info")
    registrar("Ruptura de denominador · educación", "Desde 2018 el MEN calcula coberturas con proyecciones del CNPV 2018.",
              "Se documenta; las comparaciones 2017-2018 deben leerse con cautela.", "info")
    for clave, nom in (("cob", "cobertura neta"), ("des", "deserción")):
        for a in detectar_anios_anomalos(W[clave], nom, min_salto=8.0 if clave == "cob" else 2.5):
            W[clave][a] = np.nan
    for clave in ("cob", "des", "pi", "mdm", "idf_transf", "idf_propios", "idf_inversion", "idf_idf"):
        W[clave], imp_flags[clave] = imputar_pchip(W[clave])

    # --- Panel municipio-año ---
    P = pd.MultiIndex.from_product([CODIGOS, ANIOS], names=["codigo", "anio"]).to_frame(index=False)
    P = P.merge(CAT, on="codigo", how="left")

    def largo(w, nombre_col, conteo=False):
        anios_cob = [a for a in w.columns if A0 <= a <= A1]
        x = w.reindex(index=CODIGOS)[anios_cob]
        if conteo:
            x = x.fillna(0.0)
        x = x.copy()
        x.index.name = "codigo"
        s = x.reset_index().melt(id_vars="codigo", var_name="anio", value_name=nombre_col)
        s["anio"] = s["anio"].astype(int)
        return s

    for clave, col, conteo in (("pob", "poblacion", False), ("hom", "homicidios", True), ("sec", "secuestros", True),
                               ("vif", "vif", True), ("coca", "coca_ha", True), ("cob", "cobertura_neta", False),
                               ("des", "desercion", False), ("pi", "partos_inst", False), ("mdm", "mdm", False),
                               ("idf_transf", "dep_transf", False), ("idf_propios", "rec_propios", False),
                               ("idf_inversion", "inversion_pct", False), ("idf_idf", "idf", False), ("va_corr", "va_corr", False)):
        P = P.merge(largo(W[clave], col, conteo), on=["codigo", "anio"], how="left")
    defl = deflactor_vab()
    P["va_real"] = P.va_corr / P.anio.map(defl)
    P["va_pc"] = P.va_real * 1e3 / P.poblacion
    P["tasa_homicidios"] = P.homicidios / P.poblacion * 1e5
    P["tasa_secuestros"] = P.secuestros / P.poblacion * 1e5
    P["tasa_vif"] = P.vif / P.poblacion * 1e5
    P = P.merge(CENTROS[["codigo", "area_km2"]], on="codigo", how="left")
    P["coca_pct"] = P.coca_ha / P.area_km2
    imp_cols = {"cob": "cobertura_neta", "des": "desercion", "pi": "partos_inst", "mdm": "mdm", "idf_transf": "dep_transf",
                "idf_propios": "rec_propios", "idf_inversion": "inversion_pct", "idf_idf": "idf"}
    IMP = {}
    for clave, col in imp_cols.items():
        m = imp_flags[clave].reindex(index=CODIGOS).fillna(False)
        m = m[[a for a in m.columns if A0 <= a <= A1]].copy()
        m.index.name = "codigo"
        m = m.reset_index().melt(id_vars="codigo", var_name="anio", value_name="imp")
        m["anio"] = m["anio"].astype(int)
        m["imp"] = m["imp"].astype(bool)
        IMP[col] = set(map(tuple, m.loc[m.imp, ["codigo", "anio"]].values.tolist()))
        n_imp = len(IMP[col])
        if n_imp:
            registrar(f"Imputación técnica · {nombre(col)}", f"{n_imp} celdas municipio-año eran huecos interiores.",
                      "Interpoladas con PCHIP (monótona, sin extrapolación); quedan marcadas en las tablas.", "imputación")

    # --- Corte transversal censal / estructural ---
    ipm = parse_wide("ipm2018")
    priv = parse_wide("priv2018")
    estr = parse_wide("va_estr2024")
    CS = CAT.copy()
    CS["ipm"] = CS.codigo.map(ipm[2018])
    CS["ipm_urbano"] = CS.codigo.map(ipm[2019])
    CS["ipm_rural"] = CS.codigo.map(ipm[2020])
    CS["brecha_ipm"] = CS.ipm_rural - CS.ipm_urbano
    nom_priv = ["analfabetismo", "bajo_logro", "barr_infancia", "barr_salud", "dependencia", "hacinamiento", "excretas",
                "inasistencia", "paredes", "pisos", "rezago", "sin_agua", "sin_aseg", "trab_infantil", "trab_informal"]
    for i, npv in enumerate(nom_priv):
        CS["priv_" + npv] = CS.codigo.map(priv[2018 + i])
    CS["sh_primario"] = CS.codigo.map(estr[2024] / estr[2027] * 100)
    CS["sh_terciario"] = CS.codigo.map(estr[2026] / estr[2027] * 100)
    CS = CS.merge(CENTROS, on="codigo", how="left")

    # --- Departamento ---
    D = pd.DataFrame({"anio": ANIOS})
    pib_c = dict(zip(PIB_ANIOS, PIB_DEP[("const", "PIB")][1]))
    pib_n = dict(zip(PIB_ANIOS, PIB_DEP[("corr", "PIB")][1]))
    D["pib"] = D.anio.map(pib_c)
    D["pib_corriente"] = D.anio.map(pib_n)
    D["crecimiento_pib"] = D.pib.pct_change() * 100
    pob_dep = P.groupby("anio").poblacion.sum()
    D["poblacion"] = D.anio.map(pob_dep)
    D["pib_pc"] = D.pib * 1e3 / D.poblacion
    for i, col in enumerate(["desempleo", "tgp", "to"]):
        D[col] = D.anio.map({a: v[i] for a, v in GEIH_PASTO.items()})
    D["informalidad"] = D.anio.map(INFORMALIDAD_PASTO)
    D["inflacion"] = D.anio.map(IPC_NACIONAL)
    for col, serie in POBREZA_MON.items():
        D[col] = D.anio.map(serie)
    D["ipm_dep"] = D.anio.map({a: v[0] for a, v in IPM_DEP.items()})
    g = P.groupby("anio")
    hom_cov = [a for a in W["hom"].columns if A0 <= a <= A1]
    D["tasa_homicidios_dep"] = np.where(D.anio.isin(hom_cov), D.anio.map(g.homicidios.sum()) / D.poblacion * 1e5, np.nan)
    sec_cov = [a for a in W["sec"].columns if A0 <= a <= A1]
    D["secuestros_dep"] = np.where(D.anio.isin(sec_cov), D.anio.map(g.secuestros.sum()), np.nan)
    coca_cov = [a for a in W["coca"].columns if A0 <= a <= A1]
    D["coca_dep"] = np.where(D.anio.isin(coca_cov), D.anio.map(g.coca_ha.sum()), np.nan)
    def _prom_pond(d, col, min_cob=0.9):
        ok = d[col].notna()
        if d.loc[ok, "poblacion"].sum() < min_cob * d.poblacion.sum():
            return np.nan
        return np.average(d.loc[ok, col], weights=d.loc[ok, "poblacion"])

    D["cobertura_dep"] = D.anio.map(g.apply(lambda d: _prom_pond(d, "cobertura_neta")))
    D["idf_mediana"] = D.anio.map(g.idf.median())
    D["dep_transf_dep"] = D.anio.map(g.dep_transf.median())
    D["recursos_dnp"] = D.anio.map(RECURSOS_DNP)
    D["ctei"] = D.anio.map(CTEI_DNP)
    SECT = pd.DataFrame([dict(anio=a, codigo=cod, actividad=nom, valor=vals[PIB_ANIOS.index(a)])
                         for (tipo, cod), (nom, vals) in PIB_DEP.items()
                         if tipo == "const" and cod not in ("VAB", "IMP", "PIB") for a in PIB_ANIOS])
    return P, CS, D, SECT, IMP


print("▸ Cargando cartografía oficial MGN-DANE…")
GEOMS, ANILLOS, CENTROS, GEOJSON = cargar_geometria()
PANEL, CS, DEPTO, SECT, IMPUTADOS = construir_base()
CAT = CAT.merge(CENTROS, on="codigo", how="left")
N_LIVE = sum(1 for v in ESTADO.values() if v == "live")
for _k in ("pob", "ipm2018", "va", "pib", "geih", "informal", "ipc", "pm", "ipmdep", "salud", "mdm", "idf", "dnp", "idc"):
    ESTADO.setdefault(_k, "snap")
registrar("Corte censal · IPM municipal", "El DANE publica IPM municipal solo para el Censo 2018; no existe serie anual oficial por municipio.",
          "Se usa como corte transversal (no se anualiza: hacerlo sería fabricar datos). La serie anual es la departamental (ECV 2018-2025).", "info")
registrar("Cobertura · inflación", "No hay serie anual descargable del IPC de Pasto en los anexos vigentes del DANE.",
          "Se usa el IPC nacional y se rotula como tal.", "info")
registrar("Cobertura · mercado laboral", "La GEIH publica tasas anuales robustas para Pasto A.M., no para el agregado de Nariño en la serie larga.",
          "Se reporta Pasto A.M. como referente urbano del departamento.", "info")
print(f"▸ Base lista: {len(PANEL):,} obs. municipio-año · {PANEL.codigo.nunique()} municipios · fuentes en vivo: {N_LIVE}")


def es_live(clave):
    return ESTADO.get(clave) == "live"


CLAVE_FUENTE = {"tasa_homicidios": "hom", "tasa_secuestros": "sec", "tasa_vif": "vif", "coca_ha": "coca", "coca_pct": "coca",
                "cobertura_neta": "edu", "desercion": "edu", "partos_inst": "salud", "mdm": "mdm", "dep_transf": "idf",
                "rec_propios": "idf", "inversion_pct": "idf", "idf": "idf", "va_pc": "va", "sh_primario": "va",
                "pib": "pib", "crecimiento_pib": "pib", "pib_pc": "pib", "desempleo": "geih", "tgp": "geih", "to": "geih",
                "informalidad": "informal", "inflacion": "ipc", "pobreza_monetaria": "pm", "pobreza_extrema": "pm", "gini": "pm",
                "ipm_dep": "ipmdep", "tasa_homicidios_dep": "hom", "secuestros_dep": "sec", "coca_dep": "coca",
                "cobertura_dep": "edu", "idf_mediana": "idf", "dep_transf_dep": "idf", "recursos_dnp": "dnp", "ctei": "dnp"}


def etiqueta_fuente(k):
    clave = CLAVE_FUENTE.get(k, "ipm2018" if k in IND_MUN_CENSAL else "pob")
    vivo = es_live(clave)
    txt = "API en vivo" if vivo else f"Instantánea oficial {CONFIG['fecha_instantanea']}"
    return f'<span class="src {"live" if vivo else "snap"}">● {txt}</span> · <span class="cita">{META.get(k, {}).get("fuente", "")}</span>'




# -----------------------------------------------------------------------------
# 13. UTILIDADES DE ACCESO A DATOS, TABLAS Y COMPONENTES HTML
# -----------------------------------------------------------------------------
def municipios_sel(subs, muns):
    subs = [s for s in (subs or []) if s in SUBREGIONES]
    muns = [m for m in (muns or []) if m in MUN_A_COD]
    if muns:
        return muns
    if subs:
        return CAT[CAT.subregion.isin(subs)].municipio.tolist()
    return CAT.municipio.tolist()


def rango(a0, a1):
    a0 = int(a0) if a0 not in (None, "") else A0
    a1 = int(a1) if a1 not in (None, "") else A1
    return (min(a0, a1), max(a0, a1))


@functools.lru_cache(maxsize=128)
def anios_disp(k):
    if META[k]["corte"] == "censal":
        return (2024,) if k == "sh_primario" else (2018,)
    n = PANEL.groupby("anio")[k].apply(lambda x: x.notna().sum())
    return tuple(int(a) for a, v in n.items() if v >= 32)


def anio_valido(k, anio):
    disp = anios_disp(k)
    if not disp:
        return None
    return min(disp, key=lambda a: (abs(a - int(anio)), -a))


def corte(anio, cols):
    """Valores municipio a municipio en un año (las variables censales salen del corte oficial)."""
    base = CAT[["codigo", "municipio", "subregion", "zona"]].copy()
    anuales = [c for c in cols if META.get(c, {}).get("corte") != "censal"]
    censales = [c for c in cols if META.get(c, {}).get("corte") == "censal"]
    if anuales:
        base = base.merge(PANEL.loc[PANEL.anio == int(anio), ["codigo"] + anuales], on="codigo", how="left")
    if censales:
        base = base.merge(CS[["codigo"] + censales], on="codigo", how="left")
    return base


def corte_transversal(a0, a1, cols):
    """Promedio municipal del periodo para variables anuales; corte oficial para las censales."""
    base = CAT[["codigo", "municipio", "subregion", "zona"]].copy()
    anuales = [c for c in cols if META.get(c, {}).get("corte") != "censal"]
    censales = [c for c in cols if META.get(c, {}).get("corte") == "censal"]
    if anuales:
        d = PANEL[(PANEL.anio >= a0) & (PANEL.anio <= a1)].groupby("codigo")[anuales].mean().reset_index()
        base = base.merge(d, on="codigo", how="left")
    if censales:
        base = base.merge(CS[["codigo"] + censales], on="codigo", how="left")
    return base


def es_imputado(col, codigo, anio):
    return (codigo, int(anio)) in IMPUTADOS.get(col, set())


def tabla_html(df, num_cols=None, max_rows=200, decs=None):
    num_cols = num_cols or [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    decs = decs or {}
    th = "".join(f"<th>{c}</th>" for c in df.columns)
    filas = []
    for _, r in df.head(max_rows).iterrows():
        tds = []
        for c in df.columns:
            v = r[c]
            if c in num_cols and isinstance(v, (int, float, np.integer, np.floating)):
                tds.append(f'<td class="num">{fnum(v, decs.get(c, 3 if abs(v) < 10 else 2))}</td>')
            else:
                tds.append(f"<td>{v}</td>")
        filas.append("<tr>" + "".join(tds) + "</tr>")
    return f'<div class="tbl-wrap"><table class="tbl"><thead><tr>{th}</tr></thead><tbody>{"".join(filas)}</tbody></table></div>'


def callout(titulo, cuerpo, tono="info", icono="🧭"):
    return f'<div class="callout {tono}"><h4>{icono} {titulo}</h4>{cuerpo}</div>'


def intro(icono, titulo, texto, metodos):
    chips = "".join(f"<span>{m}</span>" for m in metodos)
    return (f'<div class="obs-intro"><div class="ico">{icono}</div><div><h3>{titulo}</h3>'
            f'<p>{texto}</p><div class="met">{chips}</div></div></div>')


def mono(txt):
    return f'<div class="mono">{str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")}</div>'


def p_estrellas(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def error_html(e):
    return callout("No fue posible completar el cálculo con esta selección",
                   f"<p>Ajusta los filtros o variables e inténtalo de nuevo. Detalle técnico: <code>{type(e).__name__}: {str(e)[:220]}</code></p>",
                   "warn", "⚠️")


def blindado(salidas):
    """Protege cada módulo: ante cualquier error devuelve componentes válidos (nunca una pantalla rota)."""
    def deco(fn):
        @functools.wraps(fn)
        def envoltura(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                print(f"[{fn.__name__}] {type(e).__name__}: {e}")
                out = []
                for s in salidas:
                    out.append(error_html(e) if s == "html" else fig_vacia("No disponible para esta selección")
                               if s == "fig" else None)
                return tuple(out) if len(out) > 1 else out[0]
        return envoltura
    return deco


def orientar(valores, k):
    s = META.get(k, {}).get("sentido", 1) or 1
    return np.asarray(valores, float) * s


def percentil_orientado(serie, k):
    return pd.Series(orientar(serie, k)).rank(pct=True).values * 100


def escala_de(k):
    s = META.get(k, {}).get("sentido", 0)
    return ESCALA_VERDE if s == 1 else ESCALA_ROJA if s == -1 else ESCALA_AZUL


def nota_anio(k, pedido, usado):
    if pedido is None or usado is None or int(pedido) == int(usado):
        return ""
    if META[k]["corte"] == "censal":
        return f"<p class='nota-fuente'>ℹ️ {nombre(k)} es un corte oficial único ({usado}); el año seleccionado no aplica.</p>"
    return f"<p class='nota-fuente'>ℹ️ {nombre(k)} no tiene dato para {pedido}; se muestra el año disponible más cercano ({usado}).</p>"


# -----------------------------------------------------------------------------
# 13b. SELECCIÓN TERRITORIAL DEL PANEL (perfil, posiciones y lectura por municipio)
# -----------------------------------------------------------------------------
SUMABLES = {"poblacion", "coca_ha"}
PERFIL = ["poblacion", "va_pc", "ipm", "tasa_homicidios", "tasa_vif", "coca_ha", "cobertura_neta", "desercion",
          "partos_inst", "idf", "dep_transf", "rec_propios", "mdm"]
MAX_DETALLE = 8


def hay_seleccion(sel):
    return 0 < len(sel) < len(CAT)


def desc_seleccion(subs, muns):
    """Texto corto que describe la selección del panel."""
    sel = municipios_sel(subs, muns)
    if not hay_seleccion(sel):
        return sel, "Todo Nariño (64 municipios)"
    if len(sel) == 1:
        return sel, f"{sel[0]} ({MUN_A_SUB[sel[0]]})"
    subs_v = [x for x in (subs or []) if x in SUBREGIONES]
    if not [m for m in (muns or []) if m in MUN_A_COD] and subs_v:
        return sel, f"{'Subregión' if len(subs_v) == 1 else 'Subregiones'} {', '.join(subs_v)} · {len(sel)} municipios"
    return sel, f"{len(sel)} municipios: {', '.join(sel[:6])}{'…' if len(sel) > 6 else ''}"


def valores_anio(k, anio):
    """Serie municipio → valor de k en el año dado (censales: corte oficial)."""
    return corte(anio, [k]).set_index("municipio")[k]


def valor_seleccion(sel, k, anio):
    """Valor agregado de la selección: suma (población, hectáreas) o promedio ponderado por población."""
    v = valores_anio(k, anio).reindex(sel)
    if k in SUMABLES:
        return float(v.sum()) if v.notna().any() else np.nan
    w = PANEL[PANEL.anio == min(int(anio), int(PANEL.anio.max()))].set_index("municipio").poblacion.reindex(sel)
    ok = v.notna() & w.notna()
    if not ok.any():
        return float(v.mean()) if v.notna().any() else np.nan
    return float(np.average(v[ok], weights=w[ok]))


def puesto_de(k, anio, mm):
    """Posición del municipio entre los 64 (1 = mejor situación según el sentido normativo)."""
    v = valores_anio(k, anio).dropna()
    if mm not in v.index:
        return None, len(v)
    s = META[k]["sentido"]
    rk = v.rank(ascending=(s == -1), method="min")
    return int(rk[mm]), len(v)


def puesto_txt(k, anio, mm):
    r, n = puesto_de(k, anio, mm)
    if r is None:
        return "sin dato"
    ref = "1 = mejor situación" if META[k]["sentido"] != 0 else "1 = valor más alto"
    return f"puesto {r} de {n} ({ref})"


def lectura_vs_mediana(k, valor, mediana):
    s = META[k]["sentido"]
    if not (np.isfinite(valor) and np.isfinite(mediana)) or s == 0 or valor == mediana:
        return '<span class="sem neutro">—</span>'
    mejor = (valor - mediana) * s > 0
    return '<span class="sem ok">▲ mejor que la mediana</span>' if mejor else '<span class="sem mal">▼ peor que la mediana</span>'


def bloque_sel(titulo, items):
    """Recuadro destacado con la lectura de la selección del panel dentro de un callout."""
    if not items:
        return ""
    return f'<div class="sel-box"><h5>📍 {titulo}</h5><ul>{"".join(f"<li>{x}</li>" for x in items)}</ul></div>'


def estado_filtros(subs, muns, a0, a1, pendiente=False):
    if pendiente:
        return ('<div class="estado-filtros pend">● Cambios sin aplicar<br><span>Pulse «Aplicar filtros» para actualizar las pestañas</span></div>')
    _, etq = desc_seleccion(subs, muns)
    a0, a1 = rango(a0, a1)
    return f'<div class="estado-filtros ok">✓ Mostrando<br><span>{etq} · {a0}–{a1}</span></div>'


def html_perfil(subs, muns, a0, a1):
    """Ficha del territorio elegido en el panel (pestaña Inicio)."""
    a0, a1 = rango(a0, a1)
    sel, etq = desc_seleccion(subs, muns)
    if not hay_seleccion(sel):
        return ('<div class="perfil-vacio">📍 <b>Perfil del territorio seleccionado.</b> Las tarjetas y gráficos de esta pestaña describen a todo '
                'el departamento. Elija una subregión o uno o varios municipios en el <b>Panel de control territorial</b> y pulse '
                '<b>«Aplicar filtros»</b> para ver aquí su ficha comparada con la mediana de Nariño; el resto de pestañas también lo destacará.</div>')
    filas = []
    for k in PERFIL:
        anio = anio_valido(k, a1)
        if anio is None:
            continue
        v = valor_seleccion(sel, k, anio)
        if not np.isfinite(v):
            continue
        todos = valores_anio(k, anio)
        med = float(todos.median())
        pos = puesto_txt(k, anio, sel[0]).replace("puesto ", "") if len(sel) == 1 and k != "poblacion" else "—"
        ref = fmt_val(todos.sum(), k) + " (total)" if k in SUMABLES else fmt_val(med, k)
        lect = lectura_vs_mediana(k, v, med) if k not in SUMABLES else '<span class="sem neutro">—</span>'
        filas.append(f"<tr><td>{nombre(k)}<div class='u'>{META[k]['unidad']}</div></td><td class='num'>{anio}</td>"
                     f"<td class='num'><b>{fmt_val(v, k)}</b></td><td class='num'>{ref}</td><td>{pos}</td><td>{lect}</td></tr>")
    pob = valor_seleccion(sel, "poblacion", anio_valido("poblacion", a1))
    subs_sel = sorted({MUN_A_SUB[m] for m in sel}, key=SUBREGIONES.index)
    nota = ("Valores del municipio." if len(sel) == 1 else
            "Selección de varios municipios: tasas y porcentajes ponderados por población; población y hectáreas de coca suman.")
    return (f'<div class="perfil"><div class="perfil-cab"><div><div class="eyebrow">Perfil del territorio seleccionado</div>'
            f'<h3>{etq}</h3><p>{"Subregión" if len(subs_sel) == 1 else "Subregiones"}: {", ".join(subs_sel)} · Población: <b>{fnum(pob, 0)}</b> habitantes · '
            f'Periodo del panel: {a0}–{a1} (se usa el año disponible más cercano a {a1})</p></div></div>'
            f'<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Indicador</th><th>Año</th><th>Selección</th><th>Nariño (mediana municipal)</th>'
            f'<th>Posición entre 64</th><th>Lectura</th></tr></thead><tbody>{"".join(filas)}</tbody></table></div>'
            f'<p class="nota-fuente">{nota} Posición: 1 = mejor situación según el sentido de cada indicador. Fuentes: DANE, DNP, MinDefensa, MinEducación, MinSalud, SIMCI.</p></div>')


# -----------------------------------------------------------------------------
# 14. CARTOGRAFÍA TEMÁTICA (polígonos oficiales MGN, render vectorial autónomo)
# -----------------------------------------------------------------------------
def mapa_municipal(valores, titulo, colorscale=None, textos=None, discreto=None, resaltar=None, cbar_title="", alto=540):
    """valores en el orden de CODIGOS. Dibuja los polígonos oficiales como capas vectoriales (no requiere mapa base)."""
    hover = list(textos) if textos is not None else [COD_A_MUN[c] for c in CODIGOS]
    f = go.Figure()
    if discreto is not None:
        cats, colores = discreto
        colores_mun = [colores.get(v, "#cbd5e1") for v in valores]
    else:
        v = np.asarray(valores, float)
        ok = np.isfinite(v)
        vmin, vmax = (np.nanmin(v[ok]), np.nanmax(v[ok])) if ok.any() else (0, 1)
        norm = np.where(ok, (v - vmin) / (vmax - vmin) if vmax > vmin else 0.5, np.nan)
        colores_mun = [sample_colorscale(colorscale, [float(x)])[0] if np.isfinite(x) else "#e2e8f0" for x in norm]
    for i, cod in enumerate(CODIGOS):
        for anillo in ANILLOS.get(cod, []):
            f.add_trace(go.Scatter(x=anillo[:, 0], y=anillo[:, 1], mode="lines", fill="toself", fillcolor=colores_mun[i],
                                   line=dict(color="white", width=0.8), hoveron="fills", hoverinfo="text", text=hover[i],
                                   showlegend=False))
    cen = CAT.set_index("codigo").loc[CODIGOS]
    f.add_trace(go.Scatter(x=cen.lon_lab, y=cen.lat_lab, mode="markers", marker=dict(size=4, color="#0f172a", opacity=0.45),
                           text=hover, hovertemplate="%{text}<extra></extra>", showlegend=False))
    if discreto is not None:
        for c_ in cats:
            if any(v == c_ for v in valores):
                f.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=12, symbol="square", color=colores[c_]),
                                       name=str(c_), showlegend=True))
    else:
        f.add_trace(go.Scatter(x=[None], y=[None], mode="markers", showlegend=False, hoverinfo="skip",
                               marker=dict(colorscale=colorscale, cmin=vmin, cmax=vmax, color=[vmin], showscale=True,
                                           colorbar=dict(title=dict(text=cbar_title, side="right"), thickness=12, len=0.75,
                                                         tickformat=",.3~g", separatethousands=True))))
    if resaltar:
        dd = cen[cen.municipio.isin(resaltar)]
        f.add_trace(go.Scatter(x=dd.lon_lab, y=dd.lat_lab, mode="markers+text", text=dd.municipio, textposition="top center",
                               textfont=dict(size=10, color=C["navy"]), marker=dict(size=7, color=C["navy"], line=dict(color="white", width=1.5)),
                               hoverinfo="skip", showlegend=False))
    lon0, lon1 = min(a[:, 0].min() for v in ANILLOS.values() for a in v), max(a[:, 0].max() for v in ANILLOS.values() for a in v)
    lat0, lat1 = min(a[:, 1].min() for v in ANILLOS.values() for a in v), max(a[:, 1].max() for v in ANILLOS.values() for a in v)
    f.add_annotation(x=0.02, y=0.98, xref="paper", yref="paper", text="▲ N", showarrow=False, font=dict(size=12, color="#64748b"))
    f.add_annotation(x=0.02, y=0.02, xref="paper", yref="paper", text="Límites: MGN-DANE", showarrow=False, font=dict(size=9.5, color="#94a3b8"))
    f.update_xaxes(visible=False, range=[lon0 - 0.05, lon1 + 0.05])
    f.update_yaxes(visible=False, scaleanchor="x", scaleratio=1, range=[lat0 - 0.05, lat1 + 0.05])
    f.update_layout(title=titulo, height=alto, margin=dict(l=10, r=10, t=60, b=10), plot_bgcolor="#f8fafc", hovermode="closest",
                    legend=dict(orientation="h", y=-0.01, x=0, yanchor="top", xanchor="left", font=dict(size=10.5)))
    if discreto is not None:
        f.update_layout(height=alto + 40, margin=dict(l=10, r=10, t=60, b=90))
    return f


# -----------------------------------------------------------------------------
# 15. PESTAÑA 1 · BIENVENIDA, PULSO TERRITORIAL Y GUÍA
# -----------------------------------------------------------------------------
INSIGNIA_SVG = """
<svg width="104" height="120" viewBox="0 0 104 120" xmlns="http://www.w3.org/2000/svg" aria-label="Insignia territorial de Nariño">
  <defs>
    <linearGradient id="gEsc" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1d4ed8"/><stop offset="1" stop-color="#0f172a"/></linearGradient>
    <linearGradient id="gMar" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0ea5e9"/><stop offset="1" stop-color="#2563eb"/></linearGradient>
    <clipPath id="cEsc"><path d="M52 4 L96 18 V58 C96 86 76 104 52 116 C28 104 8 86 8 58 V18 Z"/></clipPath>
  </defs>
  <path d="M52 4 L96 18 V58 C96 86 76 104 52 116 C28 104 8 86 8 58 V18 Z" fill="url(#gEsc)" stroke="#fbbf24" stroke-width="3"/>
  <g clip-path="url(#cEsc)">
    <circle cx="70" cy="36" r="9" fill="#fbbf24" opacity=".95"/>
    <path d="M8 78 L34 44 L44 54 L56 34 L78 64 L96 54 V120 H8 Z" fill="#15803d"/>
    <path d="M50 38 L56 34 L62 42 Z" fill="#f8fafc" opacity=".9"/>
    <path d="M8 84 Q20 78 32 84 T56 84 T80 84 T104 84 V120 H8 Z" fill="url(#gMar)" opacity=".95"/>
    <path d="M8 94 Q20 88 32 94 T56 94 T80 94 T104 94" stroke="#bae6fd" stroke-width="2" fill="none" opacity=".8"/>
  </g>
  <text x="52" y="30" text-anchor="middle" font-family="Inter,Arial" font-weight="800" font-size="13" fill="#fff" letter-spacing="1">N</text>
</svg>"""


def html_topbar():
    pill = (f'<span class="obs-pill on"><i></i>{N_LIVE} fuente(s) en vivo · resto: instantánea oficial {CONFIG["fecha_instantanea"]}</span>'
            if N_LIVE else f'<span class="obs-pill off"><i></i>Sin conexión a APIs · instantánea oficial verificada {CONFIG["fecha_instantanea"]}</span>')
    return (f'<div class="obs-topbar"><div class="marca"><b>Observatorio Económico y Social de Nariño</b>'
            f'<span>Plataforma Territorial de Inteligencia Económica · 13 subregiones · 64 municipios · datos oficiales</span></div>{pill}</div>')


def html_hero():
    chips = "".join(f'<span class="obs-chip">{s}</span>' for s in
                    ["DANE", "DNP", "MinDefensa · Policía", "UNODC · SIMCI", "MinEducación", "MinSalud", "MGN-DANE"])
    return f"""
<div class="obs-hero"><div class="fila">{INSIGNIA_SVG}
<div style="flex:1;min-width:280px">
  <div class="eyebrow">Gobernanza basada en evidencia · Departamento de Nariño</div>
  <h1>Observatorio Económico y Social de Nariño</h1>
  <h2>Plataforma Territorial de Inteligencia Económica y Simulación de Políticas</h2>
  <div class="lema">«Del dato al territorio: evidencia para cerrar brechas entre la capital, la cordillera, la frontera sur y el litoral pacífico.»
  Explore nueve dimensiones del desarrollo con cifras oficiales, compare municipios, identifique patrones espaciales y simule decisiones fiscales.</div>
</div></div>
<div class="obs-ribbon">{chips}<span class="obs-chip">Cobertura {A0}–{A1}</span><span class="obs-chip">Actualizado {datetime.now():%d/%m/%Y}</span></div>
</div>"""


def sparkline(vals, color):
    v = np.asarray([x for x in vals if x is not None and np.isfinite(x)], float)
    if len(v) < 2:
        return ""
    w, h = 110, 30
    x = np.linspace(2, w - 2, len(v))
    rng_ = v.max() - v.min() or 1
    y = h - 3 - (v - v.min()) / rng_ * (h - 6)
    pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in zip(x, y))
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"><polyline points="{pts}" fill="none" stroke="{color}" '
            f'stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/><circle cx="{x[-1]:.1f}" cy="{y[-1]:.1f}" r="2.8" fill="{color}"/></svg>')


def serie_dep(k):
    d = DEPTO[["anio", k]].dropna()
    return d.anio.values.astype(int), d[k].values.astype(float)


def tono_delta(delta, k, umbral=0.0):
    s = META[k]["sentido"]
    if not np.isfinite(delta) or abs(delta) <= umbral:
        return "warn"
    return "ok" if delta * s > 0 else "alert"


def kpi_card(k, icono, valor_fmt, delta_txt, tono, sub, color, titulo=None):
    _, v = serie_dep(k)
    return f"""<div class="kpi-card"><div class="kpi-top"><div class="kpi-label">{titulo or nombre(k)}</div><div class="kpi-ico">{icono}</div></div>
<div class="kpi-value">{valor_fmt}</div><div class="kpi-sub">{sub}</div>
<div class="kpi-foot"><span class="badge {tono}">{delta_txt}</span>{sparkline(v[-12:], color)}</div>
<div>{etiqueta_fuente(k).split(' · ')[0]}</div></div>"""


def html_kpis():
    t = []
    a, v = serie_dep("pib")
    g = (v[-1] / v[-2] - 1) * 100
    t.append(kpi_card("pib", "🏛️", f"$ {fnum(v[-1] / 1000, 1)} billones", f"{'▲' if g >= 0 else '▼'} {fnum(g, 1)} % real",
                      "alert" if g < 0 else ("warn" if g < 1.5 else "ok"), f"PIB real (pesos de 2015) · {a[-1]}pr", C["azul"], "PIB departamental"))
    a, v = serie_dep("desempleo")
    d = v[-1] - v[-2]
    t.append(kpi_card("desempleo", "👷", f"{fnum(v[-1], 1)} %", f"{'▲' if d >= 0 else '▼'} {fnum(abs(d), 1)} p.p.",
                      tono_delta(d, "desempleo", 0.2), f"Pasto A.M. · {a[-1]} vs {a[-2]}", C["ambar"], "Tasa de desempleo"))
    a, v = serie_dep("ipm_dep")
    d = v[-1] - v[-2]
    t.append(kpi_card("ipm_dep", "🏠", f"{fnum(v[-1], 1)} %", f"{'▲' if d >= 0 else '▼'} {fnum(abs(d), 1)} p.p.",
                      tono_delta(d, "ipm_dep", 0.1), f"Pobreza multidimensional · {a[-1]}", C["rojo"], "IPM departamental"))
    a, v = serie_dep("coca_dep")
    d = (v[-1] / v[-2] - 1) * 100
    t.append(kpi_card("coca_dep", "🌿", f"{fnum(v[-1], 0)} ha", f"{'▲' if d >= 0 else '▼'} {fnum(abs(d), 1)} % anual",
                      tono_delta(d, "coca_dep", 1.0), f"Área detectada (SIMCI) · {a[-1]}", "#15803d", "Cultivos de coca"))
    a, v = serie_dep("tasa_homicidios_dep")
    d = (v[-1] / v[-2] - 1) * 100
    t.append(kpi_card("tasa_homicidios_dep", "🛡️", f"{fnum(v[-1], 1)}", f"{'▲' if d >= 0 else '▼'} {fnum(abs(d), 1)} % anual",
                      tono_delta(d, "tasa_homicidios_dep", 1.0), f"Homicidios por 100.000 hab. · {a[-1]}", C["navy"], "Tasa de homicidios"))
    a, v = serie_dep("pobreza_monetaria")
    d = v[-1] - v[-2]
    _, gv = serie_dep("gini")
    t.append(kpi_card("pobreza_monetaria", "⚖️", f"{fnum(v[-1], 1)} %", f"{'▲' if d >= 0 else '▼'} {fnum(abs(d), 1)} p.p.",
                      tono_delta(d, "pobreza_monetaria", 0.2), f"Gini {fnum(gv[-1], 3)} · {a[-1]}", "#7c3aed", "Pobreza monetaria"))
    return f'<div class="kpi-grid">{"".join(t)}</div>'


def html_guia():
    pasos = [
        ("Elija su territorio", "En el <b>Panel de control</b> seleccione subregiones; la lista de municipios se ajusta en cascada.", "Panel de control"),
        ("Defina el periodo", "Ajuste los años. Si un indicador no tiene dato en ese año, la app usa el más cercano y lo avisa.", "Panel de control"),
        ("Compare y ubique", "La Radiografía ordena municipios y mide brechas; el módulo Espacial dice si los problemas se agrupan en el mapa.", "Pestañas 2 y 3"),
        ("Descubra patrones", "Las tipologías agrupan municipios parecidos y el índice sintético resume muchas variables en una sola.", "Pestañas 4 y 5"),
        ("Simule decisiones", "Mueva los controles fiscales y compare el escenario con la línea base hasta 2030, con bandas de incertidumbre.", "Pestaña 9"),
        ("Lea el diagnóstico", "Cada módulo trae un recuadro en lenguaje claro y una <b>Vista técnica</b> con las pruebas formales.", "Todas"),
    ]
    cards = "".join(f'<div class="guide-card"><div class="num">{i}</div><h5>{t}</h5><p>{d}</p><span class="tab">{tab}</span></div>'
                    for i, (t, d, tab) in enumerate(pasos, 1))
    return (f'<div class="obs-section-title">¿Cómo explorar este Observatorio?</div>'
            f'<div class="obs-section-sub">Seis pasos para pasar de la consulta a la decisión pública.</div><div class="guide-grid">{cards}</div>')


def html_fuentes():
    filas = []
    for k, (desc, ent, url) in FUENTES_META.items():
        est = ESTADO.get(k, "snap")
        b = ('<span class="badge live">API / descarga en vivo</span>' if est == "live"
             else f'<span class="badge snap">Instantánea oficial {CONFIG["fecha_instantanea"]}</span>')
        filas.append(f'<tr><td>{desc}</td><td>{ent}</td><td>{b}</td><td class="cita"><a href="{url}" target="_blank">{url[:70]}{"…" if len(url) > 70 else ""}</a></td></tr>')
    nota = ("Cuando hay conexión, las series de datos.gov.co se actualizan en vivo; si un servidor "
            "no responde, se usa la instantánea verificada embebida (mismas fuentes, transcritas el " + CONFIG["fecha_instantanea"] + ").")
    return (f'<div class="obs-section-title">Trazabilidad de fuentes</div><div class="obs-section-sub">{nota}</div>'
            f'<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Serie</th><th>Entidad</th><th>Estado</th><th>Origen</th></tr></thead>'
            f'<tbody>{"".join(filas)}</tbody></table></div>')


def html_auditoria():
    badge = {"corrección": "alert", "imputación": "imp", "aviso": "warn", "info": "neutral"}
    filas = "".join(f'<tr><td><span class="badge {badge.get(a["severidad"], "neutral")}">{a["severidad"]}</span></td>'
                    f'<td><b>{a["tema"]}</b></td><td>{a["hallazgo"]}</td><td>{a["accion"]}</td></tr>' for a in AUDITORIA)
    return (f'<div class="obs-section-title">Bitácora de auditoría de datos</div>'
            f'<div class="obs-section-sub">Revisión automática de calidad ejecutada al iniciar: rupturas, valores imposibles, coberturas e imputaciones.</div>'
            f'<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Tipo</th><th>Tema</th><th>Hallazgo</th><th>Tratamiento</th></tr></thead>'
            f'<tbody>{filas}</tbody></table></div>')


def html_ficha():
    autores = "<br>".join(CREDITOS["autores"])
    return f"""<div class="obs-section-title">Ficha técnica y créditos de autoría</div>
<div class="ficha"><div><h4>Ficha técnica</h4><dl>
<dt>Producto</dt><dd>Observatorio Económico y Social de Nariño – Plataforma Territorial de Inteligencia Económica y Simulación de Políticas (v2.0 auditada)</dd>
<dt>Cobertura</dt><dd>Departamento de Nariño: 13 subregiones, 64 municipios · {A0}–{A1} según disponibilidad oficial de cada serie</dd>
<dt>Dimensiones</dt><dd>Equidad · Mercado laboral · Precios · Seguridad · Economías ilícitas · Cuentas económicas · Finanzas públicas · CTeI · Desarrollo social</dd>
<dt>Métodos</dt><dd>EDA; Moran I, Geary C y LISA con contigüidad real; K-Means, Ward y DBSCAN; PCA; MCO, Ridge, Lasso, ElasticNet, SVR y Random Forest; ADF, Johansen, VAR/VECM, IRF y FEVD; ARIMA/ETS; panel de efectos fijos; XAI</dd>
<dt>Cartografía</dt><dd>Marco Geoestadístico Nacional (MGN 2018, DANE), unión por código DIVIPOLA de 5 dígitos</dd>
<dt>Tecnología</dt><dd>Python · pandas · statsmodels · scikit-learn · PySAL · Plotly · Gradio</dd>
</dl></div>
<div><h4>Autoría</h4><div class="sello"><b>{CREDITOS['rol']}</b><br>{autores}<br><br>
<b>{CREDITOS['programa']}</b> · {CREDITOS['facultad']}<br>{CREDITOS['universidad']}<br><br>
<b>Tutoría docente:</b> {CREDITOS['docente']}<br><b>Seminario:</b> {CREDITOS['seminario']}<br>{CREDITOS['ciudad_anio']}</div></div></div>"""


def fig_pulso():
    d = DEPTO[["anio", "pib", "crecimiento_pib"]].dropna(subset=["pib"])
    f = make_subplots(specs=[[{"secondary_y": True}]])
    var = [variacion_txt(a, b, "pib") for a, b in zip(d.pib.shift(1), d.pib)]
    f.add_bar(x=d.anio, y=d.pib, name="PIB real (miles de millones COP de 2015)", marker_color="#1e3a8a", opacity=0.88,
              customdata=np.column_stack([var]),
              hovertemplate="<b>Nariño</b><br>Año: %{x}<br>PIB: $ %{y:,.0f} miles de millones<br>Variación: %{customdata[0]}<extra></extra>")
    col = [C["verde"] if (g or 0) >= 0 else C["rojo"] for g in d.crecimiento_pib.fillna(0)]
    f.add_scatter(x=d.anio, y=d.crecimiento_pib, name="Crecimiento real (%)", mode="lines+markers",
                  line=dict(color=C["ambar"], width=2.5), marker=dict(color=col, size=8, line=dict(color="white", width=1)),
                  hovertemplate="Año: %{x}<br>Crecimiento: %{y:,.1f} %<extra></extra>", secondary_y=True)
    f.update_yaxes(title_text="miles de millones COP (2015)", tickprefix="$ ", tickformat=",.0f", secondary_y=False)
    f.update_yaxes(title_text="crecimiento anual", ticksuffix=" %", tickformat=",.1f", secondary_y=True, showgrid=False, zeroline=True, zerolinecolor="#cbd5e1")
    f.update_layout(title="Pulso económico de Nariño: PIB real y crecimiento anual<br><sup>DANE, cuentas departamentales base 2015 (2024p, 2025pr)</sup>", height=450, bargap=0.25)
    return f


def fig_sectores():
    ult = int(SECT.anio.max())
    d = SECT[SECT.anio == ult].copy()
    d["sh"] = d.valor / d.valor.sum() * 100
    d = d.sort_values("sh")
    f = go.Figure(go.Bar(x=d.sh, y=d.actividad, orientation="h", marker=dict(color=d.sh, colorscale=ESCALA_AZUL, line=dict(width=0)),
                         customdata=np.column_stack([d.valor]),
                         hovertemplate="<b>%{y}</b><br>Participación: %{x:,.1f} %<br>Valor: $ %{customdata[0]:,.0f} miles de millones (2015)<extra></extra>"))
    f.update_layout(title=f"Estructura productiva de Nariño ({ult}pr)<br><sup>Participación de cada rama en el valor agregado real</sup>",
                    height=450, margin=dict(l=270, r=30, t=70, b=40))
    f.update_xaxes(ticksuffix=" %", title_text="% del valor agregado")
    return f


def fig_social():
    d = DEPTO
    f = make_subplots(rows=1, cols=3, subplot_titles=["Pobreza multidimensional (ECV)", "Pobreza monetaria y Gini", "Seguridad: tasa de homicidios"],
                      specs=[[{}, {"secondary_y": True}, {}]], horizontal_spacing=0.08)
    s = d[["anio", "ipm_dep"]].dropna()
    f.add_trace(go.Scatter(x=s.anio, y=s.ipm_dep, mode="lines+markers", name="IPM", line=dict(color=C["rojo"], width=2.8),
                           hovertemplate="Año %{x}<br>IPM: %{y:.1f} %<extra></extra>"), row=1, col=1)
    s = d[["anio", "pobreza_monetaria", "gini"]].dropna()
    f.add_trace(go.Bar(x=s.anio, y=s.pobreza_monetaria, name="Pobreza monetaria (%)", marker_color="#a78bfa",
                       hovertemplate="Año %{x}<br>Pobreza monetaria: %{y:.1f} %<extra></extra>"), row=1, col=2)
    f.add_trace(go.Scatter(x=s.anio, y=s.gini, mode="lines+markers", name="Gini", line=dict(color="#4c1d95", width=2.5),
                           hovertemplate="Año %{x}<br>Gini: %{y:.3f}<extra></extra>"), row=1, col=2, secondary_y=True)
    s = d[["anio", "tasa_homicidios_dep"]].dropna()
    f.add_trace(go.Scatter(x=s.anio, y=s.tasa_homicidios_dep, mode="lines+markers", name="Homicidios por 100 mil", fill="tozeroy",
                           fillcolor="rgba(15,23,42,.06)", line=dict(color=C["navy"], width=2.5),
                           hovertemplate="Año %{x}<br>Tasa: %{y:.1f}<extra></extra>"), row=1, col=3)
    f.update_yaxes(ticksuffix=" %", row=1, col=1)
    f.update_yaxes(ticksuffix=" %", row=1, col=2, secondary_y=False)
    f.update_yaxes(tickformat=".3f", row=1, col=2, secondary_y=True, showgrid=False)
    f.update_layout(title="Pulso social de Nariño (DANE · MinDefensa)", height=400, showlegend=False)
    f.update_annotations(font=dict(size=12, color=C["navy"]))
    return f


def fig_ctei():
    d = DEPTO[["anio", "recursos_dnp", "ctei"]].dropna().sort_values("anio")
    if d.empty:
        return fig_vacia("Sin datos de inversión CTeI", 340)
    pct = 100 * d.ctei / d.recursos_dnp
    f = make_subplots(specs=[[{"secondary_y": True}]])
    f.add_trace(go.Bar(x=d.anio, y=d.ctei, name="Inversión CTeI (miles de millones COP)", marker_color=C["azul"],
                       hovertemplate="Año %{x}<br>CTeI: %{y:,.1f} mil millones<extra></extra>"), secondary_y=False)
    f.add_trace(go.Scatter(x=d.anio, y=pct, name="% de la inversión total en proyectos", mode="lines+markers",
                           line=dict(color=C["ambar"], width=2.5),
                           hovertemplate="Año %{x}<br>Participación: %{y:.2f} %<extra></extra>"), secondary_y=True)
    f.update_yaxes(title_text="miles de millones COP", secondary_y=False)
    f.update_yaxes(title_text="% del total", ticksuffix=" %", showgrid=False, secondary_y=True)
    f.update_layout(title="Inversión pública en CTeI en Nariño<br><sup>Pagos en proyectos del sector CTeI · DNP MapaInversiones (pesos corrientes)</sup>",
                    height=360, margin=dict(t=80, b=40), legend=dict(orientation="h", y=-0.2, x=0))
    return f


def html_ctei():
    filas = "".join(f"<tr><td>{a}</td><td class='num'>{fnum(p, 2) if p else '—'}</td><td class='num'>{pos} de 33</td></tr>" for a, p, pos in IDC_NARINO)
    return callout("Ciencia, tecnología e innovación (CTeI)",
                   "<p>Nariño ocupa posiciones intermedias-bajas en el <b>Índice Departamental de Competitividad</b>. La inversión pública en proyectos "
                   "de CTeI reportada en MapaInversiones (DNP) es baja y muy irregular entre años: concentra picos en 2013, 2019 y 2021 (gráfico).</p>"
                   f'<div class="tbl-wrap" style="max-width:420px"><table class="tbl"><thead><tr><th>IDC</th><th>Puntaje (0-10)</th><th>Puesto</th></tr></thead>'
                   f"<tbody>{filas}</tbody></table></div><p class='nota-fuente'>Fuente: Consejo Privado de Competitividad y U. del Rosario, informes IDC 2024 y 2025 "
                   "(2023 según el recálculo publicado en 2024). Puntajes entre ediciones no son estrictamente comparables por cambios metodológicos.</p>",
                   "info", "🔬")


# -----------------------------------------------------------------------------
# 16. PESTAÑA 2 · RADIOGRAFÍA SOCIOECONÓMICA Y EXPLORADOR MUNICIPAL
# -----------------------------------------------------------------------------
@blindado(["html", "fig", "fig", "fig", "html", "html", "fig", "file"])
def tab2_run(subs, muns, a0, a1, ind, anio, vista):
    a0, a1 = rango(a0, a1)
    k = ind
    m = META[k]
    pedido = int(anio)
    anio = anio_valido(k, pedido)
    sel = municipios_sel(subs, muns)
    cr = corte(anio, [k]).dropna(subset=[k])
    s = m["sentido"] or 1
    if vista == "Selección actual":
        dr = cr[cr.municipio.isin(sel)]
    else:
        dr = cr.sort_values(k, ascending=(s == 1) if vista == "25 más críticos" else (s != 1)).head(25)
    dr = dr.sort_values(k, ascending=True)
    resaltar = set(sel) if len(sel) < 64 else set()
    opac = [1.0 if (not resaltar or mm in resaltar) else 0.35 for mm in dr.municipio]
    if m["corte"] == "anual":
        prev = corte(anio - 1, [k]).set_index("municipio")[k]
        var = [variacion_txt(prev.get(mm, np.nan), v, k) for mm, v in zip(dr.municipio, dr[k])]
    else:
        var = ["corte único"] * len(dr)
    marca = ["†" if es_imputado(k, c, anio) else "" for c in dr.codigo]
    f_rank = go.Figure(go.Bar(x=dr[k], y=[f"{a}{b}" for a, b in zip(dr.municipio, marca)], orientation="h",
                              marker=dict(color=[COLOR_SUB[x] for x in dr.subregion], opacity=opac),
                              customdata=np.column_stack([dr.subregion, var]),
                              hovertemplate=f"<b>%{{y}}</b> · %{{customdata[0]}}<br>Año: {anio}<br>{m['nombre']}: %{{x:,.{m['dec']}f}} {m['unidad']}<br>Variación anual: %{{customdata[1]}}<extra></extra>"))
    med = cr[k].median()
    if len(dr) < 6:
        f_rank.update_traces(width=0.45)
    f_rank.add_vline(x=med, line=dict(color=C["ambar"], dash="dash", width=2))
    f_rank.update_layout(title=f"{m['nombre']} · {vista.lower()} ({anio})<br><sup>Línea punteada: mediana de Nariño ({fmt_val(med, k)}) · † dato imputado (PCHIP)</sup>",
                         height=max(460, min(560, 22 * len(dr) + 130)), margin=dict(l=160, r=30, t=70, b=50))
    eje(f_rank, k, "x")
    f_box = go.Figure()
    for sb in SUBREGIONES:
        dd = cr[cr.subregion == sb]
        f_box.add_trace(go.Box(y=dd[k], name=sb, marker_color=COLOR_SUB[sb], boxpoints="all", jitter=0.4, pointpos=0,
                               marker=dict(size=6, opacity=0.8), line=dict(width=1.6), text=dd.municipio,
                               hovertemplate=f"<b>%{{text}}</b><br>{sb}<br>Año: {anio}<br>{m['nombre']}: %{{y:,.{m['dec']}f}}<extra></extra>"))
    if hay_seleccion(sel):
        ds = cr[cr.municipio.isin(sel)]
        f_box.add_trace(go.Scatter(x=ds.subregion, y=ds[k], mode="markers+text" if len(ds) <= MAX_DETALLE else "markers",
                                   text=ds.municipio, textposition="middle right", textfont=dict(size=11, color=C["navy"]),
                                   marker=dict(symbol="star", size=16, color="#f59e0b", line=dict(color=C["navy"], width=1.5)),
                                   name="Selección", hovertemplate=f"<b>%{{text}}</b> (selección)<br>Año: {anio}<br>{m['nombre']}: %{{y:,.{m['dec']}f}}<extra></extra>"))
    f_box.update_layout(title=f"Brechas entre subregiones ({anio}){'<br><sup>★ municipios de su selección</sup>' if hay_seleccion(sel) else ''}",
                        showlegend=False, height=480, margin=dict(l=70, r=20, t=60, b=110))
    f_box.update_xaxes(tickangle=-35)
    eje(f_box, k, "y")
    # Trayectorias o brecha urbano-rural
    if m["corte"] == "anual":
        d = PANEL[(PANEL.anio >= a0) & (PANEL.anio <= a1)].dropna(subset=[k])
        f_tr = go.Figure()
        mediana = d.groupby("anio")[k].median()
        q25, q75 = d.groupby("anio")[k].quantile(0.25), d.groupby("anio")[k].quantile(0.75)
        f_tr.add_trace(go.Scatter(x=list(q75.index) + list(q25.index[::-1]), y=list(q75.values) + list(q25.values[::-1]), mode="lines", fill="toself",
                                  fillcolor="rgba(148,163,184,.18)", line=dict(width=0), name="Rango intercuartílico municipal", hoverinfo="skip"))
        f_tr.add_trace(go.Scatter(x=mediana.index, y=mediana.values, name="Mediana municipal de Nariño", mode="lines",
                                  line=dict(color=C["ambar"], width=3, dash="dash"),
                                  hovertemplate=f"<b>Mediana Nariño</b><br>Año: %{{x}}<br>{m['nombre']}: %{{y:,.{m['dec']}f}}<extra></extra>"))
        grupos = [(mm, d[d.municipio == mm], COLOR_SUB[MUN_A_SUB[mm]]) for mm in sel] if len(sel) <= 8 else \
            [(f"{sb} (mediana)", d[d.municipio.isin(sel) & (d.subregion == sb)].groupby("anio")[k].median().reset_index(), COLOR_SUB[sb])
             for sb in SUBREGIONES if (d.municipio.isin(sel) & (d.subregion == sb)).any()]
        for nm, g, col in grupos:
            vv = [variacion_txt(p, c, k) for p, c in zip(g[k].shift(1), g[k])]
            f_tr.add_trace(go.Scatter(x=g.anio, y=g[k], name=nm, mode="lines+markers", line=dict(color=col, width=2.4), marker=dict(size=5),
                                      customdata=np.column_stack([[nm] * len(g), vv]),
                                      hovertemplate=f"<b>%{{customdata[0]}}</b><br>Año: %{{x}}<br>{m['nombre']}: %{{y:,.{m['dec']}f}}<br>Variación: %{{customdata[1]}}<extra></extra>"))
        f_tr.update_layout(title=f"Trayectoria {a0}–{a1}: territorios seleccionados frente a la mediana de Nariño", height=470)
        eje(f_tr, k, "y")
        f_tr.update_xaxes(dtick=2, title_text="")
    else:
        dd = CS[CS.municipio.isin(sel)] if len(sel) < 64 else CS
        dd = dd.sort_values("ipm")
        f_tr = go.Figure()
        for _, r in dd.iterrows():
            f_tr.add_trace(go.Scatter(x=[r.ipm_urbano, r.ipm_rural], y=[r.municipio] * 2, mode="lines", line=dict(color="#cbd5e1", width=3),
                                      showlegend=False, hoverinfo="skip"))
        f_tr.add_trace(go.Scatter(x=dd.ipm_urbano, y=dd.municipio, mode="markers", name="Cabecera", marker=dict(size=9, color=C["azul"]),
                                  hovertemplate="<b>%{y}</b><br>IPM cabecera: %{x:.1f} %<extra></extra>"))
        f_tr.add_trace(go.Scatter(x=dd.ipm_rural, y=dd.municipio, mode="markers", name="Rural disperso", marker=dict(size=9, color=C["rojo"]),
                                  hovertemplate="<b>%{y}</b><br>IPM rural: %{x:.1f} %<extra></extra>"))
        f_tr.update_layout(title="Brecha urbano-rural del IPM por municipio (CNPV 2018)", height=max(470, 15 * len(dd) + 140),
                           margin=dict(l=160, r=20, t=60, b=60))
        f_tr.update_xaxes(ticksuffix=" %", title_text="% de personas en pobreza multidimensional")
        f_tr.update_yaxes(tickfont=dict(size=10))
    # Atípicos
    x = cr[k].astype(float)
    q1, q3 = x.quantile(0.25), x.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    zz = (x - x.mean()) / x.std(ddof=1)
    out = cr.assign(z=zz.values)
    out = out[(out[k] < lo) | (out[k] > hi) | (out.z.abs() > 2.5)].copy()
    out["Criterio"] = [("IQR alto" if v > hi else "IQR bajo" if v < lo else "") + (" · |Z|>2,5" if abs(z) > 2.5 else "") for v, z in zip(out[k], out.z)]
    tabla_out = out[["municipio", "subregion", k, "z", "Criterio"]].rename(columns={"municipio": "Municipio", "subregion": "Subregión", k: m["nombre"], "z": "Z-score"})
    html_out = (tabla_html(tabla_out.sort_values("Z-score", key=abs, ascending=False), decs={m["nombre"]: m["dec"], "Z-score": 2})
                if len(tabla_out) else callout("Sin valores atípicos", "<p>Ningún municipio supera 1,5 × IQR ni |Z| > 2,5.</p>", "ok", "✅"))
    html_out = (f'<div class="obs-section-title" style="font-size:16px">Detección de valores atípicos ({anio})</div>'
                f'<div class="obs-section-sub">Umbrales de Tukey: {fmt_val(lo, k)} a {fmt_val(hi, k)} · Z con media {fmt_val(x.mean(), k)} y desviación {fmt_val(x.std(), k)}</div>' + html_out)
    # Narrativa
    peor = cr.sort_values(k, ascending=(s == 1)).iloc[0]
    mejor = cr.sort_values(k, ascending=(s != 1)).iloc[0]
    sub_m = cr.groupby("subregion")[k].mean().sort_values(ascending=(s == 1))
    brecha = (f"{fnum(abs(sub_m.iloc[-1] - sub_m.iloc[0]), 1)} p.p." if m["tipo"] == "pct"
              else f"{fnum(max(sub_m.max(), 1e-9) / max(sub_m.min(), 1e-9), 1)} veces" if sub_m.min() > 0 else f"{fmt_val(sub_m.max() - sub_m.min(), k)}")
    tendencia_txt = ""
    if m["corte"] == "anual":
        serie = PANEL.dropna(subset=[k]).groupby("anio")[k].median()
        serie = serie[(serie.index >= a0) & (serie.index <= a1)]
        if len(serie) >= 2:
            mejora = (serie.iloc[-1] - serie.iloc[0]) * s > 0
            tendencia_txt = (f"<li>Entre {serie.index[0]} y {serie.index[-1]} la mediana pasó de {fmt_val(serie.iloc[0], k)} a "
                             f"{fmt_val(serie.iloc[-1], k)}: <b>{'mejora' if mejora else 'deterioro'}</b>.</li>")
    sel_txt = ""
    items_sel = []
    if hay_seleccion(sel):
        vs = valor_seleccion(sel, k, anio)
        rel = "mejor" if (vs - med) * s > 0 else "peor"
        if len(sel) > 1:
            items_sel.append(f"Su selección ({len(sel)} municipios) registra <b>{fmt_val(vs, k)}</b> (promedio ponderado por población), "
                             f"<b>{rel}</b> que la mediana departamental ({fmt_val(med, k)}).")
        vals_sel = cr.set_index("municipio")[k]
        for mm in sel[:MAX_DETALLE]:
            v = vals_sel.get(mm, np.nan)
            if not np.isfinite(v):
                items_sel.append(f"<b>{mm}</b>: sin dato en {anio}.")
                continue
            var_t = f" · variación anual {variacion_txt(prev.get(mm, np.nan), v, k)}" if m["corte"] == "anual" else ""
            items_sel.append(f"<b>{mm}</b> ({MUN_A_SUB[mm]}): {fmt_val(v, k)} · {puesto_txt(k, anio, mm)} · "
                             f"{'mejor' if (v - med) * s > 0 else 'peor' if (v - med) * s < 0 else 'igual'} que la mediana{var_t}.")
        if len(sel) > MAX_DETALLE:
            items_sel.append(f"… y {len(sel) - MAX_DETALLE} municipios más (vista «Selección actual» del ranking).")
    cuerpo = (f"<p>En <b>{anio}</b> la mediana municipal de <b>{minus(m['nombre'])}</b> en Nariño fue <b>{fmt_val(med, k)}</b> ({m['unidad']}).</p><ul>"
              f"<li>Situación más crítica: <b>{peor.municipio}</b> ({peor.subregion}) con {fmt_val(peor[k], k)}; más favorable: "
              f"<b>{mejor.municipio}</b> ({mejor.subregion}) con {fmt_val(mejor[k], k)}.</li>"
              f"<li>Entre subregiones, <b>{sub_m.index[0]}</b> presenta el peor promedio y <b>{sub_m.index[-1]}</b> el mejor: brecha de <b>{brecha}</b>.</li>"
              f"{tendencia_txt}<li><b>{len(tabla_out)}</b> municipios con valores atípicos requieren revisión focalizada.</li>{sel_txt}</ul>"
              f"<p class='nota-fuente'>{etiqueta_fuente(k)}</p>{nota_anio(k, pedido, anio)}")
    if items_sel:
        cuerpo = cuerpo.replace("<p class='nota-fuente'>", bloque_sel(f"Su selección · {minus(m['nombre'])} ({anio})", items_sel) + "<p class='nota-fuente'>", 1)
    html_n = callout("Diagnóstico para la decisión pública", cuerpo, "info", "🧭")
    # Técnica
    desc = cr.groupby("subregion")[k].agg(["count", "mean", "median", "std", "min", "max"]).reset_index()
    desc.columns = ["Subregión", "n", "Media", "Mediana", "Desv. est.", "Mín.", "Máx."]
    desc["CV (%)"] = desc["Desv. est."] / desc["Media"].abs() * 100
    sh = sps.shapiro(x)
    jb = sps.jarque_bera(x)
    grupos_ = [g[k].values for _, g in cr.groupby("subregion") if len(g) > 1]
    kw = sps.kruskal(*grupos_)
    an = sps.f_oneway(*grupos_)
    xs = np.sort(x.values - min(0, x.min()))
    gini_t = (2 * np.sum(np.arange(1, len(xs) + 1) * xs) / (len(xs) * xs.sum()) - (len(xs) + 1) / len(xs)) if xs.sum() > 0 else np.nan
    pruebas = pd.DataFrame([
        ["Shapiro-Wilk (normalidad)", sh[0], sh[1], "No normal" if sh[1] < 0.05 else "Compatible con normalidad"],
        ["Jarque-Bera (normalidad)", jb[0], jb[1], "No normal" if jb[1] < 0.05 else "Compatible con normalidad"],
        ["Kruskal-Wallis (subregiones)", kw[0], kw[1], "Subregiones difieren" if kw[1] < 0.05 else "Sin diferencias significativas"],
        ["ANOVA F (medias por subregión)", an[0], an[1], "Medias difieren" if an[1] < 0.05 else "Medias similares"],
    ], columns=["Prueba", "Estadístico", "p-valor", "Conclusión (α = 5 %)"])
    n_imp = sum(es_imputado(k, c, anio) for c in cr.codigo)
    tec = (f'<div class="tec"><h5>Estadística descriptiva por subregión ({anio})</h5>{tabla_html(desc, decs={"n": 0})}'
           f'<h5>Pruebas formales</h5>{tabla_html(pruebas, decs={"Estadístico": 3, "p-valor": 4})}'
           f'<p>Asimetría: {fnum(sps.skew(x), 3)} · Curtosis (exceso): {fnum(sps.kurtosis(x), 3)} · Gini territorial del indicador: {fnum(gini_t, 3)} · '
           f'CV global: {fnum(x.std() / abs(x.mean()) * 100, 1)} % · Observaciones imputadas en el corte: {n_imp}.</p></div>')
    cols = list(IND_MUN)
    cm_df = corte_transversal(max(a0, 2011), min(a1, 2022), cols)[cols]
    cm = cm_df.corr(method="spearman")
    etiq = [nombre(c).split("(")[0].strip()[:30] for c in cols]
    f_corr = go.Figure(go.Heatmap(z=cm.values, x=etiq, y=etiq, zmin=-1, zmax=1, colorscale=ESCALA_DIV, text=np.round(cm.values, 2),
                                  texttemplate="%{text:.2f}", textfont=dict(size=8.5),
                                  hovertemplate="%{y} × %{x}<br>ρ de Spearman: %{z:.3f}<extra></extra>", colorbar=dict(title="ρ", thickness=12)))
    f_corr.update_layout(title="Correlaciones de Spearman entre indicadores municipales<br><sup>Promedios municipales del periodo (máx. 2011-2022) y cortes censales</sup>",
                         height=720, margin=dict(l=230, r=30, t=70, b=200))
    f_corr.update_xaxes(tickangle=-45)
    dsel = PANEL[(PANEL.anio >= a0) & (PANEL.anio <= a1) & (PANEL.municipio.isin(sel))].merge(
        CS[["codigo"] + IND_MUN_CENSAL], on="codigo", how="left")
    ruta = tempfile.NamedTemporaryFile(prefix="observatorio_narino_", suffix=".csv", delete=False).name
    dsel.to_csv(ruta, index=False, encoding="utf-8-sig")
    return html_n, f_rank, f_box, f_tr, html_out, tec, f_corr, ruta


# -----------------------------------------------------------------------------
# 17. PESTAÑA 3 · GEOINTELIGENCIA Y ECONOMETRÍA ESPACIAL
# -----------------------------------------------------------------------------
CUAD_COL = {"Alto-Alto": "#b91c1c", "Bajo-Bajo": "#1e3a8a", "Alto-Bajo": "#f59e0b", "Bajo-Alto": "#60a5fa", "No significativo": "#e2e8f0"}
SIG_COL = {"p < 0,01": "#0f172a", "p < 0,05": "#1e40af", "p < 0,10": "#60a5fa", "No significativo": "#e2e8f0"}


def lisa_etiquetas(res, alfa=0.05):
    nom = {1: "Alto-Alto", 2: "Bajo-Alto", 3: "Bajo-Bajo", 4: "Alto-Bajo"}
    return np.array([nom[int(q)] if p < alfa else "No significativo" for q, p in zip(res["q"], res["p_loc"])])


@functools.lru_cache(maxsize=64)
def moran_por_anio(k, tipo_w, kv):
    if META[k]["corte"] == "censal":
        return pd.DataFrame()
    W = matriz_pesos(tipo_w, int(kv))
    filas = []
    for a in anios_disp(k):
        y = corte(a, [k]).set_index("codigo").loc[CODIGOS, k].values.astype(float)
        if np.isnan(y).any() or np.nanstd(y) == 0:
            continue
        r = moran_global(y, W, perms=199)
        filas.append((a, r["I"], r["p_sim"]))
    return pd.DataFrame(filas, columns=["anio", "I", "p"])


@blindado(["html", "fig", "fig", "fig", "fig", "fig", "html"])
def tab3_run(subs, muns, a0, a1, ind, anio, tipo_w, k_vec):
    k = ind
    m = META[k]
    pedido = int(anio)
    anio = anio_valido(k, pedido)
    sel = municipios_sel(subs, muns)
    d = corte(anio, [k]).set_index("codigo").loc[CODIGOS].reset_index()
    y = d[k].values.astype(float)
    if np.isnan(y).any():
        faltan = d.municipio[np.isnan(y)].tolist()
        raise ValueError(f"faltan datos para {', '.join(faltan[:5])}; elija otro año o indicador")
    W = matriz_pesos(tipo_w, int(k_vec))
    res = moran_global(y, W)
    textos = [f"<b>{mm}</b> · {sb}<br>Año: {anio}<br>{m['nombre']}: {fmt_val(v, k)}" for mm, sb, v in zip(d.municipio, d.subregion, y)]
    f_map = mapa_municipal(y, f"{m['nombre']} por municipio ({anio})<br><sup>{'Verde = mejor situación' if m['sentido'] == 1 else 'Rojo intenso = mayor alerta' if m['sentido'] == -1 else 'Escala secuencial'}</sup>",
                           escala_de(k), textos=textos, resaltar=sel if len(sel) < 64 else None, cbar_title=m["unidad"][:24])
    etiqueta = lisa_etiquetas(res)
    textos_l = [f"<b>{mm}</b><br>Clúster LISA: {et}<br>I local: {fnum(ii, 3)}<br>p (pseudo): {fnum(p, 3)}"
                for mm, et, ii, p in zip(d.municipio, etiqueta, res["Ii"], res["p_loc"])]
    f_lisa = mapa_municipal(etiqueta, "Mapa de clústeres LISA (α = 0,05)<br><sup>Alto-Alto: puntos calientes · Bajo-Bajo: núcleos fríos</sup>",
                            textos=textos_l, discreto=(list(CUAD_COL.keys()), CUAD_COL), resaltar=sel if len(sel) < 64 else None)
    p = np.asarray(res["p_loc"])
    sig = np.where(p < 0.01, "p < 0,01", np.where(p < 0.05, "p < 0,05", np.where(p < 0.10, "p < 0,10", "No significativo")))
    f_sig = mapa_municipal(sig, "Mapa de significancia de Moran local<br><sup>p-valores empíricos por 999 permutaciones condicionales</sup>",
                           textos=[f"<b>{mm}</b><br>p (pseudo): {fnum(pp, 4)}" for mm, pp in zip(d.municipio, p)],
                           discreto=(list(SIG_COL.keys()), SIG_COL), resaltar=sel if len(sel) < 64 else None)
    # Diagrama de dispersión de Moran: pendiente exacta = I
    Wr = W / W.sum(1, keepdims=True)
    z = (y - y.mean()) / y.std()
    lag = Wr @ z
    pend = float(np.cov(z, lag, bias=True)[0, 1] / np.var(z))
    f_sc = go.Figure()
    for et in ["Alto-Alto", "Bajo-Bajo", "Alto-Bajo", "Bajo-Alto", "No significativo"]:
        msk = etiqueta == et
        if msk.any():
            f_sc.add_trace(go.Scatter(x=z[msk], y=lag[msk], mode="markers", name=et, text=d.municipio.values[msk],
                                      marker=dict(size=11, color=CUAD_COL[et] if et != "No significativo" else "#94a3b8", line=dict(color="white", width=1)),
                                      hovertemplate="<b>%{text}</b><br>z: %{x:.2f}<br>Wz: %{y:.2f}<extra></extra>"))
    xx = np.linspace(z.min(), z.max(), 10)
    f_sc.add_trace(go.Scatter(x=xx, y=pend * xx + lag.mean(), mode="lines", name=f"Pendiente = I de Moran = {fnum(pend, 4)}",
                              line=dict(color=C["navy"], width=2.5), hoverinfo="skip"))
    f_sc.add_hline(y=0, line=dict(color="#94a3b8", width=1))
    f_sc.add_vline(x=0, line=dict(color="#94a3b8", width=1))
    for (xa, ya, tx) in [(0.98, 0.98, "Alto-Alto"), (0.02, 0.02, "Bajo-Bajo"), (0.02, 0.98, "Bajo-Alto"), (0.98, 0.02, "Alto-Bajo")]:
        f_sc.add_annotation(x=xa, y=ya, xref="paper", yref="paper", text=tx, showarrow=False, font=dict(size=11, color="#64748b"),
                            xanchor="right" if xa > 0.5 else "left", yanchor="top" if ya > 0.5 else "bottom")
    f_sc.update_layout(title=f"Diagrama de dispersión de Moran · I = {fnum(res['I'], 4)} (p = {fnum(res['p_sim'], 3)})", height=500)
    f_sc.update_xaxes(title_text=f"z = {m['nombre']} estandarizado")
    f_sc.update_yaxes(title_text="Wz = rezago espacial (promedio de vecinos)")
    # Evolución temporal del I de Moran
    mt = moran_por_anio(k, tipo_w, int(k_vec))
    if len(mt):
        f_t = go.Figure()
        f_t.add_trace(go.Scatter(x=mt.anio, y=mt.I, mode="lines+markers", name="I de Moran",
                                 marker=dict(size=9, color=[C["verde"] if pp < 0.05 else "#94a3b8" for pp in mt.p], line=dict(color="white", width=1)),
                                 line=dict(color=C["azul"], width=2.5), customdata=mt.p,
                                 hovertemplate="Año %{x}<br>I: %{y:.3f}<br>p: %{customdata:.3f}<extra></extra>"))
        f_t.add_hline(y=-1 / 63, line=dict(color=C["ambar"], dash="dash"), annotation_text="E[I] = −1/(n−1)", annotation_position="bottom right")
        f_t.update_layout(title="Evolución del agrupamiento espacial (punto verde: significativo al 5 %)", height=380)
        f_t.update_xaxes(dtick=2)
        f_t.update_yaxes(title_text="I de Moran")
    else:
        f_t = fig_vacia("Indicador de corte único (censo 2018): no hay serie temporal del I de Moran", 140)
    # Narrativa
    I, pv = res["I"], res["p_sim"]
    hh = d.municipio.values[etiqueta == "Alto-Alto"].tolist()
    ll = d.municipio.values[etiqueta == "Bajo-Bajo"].tolist()
    malo, bueno = (hh, ll) if m["sentido"] == -1 else (ll, hh)
    if pv < 0.05 and I > 0:
        tono, titulo = ("alert" if m["sentido"] != 0 else "info"), "El indicador se concentra geográficamente"
        txt = (f"<p>El I de Moran es <b>{fnum(I, 3)}</b> y significativo (p = {fnum(pv, 3)}): municipios con valores parecidos de "
               f"<b>{minus(m['nombre'])}</b> tienden a ser vecinos. Las causas trascienden los límites municipales: conviene un enfoque <b>subregional</b>.</p>")
    elif pv < 0.05 and I < 0:
        tono, titulo = "warn", "Patrón de contraste entre vecinos"
        txt = f"<p>El I de Moran es negativo (<b>{fnum(I, 3)}</b>, p = {fnum(pv, 3)}): vecinos con valores opuestos, típico de polos y periferias.</p>"
    else:
        tono, titulo = "info", "Sin agrupamiento espacial significativo"
        txt = f"<p>El I de Moran (<b>{fnum(I, 3)}</b>, p = {fnum(pv, 3)}) no rechaza la aleatoriedad espacial.</p>"
    txt += "<ul>"
    if malo:
        txt += f"<li><b>Focos críticos</b>: {', '.join(malo[:10])}{'…' if len(malo) > 10 else ''}.</li>"
    if bueno:
        txt += f"<li><b>Núcleos de buen desempeño</b>: {', '.join(bueno[:10])}{'…' if len(bueno) > 10 else ''}.</li>"
    txt += f"<li>Matriz de vecindad: <b>{tipo_w}</b> sobre límites oficiales MGN-DANE.</li></ul>"
    if hay_seleccion(sel):
        lect_lisa = {"Alto-Alto": "valor alto rodeado de vecinos altos", "Bajo-Bajo": "valor bajo rodeado de vecinos bajos",
                     "Alto-Bajo": "valor alto entre vecinos bajos (atípico)", "Bajo-Alto": "valor bajo entre vecinos altos (atípico)",
                     "No significativo": "sin patrón local significativo"}
        pos = {mm: i for i, mm in enumerate(d.municipio)}
        items = []
        for mm in sel[:MAX_DETALLE]:
            i = pos[mm]
            items.append(f"<b>{mm}</b>: {fmt_val(y[i], k)} · {puesto_txt(k, anio, mm)} · clúster LISA <b>{etiqueta[i]}</b> "
                         f"({lect_lisa.get(etiqueta[i], '')}; p = {fnum(p[i], 3)}).")
        if len(sel) > MAX_DETALLE:
            cnt = pd.Series(etiqueta[[pos[mm] for mm in sel]]).value_counts()
            items.append(f"Resumen de los {len(sel)} municipios: " + ", ".join(f"{et}: {n}" for et, n in cnt.items()) + ".")
        txt += bloque_sel(f"Su selección en el mapa ({anio})", items)
    html_n = callout(titulo, txt + f'<p class="nota-fuente">{etiqueta_fuente(k)}</p>{nota_anio(k, pedido, anio)}', tono, "🗺️")
    vecinos = (W > 0).sum(1)
    tab = pd.DataFrame([
        ["I de Moran global", res["I"]], ["Pendiente OLS de Wz sobre z (verificación)", pend], ["E[I] = −1/(n−1)", res["EI"]],
        ["Var(I) bajo normalidad", res["VI"]], ["z (normalidad)", res["z"]], ["p-valor (normalidad)", res["p_norm"]],
        ["z (permutaciones)", res["z_sim"]], ["p-valor pseudo (999 permutaciones)", res["p_sim"]],
        ["C de Geary", res["geary"][0]], ["p-valor Geary", res["geary"][1]],
        ["Vecinos promedio", vecinos.mean()], ["Mín. / máx. vecinos", f"{vecinos.min()} / {vecinos.max()}"],
        ["Municipios en clúster LISA (α = 5 %)", int((etiqueta != "No significativo").sum())],
    ], columns=["Estadístico", "Valor"])
    tec = (f'<div class="tec"><h5>Autocorrelación espacial global</h5>{tabla_html(tab, decs={"Valor": 4})}'
           f'<p>Motor: {res["motor"]}. W estandarizada por filas; la pendiente del diagrama coincide con el I de Moran por construcción. '
           f'Contigüidad calculada sobre los polígonos MGN (fronteras compartidas reales).</p><h5>LISA significativos</h5>'
           + tabla_html(pd.DataFrame({"Municipio": d.municipio, "Subregión": d.subregion, "I local": res["Ii"], "p (pseudo)": res["p_loc"],
                                      "Clúster": etiqueta}).query("Clúster != 'No significativo'").sort_values("p (pseudo)"),
                        decs={"I local": 3, "p (pseudo)": 4}) + "</div>")
    return html_n, f_map, f_lisa, f_sig, f_sc, f_t, tec


# -----------------------------------------------------------------------------
# 18. PESTAÑA 4 · TIPOLOGÍAS TERRITORIALES Y MINERÍA DE DATOS
# -----------------------------------------------------------------------------
VARS_TIPO = ["ipm", "va_pc", "cobertura_neta", "tasa_homicidios", "coca_pct", "dep_transf", "rec_propios", "priv_sin_agua", "priv_trab_informal"]


def matriz_estandarizada(a0, a1, vars_, logasim=True):
    cs = corte_transversal(a0, a1, vars_)
    X = cs[list(vars_)].astype(float).copy()
    faltan = X.isna().any(axis=1)
    if faltan.any():
        X = X.fillna(X.median())
    transform = {}
    if logasim:
        for c in vars_:
            if (X[c] >= 0).all() and sps.skew(X[c]) > 1.5:
                X[c] = np.log1p(X[c])
                transform[c] = "log(1+x)"
    Z = StandardScaler().fit_transform(X.values)
    return cs, X, Z, transform


def nombrar_clusters(Z, etiquetas, vars_):
    nombres = {}
    for c in sorted(set(etiquetas)):
        if c == -1:
            nombres[c] = "Atípicos (ruido)"
            continue
        mu = Z[etiquetas == c].mean(0)
        orden = np.argsort(-np.abs(mu))[:2]
        partes = [f"{'↑' if mu[j] > 0 else '↓'} {minus(nombre(vars_[j]).split('(')[0].strip())}" for j in orden]
        nombres[c] = f"T{c + 1}: " + ", ".join(partes)
    return nombres


@blindado(["html", "fig", "fig", "fig", "fig", "html", "html", "fig"])
def tab4_run(subs, muns, a0, a1, vars_, k, metodo, eps, logasim):
    a0, a1 = rango(a0, a1)
    vars_ = list(vars_ or VARS_TIPO)
    if len(vars_) < 2:
        raise ValueError("Seleccione al menos 2 variables")
    sel = municipios_sel(subs, muns)
    cs, X, Z, transf = matriz_estandarizada(a0, a1, vars_, logasim)
    k = int(k)
    km = KMeans(n_clusters=k, n_init=25, random_state=0).fit(Z)
    ag = AgglomerativeClustering(n_clusters=k, linkage="ward").fit(Z)
    db = DBSCAN(eps=float(eps), min_samples=3).fit(Z)
    etq = {"K-Means": km.labels_, "Jerárquico (Ward)": ag.labels_, "DBSCAN": db.labels_}
    lab = etq[metodo]
    nombres_c = nombrar_clusters(Z, lab, vars_)
    pca = PCA(n_components=2).fit(Z)
    P2 = pca.transform(Z)
    paleta = ["#1e3a8a", "#10b981", "#f59e0b", "#ef4444", "#7c3aed", "#0891b2", "#c2410c", "#475569"]
    col_c = {c: (paleta[c % len(paleta)] if c >= 0 else "#94a3b8") for c in set(lab)}
    f_pca = go.Figure()
    for c in sorted(set(lab)):
        msk = lab == c
        f_pca.add_trace(go.Scatter(x=P2[msk, 0], y=P2[msk, 1], mode="markers", name=nombres_c[c],
                                   marker=dict(size=[15 if mm in sel and len(sel) < 64 else 10 for mm in cs.municipio[msk]],
                                               color=col_c[c], line=dict(color="white", width=1)),
                                   text=cs.municipio[msk], customdata=cs.subregion[msk],
                                   hovertemplate="<b>%{text}</b> · %{customdata}<br>CP1: %{x:.2f} · CP2: %{y:.2f}<extra></extra>"))
    if len(sel) < 64:
        msk = cs.municipio.isin(sel).values
        f_pca.add_trace(go.Scatter(x=P2[msk, 0], y=P2[msk, 1], mode="text", text=cs.municipio[msk], textposition="top center",
                                   textfont=dict(size=10, color=C["navy"]), showlegend=False, hoverinfo="skip"))
    f_pca.update_layout(title=f"Tipologías territoriales ({metodo}) proyectadas en el plano PCA 2D", height=520,
                        legend=dict(orientation="v", y=1, x=1.01, yanchor="top", xanchor="left"), margin=dict(r=260))
    f_pca.update_xaxes(title_text=f"Componente 1 ({fnum(pca.explained_variance_ratio_[0] * 100, 1)} % de la varianza)")
    f_pca.update_yaxes(title_text=f"Componente 2 ({fnum(pca.explained_variance_ratio_[1] * 100, 1)} %)")
    ks = list(range(2, 9))
    sil, inercia = [], []
    for kk in ks:
        mm_ = KMeans(n_clusters=kk, n_init=15, random_state=0).fit(Z)
        sil.append(silhouette_score(Z, mm_.labels_))
        inercia.append(mm_.inertia_)
    f_sil = make_subplots(specs=[[{"secondary_y": True}]])
    f_sil.add_bar(x=ks, y=sil, name="Silhouette (K-Means)", marker_color=[C["verde"] if kk == ks[int(np.argmax(sil))] else "#93c5fd" for kk in ks],
                  hovertemplate="k = %{x}<br>Silhouette: %{y:.3f}<extra></extra>")
    f_sil.add_scatter(x=ks, y=inercia, name="Inercia (método del codo)", mode="lines+markers", line=dict(color=C["navy"], width=2.5),
                      hovertemplate="k = %{x}<br>Inercia: %{y:,.1f}<extra></extra>", secondary_y=True)
    f_sil.update_layout(title=f"Número de tipologías: Silhouette máximo en k = {ks[int(np.argmax(sil))]}", height=450)
    f_sil.update_xaxes(title_text="Número de clústeres (k)", dtick=1)
    f_sil.update_yaxes(title_text="Silhouette", secondary_y=False, tickformat=".2f")
    f_sil.update_yaxes(title_text="Inercia intra-clúster", secondary_y=True, showgrid=False)
    perf = pd.DataFrame(Z, columns=vars_).assign(c=lab).groupby("c").mean()
    perf.index = [nombres_c[i] for i in perf.index]
    f_perf = go.Figure(go.Heatmap(z=perf.values, x=[nombre(v).split("(")[0].strip()[:28] for v in vars_], y=perf.index, colorscale=ESCALA_DIV, zmid=0,
                                  text=np.round(perf.values, 2), texttemplate="%{text:.2f}", textfont=dict(size=11),
                                  hovertemplate="%{y}<br>%{x}<br>Desvío estandarizado: %{z:.2f}<extra></extra>", colorbar=dict(title="z", thickness=12)))
    f_perf.update_layout(title="Perfil de cada tipología (promedios estandarizados: azul = por encima, rojo = por debajo de Nariño)",
                         height=max(420, 70 * len(perf) + 230), margin=dict(l=320, r=30, t=60, b=160))
    f_perf.update_xaxes(tickangle=-35)
    cs_ord = cs.set_index("codigo").loc[CODIGOS]
    lab_ord = pd.Series(lab, index=cs.codigo).loc[CODIGOS].values
    etiquetas_mapa = np.array([nombres_c[c] for c in lab_ord])
    textos = [f"<b>{mm}</b> · {sb}<br>{nombres_c[c]}" for mm, sb, c in zip(cs_ord.municipio, cs_ord.subregion, lab_ord)]
    f_map = mapa_municipal(etiquetas_mapa, f"Mapa de tipologías territoriales ({metodo})", textos=textos,
                           discreto=([nombres_c[c] for c in sorted(set(lab))], {nombres_c[c]: col_c[c] for c in set(lab)}),
                           resaltar=sel if len(sel) < 64 else None)
    filas = [[nombres_c[c], int((lab == c).sum()), ", ".join(cs.municipio[lab == c].tolist())] for c in sorted(set(lab))]
    tabla = tabla_html(pd.DataFrame(filas, columns=["Tipología", "N.º municipios", "Municipios"]), decs={"N.º municipios": 0})
    met = []
    for nm, l in etq.items():
        nclu = len(set(l) - {-1})
        msk = l != -1
        if nclu >= 2 and msk.sum() > nclu:
            met.append([nm, nclu, int((l == -1).sum()), silhouette_score(Z[msk], l[msk]), calinski_harabasz_score(Z[msk], l[msk]),
                        davies_bouldin_score(Z[msk], l[msk])])
        else:
            met.append([nm, nclu, int((l == -1).sum()), np.nan, np.nan, np.nan])
    dfm = pd.DataFrame(met, columns=["Algoritmo", "Clústeres", "Ruido", "Silhouette ↑", "Calinski-Harabasz ↑", "Davies-Bouldin ↓"])
    mejor = dfm.dropna().sort_values("Silhouette ↑", ascending=False).iloc[0]["Algoritmo"] if dfm["Silhouette ↑"].notna().any() else metodo
    sil_act = dfm.loc[dfm.Algoritmo == metodo, "Silhouette ↑"].iloc[0]
    calidad = "fuerte" if sil_act > 0.5 else "razonable" if sil_act > 0.25 else "débil"
    grande = max(filas, key=lambda r: r[1])
    cuerpo = (f"<p>Con <b>{metodo}</b> los 64 municipios se agrupan en <b>{len(set(lab) - {-1})}</b> tipologías con estructura "
              f"<b>{calidad}</b> (Silhouette = {fnum(sil_act, 3)}). El algoritmo con mejor separación es <b>{mejor}</b>.</p><ul>"
              f"<li>La tipología más numerosa es <b>{grande[0]}</b> ({grande[1]} municipios).</li>"
              f"<li>Los perfiles permiten diseñar <b>paquetes de política diferenciados</b>.</li>"
              f"<li>Variables anuales promediadas en {a0}–{a1} y cortes censales 2018; {len(vars_)} variables{' (log en las asimétricas)' if transf else ''}.</li></ul>")
    if hay_seleccion(sel):
        lab_mun = dict(zip(cs.municipio, lab))
        items = []
        for mm in sel[:MAX_DETALLE]:
            c = lab_mun.get(mm)
            if c is None:
                continue
            pares = [x for x in cs.municipio[lab == c] if x != mm]
            items.append(f"<b>{mm}</b> pertenece a <b>{nombres_c[c]}</b> ({int((lab == c).sum())} municipios)"
                         + (f"; se parece a: {', '.join(pares[:5])}{'…' if len(pares) > 5 else ''}." if pares else "."))
        if len(sel) > MAX_DETALLE:
            cnt = pd.Series([nombres_c[lab_mun[mm]] for mm in sel if mm in lab_mun]).value_counts()
            items.append(f"Los {len(sel)} municipios de su selección se reparten así: " + "; ".join(f"{t}: {n}" for t, n in cnt.items()) + ".")
        cuerpo += bloque_sel("Su selección en las tipologías", items)
    html_n = callout("Tipologías para focalizar la política pública", cuerpo, "info", "🧩")
    tec = (f'<div class="tec"><h5>Comparación de algoritmos</h5>{tabla_html(dfm, decs={"Clústeres": 0, "Ruido": 0, "Silhouette ↑": 3, "Calinski-Harabasz ↑": 1, "Davies-Bouldin ↓": 3})}'
           f'<p>Variables estandarizadas. Transformaciones: {", ".join(f"{nombre(a)}: {b}" for a, b in transf.items()) or "ninguna"}. '
           f'K-Means con 25 inicializaciones; Ward; DBSCAN con ε = {eps} y mínimo 3 vecinos.</p></div>')
    try:
        Lk = sch.linkage(Z, "ward")
        f_den = ff.create_dendrogram(Z, labels=cs.municipio.tolist(), linkagefun=lambda x: sch.linkage(x, "ward"),
                                     color_threshold=sorted(Lk[:, 2])[-(k - 1)])
        f_den.update_layout(title="Dendrograma jerárquico (Ward)", height=480, margin=dict(l=50, r=20, t=60, b=150), showlegend=False)
        f_den.update_xaxes(tickangle=-60, tickfont=dict(size=9))
    except Exception:
        f_den = fig_vacia("Dendrograma no disponible")
    return html_n, f_pca, f_sil, f_perf, f_map, tec, tabla, f_den


# -----------------------------------------------------------------------------
# 19. PESTAÑA 5 · SÍNTESIS DIMENSIONAL (PCA) E ÍNDICE SINTÉTICO MUNICIPAL
# -----------------------------------------------------------------------------
VARS_PCA = ["ipm", "priv_bajo_logro", "priv_sin_agua", "priv_excretas", "priv_trab_informal", "va_pc", "cobertura_neta",
            "desercion", "tasa_homicidios", "coca_pct", "rec_propios", "idf"]


@blindado(["html", "fig", "fig", "fig", "fig", "fig", "html"])
def tab5_run(subs, muns, a0, a1, vars_):
    a0, a1 = rango(a0, a1)
    vars_ = list(vars_ or VARS_PCA)
    if len(vars_) < 3:
        raise ValueError("Seleccione al menos 3 variables")
    sel = municipios_sel(subs, muns)
    cs, X, _, transf = matriz_estandarizada(a0, a1, vars_, True)
    Xo = X.copy()
    for c in vars_:
        Xo[c] = Xo[c] * (META[c]["sentido"] or 1)
    Z = StandardScaler().fit_transform(Xo.values)
    p = len(vars_)
    pca = PCA().fit(Z)
    ev = pca.explained_variance_
    evr = pca.explained_variance_ratio_
    nk = max(1, int((ev > 1).sum()))
    comps_ = pca.components_.copy()
    for j in range(p):
        if comps_[j].sum() < 0:
            comps_[j] *= -1
    cargas = comps_.T * np.sqrt(ev)
    scores = Z @ comps_.T
    idx_raw = (scores[:, :nk] * evr[:nk]).sum(1) / evr[:nk].sum()
    indice = (idx_raw - idx_raw.min()) / (idx_raw.max() - idx_raw.min()) * 100
    cs = cs.assign(indice=indice)
    comps = [f"CP{i + 1}" for i in range(p)]
    f_scree = make_subplots(specs=[[{"secondary_y": True}]])
    f_scree.add_bar(x=comps, y=ev, name="Autovalor", marker_color=[C["azul"] if e > 1 else "#cbd5e1" for e in ev],
                    customdata=evr * 100, hovertemplate="%{x}<br>Autovalor: %{y:.3f}<br>Varianza: %{customdata:.1f} %<extra></extra>")
    f_scree.add_scatter(x=comps, y=np.cumsum(evr) * 100, name="Varianza acumulada (%)", mode="lines+markers",
                        line=dict(color=C["ambar"], width=2.5), hovertemplate="%{x}<br>Acumulada: %{y:.1f} %<extra></extra>", secondary_y=True)
    f_scree.add_hline(y=1, line=dict(color=C["rojo"], dash="dash", width=2), annotation_text="Criterio de Kaiser (autovalor = 1)",
                      annotation_position="top right", annotation_font=dict(color=C["rojo"], size=11))
    f_scree.update_layout(title=f"Gráfico de sedimentación<br><sup>{nk} componente(s) con autovalor > 1 explican {fnum(evr[:nk].sum() * 100, 1)} % de la varianza</sup>", height=450)
    f_scree.update_yaxes(title_text="autovalor", secondary_y=False)
    f_scree.update_yaxes(ticksuffix=" %", range=[0, 105], showgrid=False, title_text="acumulada", secondary_y=True)
    ncol = min(p, 5)
    f_load = go.Figure(go.Heatmap(z=cargas[:, :ncol], x=comps[:ncol], y=[nombre(v)[:36] for v in vars_], colorscale=ESCALA_DIV, zmid=0, zmin=-1, zmax=1,
                                  text=np.round(cargas[:, :ncol], 2), texttemplate="%{text:.2f}",
                                  hovertemplate="%{y}<br>%{x}: carga %{z:.3f}<extra></extra>", colorbar=dict(title="carga", thickness=12)))
    f_load.update_layout(title="Matriz de cargas factoriales<br><sup>correlación variable–componente · variables orientadas (+ = mejor)</sup>", height=480,
                         margin=dict(l=260, r=30, t=70, b=50))
    f_bi = go.Figure()
    for sb in SUBREGIONES:
        msk = (cs.subregion == sb).values
        f_bi.add_trace(go.Scatter(x=scores[msk, 0], y=scores[msk, 1], mode="markers", name=sb, text=cs.municipio[msk],
                                  marker=dict(size=10, color=COLOR_SUB[sb], line=dict(color="white", width=1)),
                                  hovertemplate="<b>%{text}</b><br>CP1: %{x:.2f}<br>CP2: %{y:.2f}<extra></extra>"))
    esc = np.abs(scores[:, :2]).max() * 0.9
    for j, v in enumerate(vars_):
        f_bi.add_annotation(x=comps_[0, j] * esc, y=comps_[1, j] * esc, ax=0, ay=0, xref="x", yref="y", axref="x", ayref="y",
                            showarrow=True, arrowhead=2, arrowwidth=1.6, arrowcolor="#475569")
        f_bi.add_annotation(x=comps_[0, j] * esc * 1.13, y=comps_[1, j] * esc * 1.13, text=nombre(v).split("(")[0][:22],
                            showarrow=False, font=dict(size=10, color="#334155"))
    f_bi.update_layout(title="Biplot: municipios y vectores de cargas en el plano CP1–CP2", height=540,
                       legend=dict(orientation="v", x=1.01, y=1, xanchor="left", yanchor="top"))
    f_bi.update_xaxes(title_text=f"CP1 ({fnum(evr[0] * 100, 1)} %)")
    f_bi.update_yaxes(title_text=f"CP2 ({fnum(evr[1] * 100, 1)} %)")
    cr = cs.sort_values("indice")
    f_rank = go.Figure(go.Bar(x=cr.indice, y=cr.municipio, orientation="h",
                              marker=dict(color=cr.indice, colorscale=ESCALA_SEMAFORO, cmin=0, cmax=100,
                                          line=dict(width=[2 if mm in sel and len(sel) < 64 else 0 for mm in cr.municipio], color=C["navy"])),
                              customdata=cr.subregion, hovertemplate="<b>%{y}</b> · %{customdata}<br>Índice: %{x:.1f} / 100<extra></extra>"))
    f_rank.update_layout(title="Índice Sintético de Desarrollo Territorial (0 = menor, 100 = mayor desarrollo relativo)", height=1120,
                         margin=dict(l=160, r=30, t=60, b=40))
    f_rank.update_yaxes(tickfont=dict(size=10))
    f_rank.update_xaxes(range=[0, 100])
    cs_o = cs.set_index("codigo").loc[CODIGOS]
    textos = [f"<b>{mm}</b> · {sb}<br>Índice sintético: {fnum(v, 1)} / 100" for mm, sb, v in zip(cs_o.municipio, cs_o.subregion, cs_o.indice)]
    f_map = mapa_municipal(cs_o.indice.values, "Mapa del Índice Sintético de Desarrollo Territorial (0–100)", ESCALA_SEMAFORO,
                           textos=textos, resaltar=sel if len(sel) < 64 else None, cbar_title="0–100")
    R = np.corrcoef(Z.T)
    n = len(Z)
    chi = -(n - 1 - (2 * p + 5) / 6) * np.log(np.linalg.det(R))
    gl = p * (p - 1) / 2
    p_b = 1 - sps.chi2.cdf(chi, gl)
    Ri = np.linalg.pinv(R)
    Pm = -Ri / np.sqrt(np.outer(np.diag(Ri), np.diag(Ri)))
    np.fill_diagonal(Pm, 0)
    R0 = R.copy()
    np.fill_diagonal(R0, 0)
    kmo = (R0 ** 2).sum() / ((R0 ** 2).sum() + (Pm ** 2).sum())
    top = cs.sort_values("indice", ascending=False)
    sub_idx = cs.groupby("subregion").indice.mean().sort_values()
    carga_top = sorted(zip(vars_, cargas[:, 0]), key=lambda t: -abs(t[1]))[:3]
    cuerpo = (f"<p>El análisis resume <b>{p} indicadores</b> en <b>{nk} componente(s)</b> que conservan el <b>{fnum(evr[:nk].sum() * 100, 1)} %</b> "
              f"de la información. El primer componente se asocia sobre todo a: {', '.join(minus(nombre(v)) for v, _ in carga_top)}.</p><ul>"
              f"<li>Mayor desarrollo relativo: <b>{', '.join(top.municipio.head(3))}</b>.</li>"
              f"<li>Menor desarrollo relativo: <b>{', '.join(top.municipio.tail(3)[::-1])}</b>.</li>"
              f"<li>Subregión más rezagada: <b>{sub_idx.index[0]}</b> ({fnum(sub_idx.iloc[0], 1)}/100); más avanzada: <b>{sub_idx.index[-1]}</b> ({fnum(sub_idx.iloc[-1], 1)}/100).</li>"
              f"<li>Adecuación muestral: KMO = {fnum(kmo, 3)} ({'aceptable' if kmo >= 0.6 else 'mediocre' if kmo >= 0.5 else 'insuficiente'}); "
              f"Bartlett p {'< 0,001' if p_b < 0.001 else '= ' + fnum(p_b, 3)}.</li></ul>")
    if hay_seleccion(sel):
        rk = cs.set_index("municipio").indice.rank(ascending=False, method="min")
        idx_m = cs.set_index("municipio").indice
        items = []
        if len(sel) > 1:
            items.append(f"Promedio simple del índice en su selección: <b>{fnum(idx_m.reindex(sel).mean(), 1)}/100</b> "
                         f"(mediana de Nariño: {fnum(idx_m.median(), 1)}/100).")
        for mm in sel[:MAX_DETALLE]:
            items.append(f"<b>{mm}</b> ({MUN_A_SUB[mm]}): índice <b>{fnum(idx_m[mm], 1)}/100</b> · puesto {int(rk[mm])} de {len(rk)} "
                         f"(1 = mayor desarrollo relativo) · {'por encima' if idx_m[mm] > idx_m.median() else 'por debajo'} de la mediana.")
        if len(sel) > MAX_DETALLE:
            items.append(f"… y {len(sel) - MAX_DETALLE} municipios más (resaltados en el ranking y el mapa).")
        cuerpo += bloque_sel("Su selección en el índice", items)
    html_n = callout("Un solo número para comparar el desarrollo municipal", cuerpo, "info", "📉")
    eig = pd.DataFrame({"Componente": comps, "Autovalor": ev, "% varianza": evr * 100, "% acumulado": np.cumsum(evr) * 100})
    carg = pd.DataFrame(cargas[:, :ncol], columns=comps[:ncol]).assign(Variable=[nombre(v) for v in vars_])[["Variable"] + comps[:ncol]]
    tec = (f'<div class="tec"><h5>Autovalores</h5>{tabla_html(eig, decs={"Autovalor": 3, "% varianza": 2, "% acumulado": 2})}'
           f'<h5>Cargas factoriales</h5>{tabla_html(carg)}'
           f'<h5>Pruebas de adecuación</h5><p>Bartlett: χ² = {fnum(chi, 2)}, gl = {int(gl)}, p = {fnum(p_b, 5)} · KMO = {fnum(kmo, 3)}. '
           f'Variables orientadas (alto = mejor); índice = promedio de componentes con autovalor > 1 ponderado por su varianza explicada, reescalado 0–100. '
           f'Faltantes puntuales se completan con la mediana departamental antes de estandarizar.</p></div>')
    return html_n, f_scree, f_load, f_bi, f_rank, f_map, tec




# -----------------------------------------------------------------------------
# 20. PESTAÑA 6 · MODELACIÓN CAUSAL, REGULARIZACIÓN Y DIAGNÓSTICO DE RESIDUOS
# -----------------------------------------------------------------------------
FEATS_ML = ["va_pc", "cobertura_neta", "desercion", "tasa_homicidios", "coca_pct", "dep_transf", "rec_propios", "idf", "partos_inst"]
MODELOS_NOM = ["MCO", "Ridge (L2)", "Lasso (L1)", "ElasticNet", "SVR (RBF)", "Random Forest"]


def datos_modelo(a0, a1, target, feats):
    feats = [f for f in feats if f != target]
    if META[target]["corte"] == "censal":
        d = corte_transversal(a0, a1, [target] + feats).dropna(subset=[target])
        d[feats] = d[feats].fillna(d[feats].median())
        return d, feats, "transversal"
    d = PANEL[(PANEL.anio >= a0) & (PANEL.anio <= a1)][["codigo", "municipio", "anio", target] + [f for f in feats if META[f]["corte"] != "censal"]]
    cens = [f for f in feats if META[f]["corte"] == "censal"]
    if cens:
        d = d.merge(CS[["codigo"] + cens], on="codigo", how="left")
    d = d.dropna(subset=[target] + feats)
    return d, feats, "panel"


def construir_modelos():
    alphas = np.logspace(-3, 3, 40)
    return {
        "MCO": make_pipeline(StandardScaler(), LinearRegression()),
        "Ridge (L2)": make_pipeline(StandardScaler(), RidgeCV(alphas=alphas)),
        "Lasso (L1)": make_pipeline(StandardScaler(), LassoCV(cv=5, random_state=0, max_iter=50000)),
        "ElasticNet": make_pipeline(StandardScaler(), ElasticNetCV(l1_ratio=[0.1, 0.5, 0.9], cv=5, random_state=0, max_iter=50000)),
        "SVR (RBF)": TransformedTargetRegressor(regressor=make_pipeline(StandardScaler(), SVR(C=10, epsilon=0.1)), transformer=StandardScaler()),
        "Random Forest": RandomForestRegressor(n_estimators=300, min_samples_leaf=3, random_state=0, n_jobs=-1),
    }


@blindado(["html", "html", "fig", "fig", "fig", "fig", "html"])
def tab6_run(subs, muns, a0, a1, target, feats, modelo_graf):
    a0, a1 = rango(a0, a1)
    feats = list(feats or FEATS_ML)
    d, feats, modo = datos_modelo(a0, a1, target, feats)
    if len(feats) < 2:
        raise ValueError("Seleccione al menos 2 factores distintos de la variable objetivo")
    if len(d) < 30:
        raise ValueError(f"solo {len(d)} observaciones completas en {a0}-{a1}; amplíe el periodo")
    X, y = d[feats].values.astype(float), d[target].values.astype(float)
    grupos = d["codigo"].values
    cv = GroupKFold(n_splits=5) if modo == "panel" else KFold(n_splits=5, shuffle=True, random_state=0)
    kw = dict(groups=grupos) if modo == "panel" else {}
    modelos = construir_modelos()
    filas, oof, coefs = [], {}, {}
    for nm, mod in modelos.items():
        pr = cross_val_predict(mod, X, y, cv=cv, **kw)
        oof[nm] = pr
        sc = cross_val_score(mod, X, y, cv=cv, scoring="r2", **kw)
        filas.append([nm, np.sqrt(mean_squared_error(y, pr)), mean_absolute_error(y, pr), r2_score(y, pr), sc.mean(), sc.std()])
        if nm in ("MCO", "Ridge (L2)", "Lasso (L1)", "ElasticNet"):
            coefs[nm] = mod.fit(X, y)[-1].coef_
    met = pd.DataFrame(filas, columns=["Modelo", "RMSE", "MAE", "R² fuera de muestra", "R² CV (media)", "R² CV (desv.)"]).sort_values("R² fuera de muestra", ascending=False)
    mejor = met.iloc[0]["Modelo"]
    mg = mejor if modelo_graf == "Mejor modelo" else modelo_graf
    m = META[target]
    sub_v = np.array([MUN_A_SUB[x] for x in d.municipio])
    f_rp = go.Figure()
    for sb in SUBREGIONES:
        msk = sub_v == sb
        if msk.any():
            f_rp.add_trace(go.Scatter(x=y[msk], y=oof[mg][msk], mode="markers", name=sb, text=d.municipio.values[msk],
                                      marker=dict(size=8 if modo == "panel" else 11, color=COLOR_SUB[sb], opacity=0.85, line=dict(color="white", width=0.6)),
                                      hovertemplate="<b>%{text}</b><br>Real: %{x:,.2f}<br>Predicho (fuera de muestra): %{y:,.2f}<extra></extra>"))
    sel = municipios_sel(subs, muns)
    if hay_seleccion(sel):
        msk_s = d.municipio.isin(sel).values
        f_rp.add_trace(go.Scatter(x=y[msk_s], y=oof[mg][msk_s], mode="markers+text" if modo == "transversal" and msk_s.sum() <= MAX_DETALLE else "markers",
                                  text=d.municipio.values[msk_s], textposition="top center", textfont=dict(size=11, color=C["navy"]),
                                  marker=dict(symbol="star", size=15 if modo == "transversal" else 11, color="#f59e0b", line=dict(color=C["navy"], width=1.3)),
                                  name="★ Selección", hovertemplate="<b>%{text}</b> (selección)<br>Real: %{x:,.2f}<br>Predicho: %{y:,.2f}<extra></extra>"))
    lim = [min(y.min(), oof[mg].min()), max(y.max(), oof[mg].max())]
    f_rp.add_trace(go.Scatter(x=lim, y=lim, mode="lines", name="Ajuste perfecto (45°)", line=dict(color=C["navy"], dash="dash", width=2), hoverinfo="skip"))
    r2v = met.loc[met.Modelo == mg, "R² fuera de muestra"].iloc[0]
    f_rp.update_layout(title=f"Real vs. predicho · {mg}<br><sup>Predicciones fuera de muestra (validación cruzada {'por municipios' if modo == 'panel' else 'en 5 bloques'}) · R² = {fnum(r2v, 3)}</sup>",
                       height=500, legend=dict(orientation="v", x=1.01, y=1, xanchor="left", yanchor="top"))
    f_rp.update_xaxes(title_text=f"{m['nombre']} observado")
    f_rp.update_yaxes(title_text=f"{m['nombre']} predicho")
    # MCO de referencia con errores robustos
    Xc = sm.add_constant(pd.DataFrame(X, columns=feats))
    if modo == "panel":
        ols = sm.OLS(y, Xc).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(grupos)[0]})
        tipo_ee = "agrupados por municipio"
    else:
        ols = sm.OLS(y, Xc).fit(cov_type="HC3")
        tipo_ee = "robustos HC3"
    ols_nr = sm.OLS(y, Xc).fit()
    fitted, resid = ols_nr.fittedvalues.values, ols_nr.resid.values
    infl = ols_nr.get_influence()
    rstd = infl.resid_studentized_internal
    f_res = go.Figure()
    f_res.add_trace(go.Scatter(x=fitted, y=rstd, mode="markers", text=d.municipio.values,
                               marker=dict(size=7, color=np.abs(rstd), colorscale=[[0, "#93c5fd"], [0.5, C["ambar"]], [1, C["rojo"]]], cmin=0, cmax=3,
                                           line=dict(color="white", width=0.5)),
                               hovertemplate="<b>%{text}</b><br>Ajustado: %{x:,.2f}<br>Residuo estandarizado: %{y:.2f}<extra></extra>", showlegend=False))
    orden = np.argsort(fitted)
    win = max(5, len(fitted) // 10)
    suav = pd.Series(rstd[orden]).rolling(win, center=True, min_periods=3).mean().values
    f_res.add_trace(go.Scatter(x=fitted[orden], y=suav, mode="lines", line=dict(color=C["navy"], width=2.2), name="Media móvil", hoverinfo="skip"))
    for yv, dash in ((0, "solid"), (2, "dot"), (-2, "dot")):
        f_res.add_hline(y=yv, line=dict(color="#94a3b8", dash=dash, width=1))
    bp = het_breuschpagan(resid, Xc)
    f_res.update_layout(title=f"Valores ajustados vs. residuos (MCO)<br><sup>Breusch-Pagan p = {fnum(bp[1], 4)} · {'heterocedasticidad' if bp[1] < 0.05 else 'sin evidencia de heterocedasticidad'}</sup>", height=460)
    f_res.update_xaxes(title_text="valor ajustado")
    f_res.update_yaxes(title_text="residuo estandarizado")
    (osm, osr), (sl, ic, rq) = sps.probplot(rstd, dist="norm")
    n_ = len(osm)
    pp = (np.arange(1, n_ + 1) - 0.5) / n_
    se_q = (1 / sps.norm.pdf(osm)) * np.sqrt(pp * (1 - pp) / n_)
    f_qq = go.Figure()
    f_qq.add_trace(go.Scatter(x=np.r_[osm, osm[::-1]], y=np.r_[sl * osm + ic + 1.96 * se_q, (sl * osm + ic - 1.96 * se_q)[::-1]], mode="lines", fill="toself",
                              fillcolor="rgba(37,99,235,.12)", line=dict(width=0), name="Banda 95 %", hoverinfo="skip"))
    f_qq.add_trace(go.Scatter(x=osm, y=osr, mode="markers", name="Residuos", marker=dict(size=6, color=C["azul"]),
                              hovertemplate="Cuantil teórico: %{x:.2f}<br>Residuo: %{y:.2f}<extra></extra>"))
    f_qq.add_trace(go.Scatter(x=osm, y=sl * osm + ic, mode="lines", name="Referencia normal", line=dict(color=C["rojo"], width=2)))
    jbv = jarque_bera(resid)
    f_qq.update_layout(title=f"Q-Q de normalidad de residuos<br><sup>Jarque-Bera p = {fnum(jbv[1], 4)} · r = {fnum(rq, 3)}</sup>", height=460)
    f_qq.update_xaxes(title_text="cuantiles teóricos N(0,1)")
    f_qq.update_yaxes(title_text="residuos estandarizados")
    # Importancia comparada (normalizada a 100 por modelo)
    imp = {}
    for nm, cf in coefs.items():
        a = np.abs(cf)
        imp[nm] = a / a.sum() * 100 if a.sum() > 0 else a
    gss = (GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=7).split(X, y, grupos) if modo == "panel"
           else KFold(n_splits=4, shuffle=True, random_state=7).split(X))
    tr, te = next(gss)
    rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=3, random_state=0, n_jobs=-1).fit(X[tr], y[tr])
    pi = permutation_importance(rf, X[te], y[te], n_repeats=10, random_state=0, n_jobs=-1).importances_mean
    pi = np.clip(pi, 0, None)
    imp["Random Forest (permutación)"] = pi / pi.sum() * 100 if pi.sum() > 0 else pi
    M = pd.DataFrame(imp, index=[nombre(f).split("(")[0].strip()[:32] for f in feats])
    M = M.loc[M.mean(1).sort_values().index]
    f_imp = go.Figure(go.Heatmap(z=M.values, x=list(M.columns), y=list(M.index), colorscale=ESCALA_AZUL, zmin=0,
                                 text=np.round(M.values, 1), texttemplate="%{text:.1f}",
                                 hovertemplate="%{y}<br>%{x}: %{z:.1f} % de la importancia<extra></extra>", colorbar=dict(title="%", thickness=12)))
    f_imp.update_layout(title="Importancia comparada de variables entre modelos<br><sup>Lineales: |coeficiente estandarizado| · Random Forest: importancia por permutación · normalizado a 100 %</sup>",
                        height=max(420, 40 * len(feats) + 160), margin=dict(l=240, r=30, t=80, b=110))
    f_imp.update_xaxes(tickangle=-20)
    coef_tab = pd.DataFrame({"Variable": ["Constante"] + [nombre(f) for f in feats], "β": ols.params.values, "EE": ols.bse.values,
                             "t": ols.tvalues.values, "p-valor": ols.pvalues.values,
                             "IC 95 % inf.": ols.conf_int()[0].values, "IC 95 % sup.": ols.conf_int()[1].values})
    coef_tab["Sig."] = [p_estrellas(p) for p in coef_tab["p-valor"]]
    signif = coef_tab[(coef_tab["p-valor"] < 0.05) & (coef_tab.Variable != "Constante")].sort_values("t", key=abs, ascending=False)
    lista = "".join(f"<li><b>{r.Variable}</b>: {'aumenta' if r.β > 0 else 'reduce'} {minus(m['nombre'])} "
                    f"({'+' if r.β > 0 else ''}{fnum(r.β, 3)} por unidad; p = {fnum(r['p-valor'], 3)}).</li>" for _, r in signif.head(4).iterrows())
    unidad_obs = "municipios (corte transversal)" if modo == "transversal" else "observaciones municipio-año"
    cuerpo = (f"<p>Se compararon seis modelos para explicar <b>{minus(m['nombre'])}</b> con {len(feats)} factores y {len(d):,} {unidad_obs}. "
              f"El mejor desempeño <b>fuera de muestra</b> es de <b>{mejor}</b> (R² = {fnum(met.iloc[0]['R² fuera de muestra'], 3)}).</p>"
              f"<p>Asociaciones estadísticamente robustas (MCO con errores {tipo_ee}):</p><ul>{lista or '<li>Ningún factor es significativo al 5 %.</li>'}</ul>"
              f"<p class='nota-fuente'>Lectura causal sujeta a exogeneidad; la vista técnica reporta diagnósticos de especificación. {etiqueta_fuente(target)}</p>")
    if hay_seleccion(sel):
        dd_s = pd.DataFrame({"municipio": d.municipio.values, "real": y, "pred": oof[mg]})
        dd_s = dd_s[dd_s.municipio.isin(sel)].groupby("municipio")[["real", "pred"]].mean()
        sm_ = m["sentido"] or 1
        items = []
        for mm in [x for x in sel if x in dd_s.index][:MAX_DETALLE]:
            r_, p_ = dd_s.loc[mm, "real"], dd_s.loc[mm, "pred"]
            gap = (r_ - p_) * sm_
            juicio = ("mejor de lo esperado según sus factores" if gap > 0 else "peor de lo esperado según sus factores") if abs(r_ - p_) > 1e-9 else "en línea con lo esperado"
            items.append(f"<b>{mm}</b>: observado {fmt_val(r_, target)} frente a {fmt_val(p_, target)} predicho por {mg} → <b>{juicio}</b>"
                         f"{' (promedio ' + str(a0) + '–' + str(a1) + ')' if modo == 'panel' else ''}.")
        faltan = [x for x in sel if x not in dd_s.index]
        if faltan and len(items) < MAX_DETALLE:
            items.append(f"Sin observaciones completas para: {', '.join(faltan[:6])}{'…' if len(faltan) > 6 else ''}.")
        if len(sel) > MAX_DETALLE:
            items.append(f"… y {len(sel) - MAX_DETALLE} municipios más (★ en el gráfico real vs. predicho).")
        items.append("El modelo se estima con los 64 municipios: un municipio solo no tiene observaciones suficientes para estimarlo por separado.")
        cuerpo = cuerpo.replace("<p class='nota-fuente'>", bloque_sel("Su selección frente al modelo", items) + "<p class='nota-fuente'>", 1)
    html_n = callout("¿Qué factores explican el indicador?", cuerpo, "info", "🤖")
    try:
        rs = linear_reset(ols_nr, power=3, use_f=True)
        reset = (float(rs.fvalue), float(rs.pvalue))
    except Exception:
        reset = (np.nan, np.nan)
    vif = pd.DataFrame({"Variable": [nombre(f) for f in feats], "VIF": [variance_inflation_factor(Xc.values, i + 1) for i in range(len(feats))]})
    diag = pd.DataFrame([
        ["R² / R² ajustado", f"{fnum(ols.rsquared, 4)} / {fnum(ols.rsquared_adj, 4)}"],
        ["F robusto · p", f"{fnum(float(np.squeeze(ols.fvalue)), 3)} · {fnum(float(np.squeeze(ols.f_pvalue)), 4)}"],
        ["AIC / BIC", f"{fnum(ols.aic, 2)} / {fnum(ols.bic, 2)}"],
        ["Breusch-Pagan (LM · p)", f"{fnum(bp[0], 3)} · {fnum(bp[1], 4)}"],
        ["RESET de Ramsey (F · p)", f"{fnum(reset[0], 3)} · {fnum(reset[1], 4)}"],
        ["Jarque-Bera (JB · p)", f"{fnum(jbv[0], 3)} · {fnum(jbv[1], 4)}"],
        ["Durbin-Watson", fnum(durbin_watson(resid), 3)],
        ["Número de condición", fnum(ols_nr.condition_number, 1)],
    ], columns=["Diagnóstico", "Resultado"])
    V = pd.DataFrame(ols.cov_params().values, columns=["const"] + feats, index=["const"] + feats).round(6)
    V.insert(0, "", V.index)
    tec = (f'<div class="tec"><h5>Desempeño predictivo fuera de muestra</h5>'
           f'{tabla_html(met, decs={"RMSE": 3, "MAE": 3, "R² fuera de muestra": 3, "R² CV (media)": 3, "R² CV (desv.)": 3})}'
           f'<h5>MCO con errores estándar {tipo_ee}</h5>{tabla_html(coef_tab, decs={"β": 4, "EE": 4, "t": 3, "p-valor": 4, "IC 95 % inf.": 4, "IC 95 % sup.": 4})}'
           f'<p>*** p &lt; 0,01 · ** p &lt; 0,05 · * p &lt; 0,10</p><h5>Diagnósticos de especificación</h5>{tabla_html(diag)}'
           f'<h5>Multicolinealidad (VIF)</h5>{tabla_html(vif, decs={"VIF": 2})}'
           f'<h5>Matriz de varianzas-covarianzas de β ({tipo_ee})</h5>{tabla_html(V, decs={c: 6 for c in V.columns})}'
           f'<h5>Salida completa de statsmodels</h5>{mono(ols.summary(xname=["const"] + feats).as_text())}</div>')
    return (html_n, tabla_html(met, decs={"RMSE": 3, "MAE": 3, "R² fuera de muestra": 3, "R² CV (media)": 3, "R² CV (desv.)": 3}),
            f_rp, f_res, f_qq, f_imp, tec)


# -----------------------------------------------------------------------------
# 21. PESTAÑA 7 · ECONOMETRÍA DINÁMICA (ADF · JOHANSEN · VAR/VECM · IRF · FEVD · RAÍCES)
# -----------------------------------------------------------------------------
VARS_VAR_OPC = ["pib", "desempleo", "tgp", "tasa_homicidios_dep", "coca_dep", "inflacion", "idf_mediana", "dep_transf_dep"]


def preparar_series(vars_):
    d = DEPTO.set_index("anio")[list(vars_)].dropna()
    trans = {}
    for v in vars_:
        if META[v].get("log") and (d[v] > 0).all():
            d[v] = np.log(d[v])
            trans[v] = "log"
        else:
            trans[v] = "nivel"
    return d, trans


def adf_tabla(d):
    filas = []
    for v in d.columns:
        for etq, s in (("Nivel", d[v]), ("1.ª diferencia", d[v].diff().dropna())):
            try:
                r = adfuller(s.values, maxlag=2, autolag="AIC", regression="c")
                filas.append([nombre(v), etq, r[0], r[1], r[2], r[4]["5%"], "Estacionaria" if r[1] < 0.05 else "Raíz unitaria"])
            except Exception:
                filas.append([nombre(v), etq, np.nan, np.nan, np.nan, np.nan, "—"])
    return pd.DataFrame(filas, columns=["Serie", "Especificación", "ADF", "p-valor", "Rezagos", "Valor crítico 5 %", "Conclusión"])


def fevd_desde_irf(orth):
    """FEVD a partir de IRF ortogonalizadas: participación de cada choque en la varianza del error a h pasos."""
    H = orth.shape[0]
    acum = np.cumsum(orth ** 2, axis=0)
    tot = acum.sum(axis=2, keepdims=True)
    return acum / np.where(tot == 0, 1, tot)


def bootstrap_vecm(res, datos, rango_c, h, reps=200, seed=3):
    rng = np.random.default_rng(seed)
    T, k = datos.shape
    u = res.resid - res.resid.mean(0)
    alpha, beta, gamma = res.alpha, res.beta, res.gamma
    c = res.det_coef[:, 0] if res.det_coef.size else np.zeros(k)
    sims = []
    for _ in range(reps):
        y = np.zeros((T, k))
        y[:2] = datos[:2]
        e = u[rng.integers(0, len(u), T)]
        for t in range(2, T):
            dy_1 = y[t - 1] - y[t - 2]
            y[t] = y[t - 1] + alpha @ beta.T @ y[t - 1] + gamma @ dy_1 + c + e[t]
        try:
            r = VECM(y, k_ar_diff=1, coint_rank=rango_c, deterministic="co").fit()
            sims.append(r.irf(h).orth_irfs)
        except Exception:
            pass
    if len(sims) < reps * 0.5:
        return None, None
    S = np.array(sims)
    return np.percentile(S, 2.5, axis=0), np.percentile(S, 97.5, axis=0)


@blindado(["html", "fig", "fig", "fig", "fig", "html"])
def tab7_run(vars_, modelo, impulso, respuesta, horizonte, acumulado):
    vars_ = list(vars_ or ["pib", "desempleo", "tasa_homicidios_dep"])
    if len(vars_) < 2 or len(vars_) > 4:
        raise ValueError("Seleccione entre 2 y 4 series")
    impulso = impulso if impulso in vars_ else vars_[-1]
    respuesta = respuesta if respuesta in vars_ else vars_[0]
    h = int(horizonte)
    d, trans = preparar_series(vars_)
    if len(d) < 12:
        raise ValueError(f"solo {len(d)} años comunes entre las series; elija series con mayor cobertura")
    adf = adf_tabla(d)
    jo = coint_johansen(d.values, det_order=0, k_ar_diff=1)
    rango_c = 0
    for i in range(len(vars_)):
        if jo.lr1[i] > jo.cvt[i, 1]:
            rango_c = i + 1
        else:
            break
    usar = modelo
    if modelo == "Automático":
        usar = "VECM" if 0 < rango_c < len(vars_) else "VAR en diferencias"
    rango_c = min(max(rango_c, 1), len(vars_) - 1) if usar == "VECM" else rango_c
    lo = hi = None
    extra = ""
    if usar == "VECM":
        res = VECM(d.values, k_ar_diff=1, coint_rank=rango_c, deterministic="co").fit()
        irf = res.irf(h)
        orth = irf.orth_irfs
        resp = np.cumsum(orth, axis=0) if acumulado else orth
        lo, hi = bootstrap_vecm(res, d.values, rango_c, h)
        if lo is not None and acumulado:
            lo, hi = None, None
        A = res.var_rep
        p_, kk = A.shape[0], A.shape[1]
        comp = np.zeros((kk * p_, kk * p_))
        comp[:kk, :] = np.hstack(list(A))
        if p_ > 1:
            comp[kk:, :-kk] = np.eye(kk * (p_ - 1))
        inv_roots = np.linalg.eigvals(comp)
        resumen = res.summary().as_text()
        unidad_irf = "desvío en niveles (log o puntos)"
        nota_raices = f"En un VECM con rango {rango_c}, {len(vars_) - rango_c} raíz(es) igual(es) a 1 son esperadas (tendencias estocásticas comunes)."
        ic_txt = "Bandas al 95 % por bootstrap de residuos (200 réplicas)." if lo is not None else "Bandas no disponibles para esta especificación."
    else:
        dd = d.diff().dropna()
        for v in vars_:
            if trans[v] == "log":
                dd[v] = dd[v] * 100
        sel = VAR(dd.values).select_order(maxlags=2)
        p_ = max(1, int(sel.selected_orders.get("aic") or 1))
        res = VAR(dd.values).fit(p_)
        irf = res.irf(h)
        orth = irf.orth_irfs
        if acumulado:
            resp = irf.orth_cum_effects
            try:
                se = irf.cum_effect_stderr(orth=True)
            except Exception:
                se = None
        else:
            resp = orth
            se = irf.stderr(orth=True)
        if se is not None:
            lo, hi = resp - 1.96 * se, resp + 1.96 * se
        inv_roots = 1 / res.roots if len(res.roots) else np.array([])
        resumen = str(res.summary())
        unidad_irf = "puntos de variación anual" if not acumulado else "efecto acumulado (≈ % en niveles)"
        nota_raices = f"Sistema {'estable' if res.is_stable() else 'NO estable'}: todas las raíces inversas deben quedar dentro del círculo unitario."
        ic_txt = "Bandas al 95 % analíticas (asintóticas, Lütkepohl)."
        try:
            wt = res.test_whiteness(nlags=max(p_ + 2, 4))
            nt = res.test_normality()
            extra = (f"<p>Portmanteau: {fnum(wt.test_statistic, 3)}, p = {fnum(wt.pvalue, 4)} · Jarque-Bera multivariado: "
                     f"{fnum(nt.test_statistic, 3)}, p = {fnum(nt.pvalue, 4)} · Rezagos (AIC): {p_}</p>")
            gc = []
            for a in range(len(vars_)):
                for b in range(len(vars_)):
                    if a != b:
                        t_ = res.test_causality(b, [a], kind="f")
                        gc.append([nombre(vars_[a]), nombre(vars_[b]), t_.test_statistic, t_.pvalue, "Sí" if t_.pvalue < 0.05 else "No"])
            extra += "<h5>Causalidad de Granger</h5>" + tabla_html(pd.DataFrame(gc, columns=["Causa", "Efecto", "F", "p-valor", "¿Causa? (5 %)"]),
                                                                   decs={"F": 3, "p-valor": 4})
        except Exception:
            pass
    ii, jj = vars_.index(impulso), vars_.index(respuesta)
    x = np.arange(h + 1)
    y_ = resp[:, jj, ii]
    f_irf = go.Figure()
    if lo is not None:
        f_irf.add_trace(go.Scatter(x=np.r_[x, x[::-1]], y=np.r_[hi[:, jj, ii], lo[:, jj, ii][::-1]], mode="lines", fill="toself",
                                   fillcolor="rgba(37,99,235,.15)", line=dict(width=0), name="Intervalo de confianza 95 %", hoverinfo="skip"))
    f_irf.add_trace(go.Scatter(x=x, y=y_, mode="lines+markers", name="Respuesta (OIRF)", line=dict(color=C["azul"], width=3),
                               marker=dict(size=7), hovertemplate="Año %{x} tras el choque<br>Respuesta: %{y:.4f}<extra></extra>"))
    f_irf.add_hline(y=0, line=dict(color="#94a3b8", width=1.2))
    f_irf.update_layout(title=f"Impulso-respuesta ortogonalizada ({usar})<br><sup>Choque de 1 desv. est. en {minus(nombre(impulso))} → {minus(nombre(respuesta))} · {ic_txt}</sup>", height=470)
    f_irf.update_xaxes(title_text="Años después del choque", dtick=1)
    f_irf.update_yaxes(title_text=unidad_irf)
    # FEVD
    fe = fevd_desde_irf(orth)[: min(10, h + 1)]
    f_fe = go.Figure()
    pal = ["#1e3a8a", "#10b981", "#f59e0b", "#ef4444"]
    for kx, v in enumerate(vars_):
        f_fe.add_trace(go.Scatter(x=np.arange(1, len(fe) + 1), y=fe[:, jj, kx] * 100, mode="lines", stackgroup="uno", name=f"Choque: {nombre(v)}",
                                  line=dict(width=0.5, color=pal[kx]), hovertemplate=f"h = %{{x}}<br>{nombre(v)}: %{{y:.1f}} %<extra></extra>"))
    f_fe.update_layout(title=f"FEVD: {minus(nombre(respuesta))}<br><sup>% de la varianza del error de pronóstico por choque ortogonal · h = 1 a {len(fe)}</sup>", height=440)
    f_fe.update_xaxes(title_text="horizonte (años)", dtick=1)
    f_fe.update_yaxes(title_text="% de la varianza", range=[0, 100], ticksuffix=" %")
    # Raíces inversas
    th = np.linspace(0, 2 * np.pi, 200)
    f_ro = go.Figure()
    f_ro.add_trace(go.Scatter(x=np.cos(th), y=np.sin(th), mode="lines", line=dict(color="#94a3b8", width=1.5), name="Círculo unitario", hoverinfo="skip"))
    if len(inv_roots):
        mod_ = np.abs(inv_roots)
        f_ro.add_trace(go.Scatter(x=inv_roots.real, y=inv_roots.imag, mode="markers", name="Raíces inversas",
                                  marker=dict(size=12, color=[C["rojo"] if mm > 1.0001 else (C["ambar"] if mm > 0.9999 else C["verde"]) for mm in mod_],
                                              line=dict(color="white", width=1.5)),
                                  customdata=mod_, hovertemplate="Re: %{x:.3f}<br>Im: %{y:.3f}<br>Módulo: %{customdata:.4f}<extra></extra>"))
    f_ro.update_layout(title=f"Raíces inversas del polinomio autorregresivo<br><sup>{nota_raices}</sup>", height=440,
                       xaxis=dict(range=[-1.3, 1.3], zeroline=True, title_text="parte real"),
                       yaxis=dict(range=[-1.3, 1.3], scaleanchor="x", scaleratio=1, zeroline=True, title_text="parte imaginaria"))
    # Series
    k_ = len(vars_)
    f_s = make_subplots(rows=1, cols=k_, subplot_titles=[nombre(v)[:38] for v in vars_], horizontal_spacing=0.06)
    for i, v in enumerate(vars_):
        s = DEPTO[["anio", v]].dropna()
        f_s.add_trace(go.Scatter(x=s.anio, y=s[v], mode="lines+markers", line=dict(color=pal[i], width=2.5), marker=dict(size=4),
                                 name=nombre(v), showlegend=False, hovertemplate=f"<b>Nariño</b><br>Año: %{{x}}<br>{nombre(v)}: %{{y:,.2f}}<extra></extra>"),
                      row=1, col=i + 1)
        eje(f_s, v, "y", row=1, col=i + 1, titulo=False)
    f_s.update_layout(title=f"Series departamentales (muestra común {int(d.index.min())}–{int(d.index.max())}, {len(d)} años)", height=400)
    f_s.update_annotations(font=dict(size=12, color=C["navy"]))
    pico = int(np.argmax(np.abs(y_)))
    sig_txt = ""
    if lo is not None:
        sig_pts = np.where((lo[:, jj, ii] > 0) | (hi[:, jj, ii] < 0))[0]
        sig_txt = (f" La respuesta es estadísticamente distinta de cero en {len(sig_pts)} de {h + 1} horizontes."
                   if len(sig_pts) else " La banda de confianza contiene el cero en todos los horizontes: efecto no concluyente.")
    no_est = adf[(adf.Especificación == "Nivel") & (adf.Conclusión == "Raíz unitaria")].Serie.tolist()
    fe_h = fe[-1, jj] * 100
    dom = vars_[int(np.argmax(fe_h))]
    cuerpo = (f"<p>Ante un choque inesperado en <b>{minus(nombre(impulso))}</b>, <b>{minus(nombre(respuesta))}</b> reacciona de forma "
              f"<b>{'positiva' if y_[pico] > 0 else 'negativa'}</b>, con su máximo {pico} año(s) después.{sig_txt}</p><ul>"
              f"<li>A {len(fe)} años, el <b>{fnum(fe_h.max(), 1)} %</b> de la incertidumbre de {minus(nombre(respuesta))} se explica por choques en {minus(nombre(dom))}.</li>"
              f"<li>ADF: {len(no_est)} de {len(vars_)} series con raíz unitaria en niveles ({', '.join(no_est) or 'ninguna'}). Johansen: rango <b>{rango_c}</b> al 5 %.</li>"
              f"<li>Modelo: <b>{usar}</b> con {len(d)} años ({int(d.index.min())}–{int(d.index.max())}).</li></ul>"
              f"<p class='nota-fuente'>Muestras anuales cortas: resultados indicativos. {' '.join(sorted({etiqueta_fuente(v).split(' · ')[0] for v in vars_}))}</p>")
    html_n = callout("¿Cómo se transmiten los choques en la economía de Nariño?", cuerpo, "info", "📈")
    jt = pd.DataFrame({"H0: rango ≤": list(range(len(vars_))), "Traza": jo.lr1, "Crítico 90 %": jo.cvt[:, 0], "Crítico 95 %": jo.cvt[:, 1],
                       "Crítico 99 %": jo.cvt[:, 2], "Máx. autovalor": jo.lr2, "Crítico 95 % (máx.)": jo.cvm[:, 1]})
    jt["Rechaza H0 (5 %)"] = np.where(jt["Traza"] > jt["Crítico 95 %"], "Sí", "No")
    fe_tab = pd.DataFrame(fe[:, jj] * 100, columns=[f"Choque {nombre(v)}" for v in vars_])
    fe_tab.insert(0, "h", np.arange(1, len(fe) + 1))
    tec = (f'<div class="tec"><h5>Dickey-Fuller aumentada</h5>{tabla_html(adf, decs={"ADF": 3, "p-valor": 4, "Rezagos": 0, "Valor crítico 5 %": 3})}'
           f'<h5>Cointegración de Johansen (constante, 1 rezago en diferencias)</h5>{tabla_html(jt, decs={"H0: rango ≤": 0})}'
           f'<h5>FEVD de {nombre(respuesta)} (%)</h5>{tabla_html(fe_tab, decs={"h": 0})}'
           f'<p>Transformaciones: {", ".join(f"{nombre(k)}: {v}" for k, v in trans.items())}. Cholesky en el orden: {" → ".join(nombre(v) for v in vars_)}.</p>'
           f'{extra}<h5>Resultados de estimación</h5>{mono(resumen)}</div>')
    return html_n, f_s, f_irf, f_fe, f_ro, tec


# -----------------------------------------------------------------------------
# 22. PESTAÑA 8 · PRONÓSTICO DE TENDENCIAS (ARIMA / ETS, 5 AÑOS, IC 95 %)
# -----------------------------------------------------------------------------
TERR_NARINO = "Nariño (departamento)"
SERIES_PRON_DEP = ["pib", "pib_pc", "desempleo", "tgp", "inflacion", "tasa_homicidios_dep", "coca_dep", "cobertura_dep", "idf_mediana", "dep_transf_dep", "recursos_dnp"]


def serie_pronostico(territorio, ind):
    if territorio == TERR_NARINO:
        s = DEPTO[["anio", ind]].dropna()
    else:
        s = PANEL[PANEL.municipio == territorio][["anio", ind]].dropna()
    return s.anio.values.astype(int), s[ind].values.astype(float)


def ajustar_arima(y):
    mejor = None
    for p_ in range(3):
        for d_ in range(2):
            for q_ in range(3):
                try:
                    tr_ = "c" if d_ == 0 else "t"
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        r = SARIMAX(y, order=(p_, d_, q_), trend=tr_, enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
                    if np.isfinite(r.aic) and (mejor is None or r.aic < mejor[0]):
                        mejor = (r.aic, (p_, d_, q_), tr_, r)
                except Exception:
                    pass
    if mejor is None:
        raise ValueError("ningún ARIMA convergió")
    return mejor


def pronosticar(y, modelo, h):
    if modelo.startswith("ARIMA"):
        aic, orden, tr_, r = ajustar_arima(y)
        fc = r.get_forecast(h)
        ci = np.asarray(fc.conf_int(alpha=0.05))
        return np.asarray(fc.predicted_mean), ci[:, 0], ci[:, 1], np.asarray(r.fittedvalues), r, f"ARIMA{orden} con {'constante' if tr_ == 'c' else 'deriva'} (AIC = {fnum(aic, 2)})"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = ETSModel(pd.Series(y, index=pd.RangeIndex(len(y))), error="add", trend="add", damped_trend=True).fit(disp=False, maxiter=2000)
    pr = r.get_prediction(start=len(y), end=len(y) + h - 1).summary_frame(alpha=0.05)
    return pr["mean"].values, pr["pi_lower"].values, pr["pi_upper"].values, np.asarray(r.fittedvalues), r, f"ETS(A, Ad, N) amortiguado (AIC = {fnum(r.aic, 2)})"


@blindado(["html", "fig", "html", "html"])
def tab8_run(territorio, ind, modelo):
    anios, y = serie_pronostico(territorio, ind)
    if len(y) < 8:
        raise ValueError(f"la serie tiene solo {len(y)} observaciones (mínimo 8)")
    h = 5
    m = META[ind]
    media, lo, hi, ajuste, res, desc = pronosticar(y, modelo, h)
    if m["tipo"] in ("pct", "ha", "cop") or ind.startswith("tasa") or ind in ("coca_dep", "pib"):
        lo, media = np.clip(lo, 0, None), np.clip(media, 0, None)
    if m["tipo"] == "pct" and ind not in ("crecimiento_pib",) and ind != "cobertura_neta" and ind != "cobertura_dep":
        hi, media = np.clip(hi, None, 100), np.clip(media, None, 100)
    fut = np.arange(anios[-1] + 1, anios[-1] + h + 1)
    f = go.Figure()
    f.add_trace(go.Scatter(x=np.r_[fut, fut[::-1]], y=np.r_[hi, lo[::-1]], mode="lines", fill="toself", fillcolor="rgba(37,99,235,.14)",
                           line=dict(width=0), name="Intervalo de predicción 95 %", hoverinfo="skip"))
    var_h = [variacion_txt(p, c, ind) for p, c in zip(np.r_[np.nan, y[:-1]], y)]
    f.add_trace(go.Scatter(x=anios, y=y, mode="lines+markers", name="Observado (oficial)", line=dict(color=C["navy"], width=2.8), marker=dict(size=6),
                           customdata=np.column_stack([[territorio] * len(y), var_h]),
                           hovertemplate=f"<b>%{{customdata[0]}}</b><br>Año: %{{x}}<br>{m['nombre']}: %{{y:,.{m['dec']}f}}<br>Variación: %{{customdata[1]}}<extra></extra>"))
    f.add_trace(go.Scatter(x=anios[1:], y=ajuste[1:], mode="lines", name="Ajuste del modelo", line=dict(color="#94a3b8", width=1.6, dash="dot"), hoverinfo="skip"))
    var_f = [variacion_txt(p, c, ind) for p, c in zip(np.r_[y[-1], media[:-1]], media)]
    f.add_trace(go.Scatter(x=np.r_[anios[-1], fut], y=np.r_[y[-1], media], mode="lines+markers", name="Pronóstico central",
                           line=dict(color=C["azul2"], width=3, dash="dash"), marker=dict(size=7, symbol="diamond"),
                           customdata=np.column_stack([np.array([""] + var_f, dtype=object), np.r_[y[-1], lo], np.r_[y[-1], hi]]),
                           hovertemplate=f"Año: %{{x}}<br>Pronóstico: %{{y:,.{m['dec']}f}}<br>IC 95 %: %{{customdata[1]:,.{m['dec']}f}} – %{{customdata[2]:,.{m['dec']}f}}<br>Variación: %{{customdata[0]}}<extra></extra>"))
    f.add_vrect(x0=anios[-1] + 0.5, x1=fut[-1] + 0.5, fillcolor="#eff6ff", opacity=0.5, line_width=0, layer="below",
                annotation_text="Horizonte de pronóstico", annotation_position="top left", annotation_font=dict(size=11, color=C["azul"]))
    f.update_layout(title=f"{m['nombre']} · {territorio}: proyección {fut[0]}–{fut[-1]}", height=500, hovermode="x unified")
    eje(f, ind, "y")
    f.update_xaxes(dtick=2)
    try:
        mb = pronosticar(y[:-3], modelo, 3)[0]
        mape = np.nanmean(np.abs((y[-3:] - mb) / np.where(y[-3:] == 0, np.nan, y[-3:]))) * 100
    except Exception:
        mape = np.nan
    try:
        lb = acorr_ljungbox(np.asarray(res.resid)[1:], lags=[min(4, len(y) // 3)], return_df=True)
        lb_p = float(lb["lb_pvalue"].iloc[0])
    except Exception:
        lb_p = np.nan
    mejora = (media[-1] - y[-1]) * (m["sentido"] or 1) > 0
    ancho = (hi[-1] - lo[-1]) / max(abs(media[-1]), 1e-9) * 100
    tarjetas = f"""<div class="sim-grid">
<div class="sim-card"><div class="l">Último dato oficial ({anios[-1]})</div><div class="v neutral">{fmt_val(y[-1], ind)}</div><div class="d">{m['unidad']}</div></div>
<div class="sim-card"><div class="l">Pronóstico {fut[-1]}</div><div class="v {'ok' if mejora else 'alert'}">{fmt_val(media[-1], ind)}</div><div class="d">{variacion_txt(y[-1], media[-1], ind)} frente a {anios[-1]}</div></div>
<div class="sim-card"><div class="l">Rango probable {fut[-1]} (95 %)</div><div class="v neutral" style="font-size:18px">{fmt_val(lo[-1], ind)} – {fmt_val(hi[-1], ind)}</div><div class="d">amplitud relativa {fnum(ancho, 0)} %</div></div>
<div class="sim-card"><div class="l">Error de validación (MAPE)</div><div class="v {'ok' if mape < 10 else 'neutral' if mape < 25 else 'alert'}">{fnum(mape, 1)} %</div><div class="d">últimos 3 años fuera de muestra</div></div></div>"""
    cuerpo = (f"<p>Si se mantienen las dinámicas observadas, <b>{minus(m['nombre'])}</b> en <b>{territorio}</b> pasaría de {fmt_val(y[-1], ind)} "
              f"en {anios[-1]} a <b>{fmt_val(media[-1], ind)}</b> en {fut[-1]}: trayectoria de <b>{'mejora' if mejora else 'deterioro'}</b>.</p>"
              f"<p>La banda azul muestra el rango donde caería el valor real con 95 % de probabilidad. Un pronóstico no es destino: las políticas pueden cambiarlo.</p>"
              f"<p class='nota-fuente'>{etiqueta_fuente(ind)}</p>")
    html_n = callout("Hacia dónde va el indicador", cuerpo, "ok" if mejora else "warn", "🧠")
    tabla_p = pd.DataFrame({"Año": fut, "Pronóstico": media, "Límite inferior 95 %": lo, "Límite superior 95 %": hi})
    tec = (f'<div class="tec"><h5>Modelo</h5><p>{desc}. ARIMA: p, q ∈ {{0,1,2}}, d ∈ {{0,1}}, selección por AIC. Ljung-Box: p = {fnum(lb_p, 4)}. '
           f'MAPE (3 años fuera de muestra) = {fnum(mape, 2)} %. Observaciones: {len(y)} ({anios[0]}–{anios[-1]}).</p>'
           f'{tabla_html(tabla_p, decs={"Año": 0, "Pronóstico": m["dec"], "Límite inferior 95 %": m["dec"], "Límite superior 95 %": m["dec"]})}'
           f'<h5>Salida de estimación</h5>{mono(res.summary().as_text())}</div>')
    return html_n, f, tarjetas, tec


# -----------------------------------------------------------------------------
# 23. PESTAÑA 9 · LABORATORIO DE SIMULACIÓN FISCAL (panel FE + fan chart)
# -----------------------------------------------------------------------------
PALANCAS = ["rec_propios", "dep_transf", "inversion_pct"]
RESULTADOS_SIM = {"log_va_pc": "Valor agregado per cápita real", "cobertura_neta": "Cobertura neta en educación", "tasa_homicidios": "Tasa de homicidios"}


@functools.lru_cache(maxsize=1)
def estimar_elasticidades():
    d = PANEL.sort_values(["codigo", "anio"]).copy()
    d["log_va_pc"] = np.log(d.va_pc)
    for c in PALANCAS:
        d[c + "_1"] = d.groupby("codigo")[c].shift(1)
    regs = [c + "_1" for c in PALANCAS]
    out = {}
    for y_, etq in RESULTADOS_SIM.items():
        dd = d.dropna(subset=[y_] + regs)
        Xd = pd.get_dummies(dd[regs + ["codigo", "anio"]].astype({"anio": str}), columns=["codigo", "anio"], drop_first=True, dtype=float)
        mod = sm.OLS(dd[y_].values, sm.add_constant(Xd)).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(dd.codigo)[0]})
        out[y_] = dict(b=mod.params[regs].values, V=mod.cov_params().loc[regs, regs].values,
                       tabla=pd.DataFrame({"Palanca (rezago 1)": [nombre(c) for c in PALANCAS], "β": mod.params[regs].values,
                                           "EE agrupado": mod.bse[regs].values, "t": mod.tvalues[regs].values, "p-valor": mod.pvalues[regs].values}),
                       r2=mod.rsquared, n=int(mod.nobs), anios=(int(dd.anio.min()), int(dd.anio.max())))
        out[y_]["tabla"]["Sig."] = [p_estrellas(p) for p in out[y_]["tabla"]["p-valor"]]
    dd = DEPTO[["anio", "desempleo", "crecimiento_pib"]].dropna()
    du = dd.desempleo.diff()
    msk = du.notna() & ~dd.anio.isin([2020, 2021])
    okun = sm.OLS(du[msk].values, sm.add_constant(dd.crecimiento_pib[msk].values)).fit(cov_type="HC1")
    return out, okun


def agregado(munis, col, anio, pond="poblacion"):
    d = PANEL[(PANEL.municipio.isin(munis)) & (PANEL.anio == anio)].dropna(subset=[col])
    if d.empty:
        return np.nan
    return np.average(d[col], weights=d[pond])


@blindado(["html", "html", "fig", "html"])
def tab9_run(alcance, s_rec, s_transf, s_inv, dur, rho):
    est, okun = estimar_elasticidades()
    if alcance in MUN_A_COD:
        munis = [alcance]
    elif alcance in SUBREGIONES:
        munis = CAT[CAT.subregion == alcance].municipio.tolist()
    else:
        munis = CAT.municipio.tolist()
    choque = np.array([float(s_rec), float(s_transf), float(s_inv)])
    rng = np.random.default_rng(CONFIG["semilla"])
    N = 1000
    resultados = {}
    for y_ in RESULTADOS_SIM:
        col = "va_pc" if y_ == "log_va_pc" else y_
        hist = pd.Series({a: agregado(munis, col, a) for a in range(2011, 2026)}).dropna()
        ult_a, ult_v = int(hist.index[-1]), float(hist.iloc[-1])
        H = np.arange(ult_a + 1, 2031)
        activo = (np.arange(1, len(H) + 1) <= int(dur)).astype(float)
        if y_ == "log_va_pc":
            g = np.median(np.diff(np.log(hist.values[-8:])))
            base = ult_v * np.exp(g * (H - ult_a))
        elif y_ == "cobertura_neta":
            t6 = hist.iloc[-6:]
            pend = np.polyfit(t6.index, t6.values, 1)[0]
            base = np.clip(ult_v + pend * (H - ult_a), 0, 120)
        else:
            m5 = float(hist.iloc[-5:].mean())
            base = m5 + (ult_v - m5) * 0.5 ** (H - ult_a)
        B = rng.multivariate_normal(est[y_]["b"], est[y_]["V"], size=N)
        efec = np.zeros((N, len(H)))
        prev = np.zeros(N)
        for i in range(len(H)):
            s_prev = activo[i - 1] if i >= 1 else 0.0
            prev = rho * prev + (B @ choque) * s_prev
            efec[:, i] = prev
        esc = base * np.exp(efec) if y_ == "log_va_pc" else base + efec
        if y_ != "log_va_pc":
            esc = np.clip(esc, 0, None)
        resultados[y_] = dict(hist=hist, base=base, esc=esc, col=col, H=H)
    # Desempleo (Pasto A.M.) vía ley de Okun, propagando incertidumbre del VA y del coeficiente
    u_hist = DEPTO.set_index("anio").desempleo.dropna()
    va = resultados["log_va_pc"]
    l0 = np.log(float(va["hist"].iloc[-1]))
    d_base = np.diff(np.r_[l0, np.log(va["base"])])
    d_esc = np.diff(np.c_[np.full(N, l0), np.log(va["esc"])], axis=1)
    g_extra = d_esc - d_base[None, :]
    H_u = np.arange(int(u_hist.index[-1]) + 1, 2031)
    g_extra = g_extra[:, np.isin(va["H"], H_u)]
    H_u = H_u[-g_extra.shape[1]:] if g_extra.shape[1] else H_u
    b_ok = rng.normal(okun.params[1], okun.bse[1], N)
    esc_u = float(u_hist.iloc[-1]) + np.cumsum(b_ok[:, None] * g_extra * 100, axis=1)
    resultados["desempleo"] = dict(hist=u_hist[u_hist.index >= 2011], base=np.full(len(H_u), float(u_hist.iloc[-1])), esc=esc_u, col="desempleo", H=H_u)
    titulos = {"log_va_pc": "Valor agregado per cápita real (millones COP 2015)", "cobertura_neta": "Cobertura neta en educación (%)",
               "tasa_homicidios": "Tasa de homicidios (por 100.000 hab.)", "desempleo": "Desempleo Pasto A.M. (%) · ley de Okun"}
    sentido = {"log_va_pc": 1, "cobertura_neta": 1, "tasa_homicidios": -1, "desempleo": -1}
    f = make_subplots(rows=2, cols=2, subplot_titles=[titulos[k] for k in ["log_va_pc", "cobertura_neta", "tasa_homicidios", "desempleo"]],
                      vertical_spacing=0.15, horizontal_spacing=0.09)
    tarjetas = []
    for i, k in enumerate(["log_va_pc", "cobertura_neta", "tasa_homicidios", "desempleo"]):
        r_, c_ = i // 2 + 1, i % 2 + 1
        R = resultados[k]
        hist, base, esc = R["hist"], R["base"], R["esc"]
        p05, p10, p50, p90, p95 = np.percentile(esc, [5, 10, 50, 90, 95], axis=0)
        xx = np.r_[hist.index[-1], R["H"]]
        unir = lambda arr: np.r_[hist.iloc[-1], arr]
        fmt = ",.2f" if k == "log_va_pc" else ",.1f"
        f.add_trace(go.Scatter(x=hist.index, y=hist.values, mode="lines+markers", line=dict(color=C["navy"], width=2.3), marker=dict(size=4),
                               name="Histórico oficial", showlegend=i == 0, legendgroup="h", hovertemplate=f"Año %{{x}}<br>Observado: %{{y:{fmt}}}<extra></extra>"), row=r_, col=c_)
        for lo_, hi_, alpha_, nm in ((p05, p95, 0.16, "Banda 90 %"), (p10, p90, 0.28, "Banda 80 %")):
            f.add_trace(go.Scatter(x=np.r_[xx, xx[::-1]], y=np.r_[unir(hi_), unir(lo_)[::-1]], mode="lines", fill="toself", fillcolor=f"rgba(16,185,129,{alpha_})",
                                   line=dict(width=0), name=nm, showlegend=i == 0, legendgroup=nm, hoverinfo="skip"), row=r_, col=c_)
        f.add_trace(go.Scatter(x=xx, y=unir(base), mode="lines", line=dict(color="#64748b", width=2, dash="dash"), name="Línea base inercial",
                               showlegend=i == 0, legendgroup="b", hovertemplate=f"Año %{{x}}<br>Línea base: %{{y:{fmt}}}<extra></extra>"), row=r_, col=c_)
        f.add_trace(go.Scatter(x=xx, y=unir(p50), mode="lines+markers", line=dict(color=C["verde"], width=3), marker=dict(size=5),
                               name="Escenario (mediana)", showlegend=i == 0, legendgroup="e", hovertemplate=f"Año %{{x}}<br>Escenario: %{{y:{fmt}}}<extra></extra>"), row=r_, col=c_)
        dif = esc[:, -1] - base[-1]
        if k == "log_va_pc":
            dif = (esc[:, -1] / base[-1] - 1) * 100
        lo_d, md_d, hi_d = np.percentile(dif, [5, 50, 95])
        concluyente = (lo_d > 0) or (hi_d < 0)
        buena = md_d * sentido[k] > 0
        cls = "neutral" if (not concluyente or abs(md_d) < 1e-9) else ("ok" if buena else "alert")
        suf = " %" if k == "log_va_pc" else (" p.p." if k in ("cobertura_neta", "desempleo") else "")
        tarjetas.append(f'<div class="sim-card"><div class="l">{titulos[k].split("(")[0]}</div><div class="v {cls}">{"+" if md_d >= 0 else ""}{fnum(md_d, 2)}{suf}</div>'
                        f'<div class="d">IC 90 %: {fnum(lo_d, 2)} a {fnum(hi_d, 2)} · {"concluyente" if concluyente else "no concluyente"}</div></div>')
    f.update_layout(title="Gráfico de abanico al 2030: escenario de política vs. línea base inercial<br><sup>Bandas por simulación Monte Carlo (1.000 réplicas) de la incertidumbre de las elasticidades estimadas</sup>",
                    height=760, hovermode="x unified", legend=dict(orientation="h", y=-0.08))
    f.update_annotations(font=dict(size=12.5, color=C["navy"]))
    kpis = '<div class="sim-grid">' + "".join(tarjetas) + "</div>"
    sin_choque = abs(s_rec) + abs(s_transf) + abs(s_inv) == 0
    sig = {k: est[k]["tabla"] for k in est}
    lineas = []
    for k, t in sig.items():
        s_ = t[t["p-valor"] < 0.10]
        if len(s_):
            lineas.append(f"<li>{RESULTADOS_SIM[k]}: " + "; ".join(f"{r['Palanca (rezago 1)']} (β = {fnum(r['β'], 4)}, p = {fnum(r['p-valor'], 3)})" for _, r in s_.iterrows()) + ".</li>")
    if sin_choque:
        cuerpo = "<p>Mueva los controles de <b>recaudo propio, dependencia de transferencias o inversión</b> para construir un escenario.</p>"
        tono = "info"
    else:
        cuerpo = (f"<p>Escenario en <b>{alcance}</b>: {('+' if s_rec >= 0 else '')}{s_rec} p.p. en recursos propios, {('+' if s_transf >= 0 else '')}{s_transf} p.p. en dependencia de "
                  f"transferencias y {('+' if s_inv >= 0 else '')}{s_inv} p.p. en magnitud de la inversión durante {int(dur)} año(s). Las tarjetas muestran la diferencia frente a la línea "
                  f"base en 2030 y su intervalo del 90 %; <b>«no concluyente»</b> significa que la evidencia histórica no permite distinguir el efecto de cero.</p>"
                  f"<p>Palancas con evidencia histórica (p &lt; 0,10):</p><ul>{''.join(lineas) or '<li>Ninguna palanca resulta significativa en los datos 2011-2022: los efectos simulados son inciertos.</li>'}</ul>")
        tono = "info"
    cuerpo += ("<p class='nota-fuente'>Elasticidades estimadas con datos oficiales (DNP-IDF, DANE, MEN, MinDefensa) en un panel de efectos fijos de municipio y año; "
               "simulación de forma reducida, útil para comparar escenarios y no como predicción puntual.</p>")
    html_n = callout("Resultado del escenario", cuerpo, tono, "🎯")
    t_html = ""
    for k, e in est.items():
        t_html += (f"<h5>Variable dependiente: {RESULTADOS_SIM[k]}{' (log)' if k == 'log_va_pc' else ''} · R² = {fnum(e['r2'], 3)} · n = {e['n']:,} · {e['anios'][0]}–{e['anios'][1]}</h5>"
                   + tabla_html(e["tabla"], decs={"β": 5, "EE agrupado": 5, "t": 3, "p-valor": 4}))
    tec = (f'<div class="tec"><h5>Especificación</h5><p>y<sub>it</sub> = α<sub>i</sub> + τ<sub>t</sub> + β₁ recursos propios<sub>i,t−1</sub> + β₂ dependencia de transferencias<sub>i,t−1</sub> '
           f'+ β₃ magnitud de inversión<sub>i,t−1</sub> + ε<sub>it</sub>; errores agrupados por municipio. Dinámica: efecto<sub>t</sub> = ρ·efecto<sub>t−1</sub> + β′·choque<sub>t−1</sub>, '
           f'ρ = {rho}. Bandas: β ~ N(β̂, V̂) con 1.000 réplicas. Líneas base: crecimiento mediano 8 años (VA), tendencia lineal 6 años (cobertura), convergencia a la media de 5 años con vida media de 1 año (homicidios).</p>'
           f'{t_html}<h5>Ley de Okun (Pasto A.M., excluye 2020-2021)</h5><p>Δ desempleo = {fnum(okun.params[0], 3)} + ({fnum(okun.params[1], 3)}) · crecimiento del PIB · '
           f'EE robusto = {fnum(okun.bse[1], 3)}, p = {fnum(okun.pvalues[1], 4)}, R² = {fnum(okun.rsquared, 3)}</p></div>')
    return kpis, html_n, f, tec


# -----------------------------------------------------------------------------
# 24. PESTAÑA 10 · INTERPRETABILIDAD (XAI) Y RECOMENDACIONES TERRITORIALES
# -----------------------------------------------------------------------------
RECOMENDACIONES = {
    "ipm": "Focalizar oferta social (vivienda, agua y saneamiento, aseguramiento) con el SISBÉN IV y metas de cierre de brechas.",
    "ipm_rural": "Priorizar la ruralidad dispersa: acueductos veredales, vías terciarias y conectividad.",
    "brecha_ipm": "Llevar servicios de la cabecera a la zona rural con equipos extramurales y esquemas regionales.",
    "priv_bajo_logro": "Educación flexible para adultos y jóvenes, y articulación con el SENA para completar la media.",
    "priv_sin_agua": "Plan departamental de aguas: soluciones individuales y colectivas en zonas dispersas.",
    "priv_excretas": "Saneamiento básico rural (unidades sanitarias) con cofinanciación nacional.",
    "priv_sin_aseg": "Afiliación activa al régimen subsidiado y búsqueda de población no asegurada.",
    "priv_trab_informal": "Formalización laboral y empresarial: ventanilla única y acompañamiento tributario.",
    "priv_analfabetismo": "Programas de alfabetización de adultos con enfoque étnico y territorial.",
    "va_pc": "Encadenamientos productivos (agroindustria, turismo, economía popular) y acceso a crédito formal.",
    "tasa_homicidios": "Seguridad y convivencia con presencia institucional integral y prevención de violencia juvenil.",
    "tasa_secuestros": "Coordinación con el GAULA y prevención en corredores de riesgo.",
    "tasa_vif": "Fortalecer comisarías de familia, rutas de atención y prevención en colegios (una tasa alta de denuncias también refleja mayor capacidad institucional para denunciar).",
    "coca_ha": "Sustitución voluntaria, desarrollo alternativo, formalización de tierras y mercados lícitos.",
    "coca_pct": "Intervención territorial integral en los núcleos de cultivo con alternativas económicas.",
    "cobertura_neta": "Transporte y alimentación escolar (PAE) y estrategias de permanencia rural.",
    "desercion": "Alertas tempranas de deserción y acompañamiento psicosocial a estudiantes.",
    "partos_inst": "Atención prenatal y casas de paso para gestantes de zonas dispersas.",
    "dep_transf": "Fortalecer ingresos propios para reducir la dependencia del SGP.",
    "rec_propios": "Catastro multipropósito y fiscalización del predial y del ICA.",
    "inversion_pct": "Racionalizar el funcionamiento para liberar espacio fiscal hacia inversión.",
    "idf": "Plan de saneamiento y fortalecimiento de la gestión fiscal municipal.",
    "mdm": "Fortalecer capacidades de planeación, contratación y ejecución.",
}
OBJ_XAI = ["ipm", "va_pc", "tasa_homicidios", "cobertura_neta", "desercion", "coca_pct"]
FEATS_XAI = ["va_pc", "cobertura_neta", "desercion", "partos_inst", "tasa_homicidios", "tasa_vif", "coca_pct", "dep_transf", "rec_propios",
             "inversion_pct", "idf", "priv_sin_agua", "priv_trab_informal", "priv_bajo_logro"]
RADAR = ["ipm", "priv_sin_agua", "priv_trab_informal", "va_pc", "cobertura_neta", "desercion", "partos_inst", "tasa_homicidios",
         "tasa_vif", "coca_pct", "rec_propios", "idf"]


@functools.lru_cache(maxsize=16)
def modelo_xai(a0, a1, target):
    feats = [f for f in FEATS_XAI if f != target and not (target == "ipm" and f.startswith("priv_"))]
    d, feats, modo = datos_modelo(a0, a1, target, feats)
    X, y = d[feats], d[target].values
    if modo == "panel":
        tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=7).split(X, y, d.codigo.values))
    else:
        tr, te = next(KFold(n_splits=4, shuffle=True, random_state=7).split(X))
    rf = RandomForestRegressor(n_estimators=250, min_samples_leaf=3, max_features=0.6, random_state=0, n_jobs=-1).fit(X.iloc[tr], y[tr])
    pi = permutation_importance(rf, X.iloc[te], y[te], n_repeats=10, random_state=0, n_jobs=-1)
    r2 = r2_score(y[te], rf.predict(X.iloc[te]))
    rf_full = RandomForestRegressor(n_estimators=250, min_samples_leaf=3, max_features=0.6, random_state=0, n_jobs=-1).fit(X, y)
    return rf_full, feats, d, X, pi.importances_mean, pi.importances_std, r2, modo


@blindado(["html", "fig", "fig", "fig", "fig", "html"])
def tab10_run(subs, muns, a0, a1, target, municipio):
    a0, a1 = rango(a0, a1)
    rf, feats, d, X, imp, sd, r2, modo = modelo_xai(a0, a1, target)
    m = META[target]
    o = np.argsort(imp)
    f_imp = go.Figure(go.Bar(x=imp[o], y=[nombre(feats[i]) for i in o], orientation="h", error_x=dict(type="data", array=sd[o], color="#94a3b8"),
                             marker=dict(color=imp[o], colorscale=ESCALA_AZUL), hovertemplate="%{y}<br>Pérdida de R² al permutar: %{x:.4f}<extra></extra>"))
    f_imp.update_layout(title=f"Importancia por permutación<br><sup>¿qué variables ayudan más a predecir {minus(m['nombre'])}? (muestra de prueba)</sup>", height=500,
                        margin=dict(l=260, r=30, t=70, b=50))
    f_imp.update_xaxes(title_text="caída del R² al desordenar la variable")
    cod = MUN_A_COD[municipio]
    filas_m = d[d.codigo == cod]
    if filas_m.empty:
        raise ValueError(f"{municipio} no tiene observaciones completas para este modelo en {a0}-{a1}")
    fila = filas_m.sort_values("anio").iloc[[-1]] if "anio" in filas_m else filas_m.iloc[[-1]]
    anio_ref = int(fila.anio.iloc[0]) if "anio" in fila else 2018
    x0 = fila[feats]
    pred0 = rf.predict(x0)[0]
    med = X.median()
    contrib = []
    for f_ in feats:
        x1 = x0.copy()
        x1[f_] = med[f_]
        contrib.append(pred0 - rf.predict(x1)[0])
    contrib = np.array(contrib)
    oc = np.argsort(np.abs(contrib))
    s = m["sentido"] or 1
    f_loc = go.Figure(go.Bar(x=contrib[oc], y=[nombre(feats[i]) for i in oc], orientation="h",
                             marker_color=[C["verde"] if c * s > 0 else C["rojo"] for c in contrib[oc]],
                             customdata=np.column_stack([[fmt_val(x0[feats[i]].iloc[0], feats[i]) for i in oc], [fmt_val(med[feats[i]], feats[i]) for i in oc]]),
                             hovertemplate="%{y}<br>Valor del municipio: %{customdata[0]}<br>Mediana Nariño: %{customdata[1]}<br>Aporte: %{x:+.3f}<extra></extra>"))
    f_loc.add_vline(x=0, line=dict(color="#475569", width=1))
    f_loc.update_layout(title=f"Explicación local · {municipio} ({anio_ref})<br><sup>aporte de cada factor frente a un municipio típico (verde = favorable, rojo = desfavorable)</sup>",
                        height=500, margin=dict(l=260, r=30, t=70, b=50))
    f_loc.update_xaxes(title_text=f"aporte ({m['unidad']})")
    top = feats[int(np.argmax(imp))]
    pdp = partial_dependence(rf, X, [feats.index(top)], grid_resolution=40, percentiles=(0.0, 1.0))
    grid = pdp.get("grid_values", pdp.get("values"))[0]
    f_pdp = go.Figure(go.Scatter(x=grid, y=pdp["average"][0], mode="lines", line=dict(color=C["azul"], width=3, shape="spline"),
                                 hovertemplate=f"{nombre(top)}: %{{x:,.2f}}<br>{m['nombre']} esperado: %{{y:,.2f}}<extra></extra>"))
    f_pdp.add_vline(x=float(x0[top].iloc[0]), line=dict(color=C["ambar"], dash="dash", width=2), annotation_text=municipio, annotation_font=dict(color="#b45309", size=11))
    f_pdp.update_layout(title=f"Dependencia parcial de {minus(m['nombre'])}<br><sup>efecto promedio de {minus(nombre(top))} (variable más importante)</sup>", height=450)
    eje(f_pdp, top, "x")
    eje(f_pdp, target, "y")
    rec_a0 = max(a0, 2019)
    cs_r = corte_transversal(rec_a0, a1, RADAR)
    inds = [k for k in RADAR if cs_r[k].notna().sum() >= 50]
    pct = pd.DataFrame({k: percentil_orientado(cs_r[k].fillna(cs_r[k].median()).values, k) for k in inds})
    pct["municipio"] = cs_r.municipio.values
    pct["subregion"] = cs_r.subregion.values
    pm = pct[pct.municipio == municipio][inds].iloc[0]
    sb = MUN_A_SUB[municipio]
    ps = pct[pct.subregion == sb][inds].median()
    etiquetas = [nombre(k).split("(")[0].strip()[:24] for k in inds]
    f_rad = go.Figure()
    f_rad.add_trace(go.Scatterpolar(r=[50] * len(inds) + [50], theta=etiquetas + etiquetas[:1], name="Mediana Nariño", line=dict(color="#94a3b8", dash="dash")))
    f_rad.add_trace(go.Scatterpolar(r=list(ps.values) + [ps.values[0]], theta=etiquetas + etiquetas[:1], name=f"Mediana {sb}", line=dict(color=C["ambar"], width=2)))
    f_rad.add_trace(go.Scatterpolar(r=list(pm.values) + [pm.values[0]], theta=etiquetas + etiquetas[:1], name=municipio, fill="toself",
                                    fillcolor="rgba(30,58,138,.18)", line=dict(color=C["azul"], width=3)))
    f_rad.update_layout(title=f"Perfil de desempeño de {municipio}<br><sup>percentil orientado (100 = mejor de Nariño) · promedios {rec_a0}–{a1} y cortes censales</sup>", height=540,
                        polar=dict(radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75, 100], gridcolor="#e2e8f0"), angularaxis=dict(tickfont=dict(size=10))),
                        legend=dict(orientation="h", y=-0.1))
    fort = pm.sort_values(ascending=False).head(3)
    debi = pm.sort_values().head(3)
    rec = "".join(f"<li><b>{nombre(k)}</b> (percentil {fnum(debi[k], 0)}): {RECOMENDACIONES.get(k, 'Priorizar en el plan de desarrollo.')}</li>" for k in debi.index)
    pob = PANEL[(PANEL.municipio == municipio) & (PANEL.anio == min(a1, 2025))].poblacion.iloc[0]
    ipm_m = CS.set_index("municipio").ipm[municipio]
    cuerpo = (f"<p><b>{municipio}</b> ({sb}, {CAT.set_index('municipio').zona[municipio].lower()}) tiene cerca de <b>{fnum(pob, 0)}</b> habitantes "
              f"(DANE) y un IPM censal de <b>{fnum(ipm_m, 1)} %</b>. Su {minus(m['nombre'])} de referencia es <b>{fmt_val(fila[target].iloc[0], target)}</b> "
              f"(el modelo predice {fmt_val(pred0, target)}).</p><ul>"
              f"<li><b>Fortalezas relativas:</b> {', '.join(f'{minus(nombre(k))} (p{fnum(v, 0)})' for k, v in fort.items())}.</li>"
              f"<li><b>Rezagos prioritarios:</b> {', '.join(f'{minus(nombre(k))} (p{fnum(v, 0)})' for k, v in debi.items())}.</li></ul>"
              f"<p><b>Recomendaciones territoriales:</b></p><ul>{rec}</ul>"
              f"<p class='nota-fuente'>Percentil orientado: 100 = mejor situación entre los 64 municipios. Diagnóstico automático: complementar con conocimiento local.</p>")
    html_n = callout(f"Diagnóstico automatizado · {municipio}", cuerpo, "info", "🔎")
    tabla_p = pd.DataFrame({"Indicador": [nombre(k) for k in inds], "Valor": [fmt_val(cs_r.loc[cs_r.municipio == municipio, k].iloc[0], k) for k in inds],
                            "Mediana Nariño": [fmt_val(cs_r[k].median(), k) for k in inds], "Percentil orientado": pm.values,
                            "Mediana subregión (percentil)": ps.values})
    tec = (f'<div class="tec"><h5>Modelo explicativo</h5><p>Random Forest (250 árboles, hoja mínima 3) sobre {"el panel municipio-año" if modo == "panel" else "el corte transversal municipal"} '
           f'{a0}–{a1}; R² en datos no vistos = {fnum(r2, 3)}. Importancia por permutación (10 repeticiones) en la muestra de prueba. Explicación local: diferencia '
           f'entre la predicción del municipio y la obtenida al llevar cada factor a la mediana (análisis ceteris paribus).</p>'
           f'{tabla_html(pd.DataFrame({"Variable": [nombre(f_) for f_ in feats], "Importancia media": imp, "Desv. est.": sd}).sort_values("Importancia media", ascending=False), decs={"Importancia media": 4, "Desv. est.": 4})}'
           f'<h5>Tablero de percentiles de {municipio}</h5>{tabla_html(tabla_p, decs={"Percentil orientado": 0, "Mediana subregión (percentil)": 0})}</div>')
    return html_n, f_imp, f_loc, f_pdp, f_rad, tec




# -----------------------------------------------------------------------------
# 25. INTERFAZ GRADIO (compatible con Gradio 4.x, 5.x y 6.x)
# -----------------------------------------------------------------------------
TEMA = gr.themes.Soft(primary_hue="blue", secondary_hue="slate", neutral_hue="slate",
                      font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
                      font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"])
_params_blocks = inspect.signature(gr.Blocks.__init__).parameters
_params_launch = inspect.signature(gr.Blocks.launch).parameters
_kw_blocks = {"title": "Observatorio Económico y Social de Nariño"}
if "css" in _params_blocks:
    _kw_blocks.update(css=CSS, theme=TEMA)

ANIO_MAX = int(PANEL.anio.max())
OPC_SUB = SUBREGIONES[:]


def actualizar_municipios(subs, muns_actuales):
    """Cascada Subregión → Municipios: nunca deja la lista vacía ni conserva municipios fuera del filtro."""
    lista = sorted(municipios_sel(subs, None), key=lambda s: unicodedata.normalize("NFD", s))
    keep = [m for m in (muns_actuales or []) if m in lista]
    return gr.update(choices=lista, value=keep)


def restablecer():
    return (gr.update(value=[]), gr.update(choices=NOMBRES, value=[]), gr.update(value=A0), gr.update(value=ANIO_MAX))


def actualizar_ind_pron(territorio):
    if territorio == TERR_NARINO:
        keys = [k for k in SERIES_PRON_DEP if DEPTO[k].notna().sum() >= 8]
        val = "desempleo"
    else:
        keys = [k for k in IND_MUN_ANUAL if PANEL.loc[PANEL.municipio == territorio, k].notna().sum() >= 8]
        val = "tasa_homicidios" if "tasa_homicidios" in keys else keys[0]
    return gr.update(choices=opciones(keys), value=val)


def actualizar_irf_opts(vars_):
    vars_ = list(vars_ or [])
    ops = opciones(vars_)
    return (gr.update(choices=ops, value=vars_[-1] if vars_ else None), gr.update(choices=ops, value=vars_[0] if vars_ else None))


def clave_filtros(subs, muns, a0, a1):
    a0, a1 = rango(a0, a1)
    return (tuple(sorted(subs or [])), tuple(sorted(muns or [])), a0, a1)


def marcar_pendiente(subs, muns, a0, a1, aplicado):
    if aplicado is not None and clave_filtros(subs, muns, a0, a1) == tuple(tuple(x) if isinstance(x, list) else x for x in aplicado):
        return estado_filtros(subs, muns, a0, a1)
    return estado_filtros(subs, muns, a0, a1, pendiente=True)


def sincronizar(subs, muns, a0, a1):
    """Lleva la selección del panel a las pestañas con controles propios (Radiografía, Pronóstico, Simulador, XAI)."""
    sel = municipios_sel(subs, muns)
    muns_v = [m for m in (muns or []) if m in MUN_A_COD]
    if hay_seleccion(sel):
        vista = "Selección actual"
        terr = muns_v[0] if muns_v else (sel[0] if len(sel) == 1 else TERR_NARINO)
        subs_sel = {MUN_A_SUB[m] for m in sel}
        alcance = sel[0] if len(sel) == 1 else (next(iter(subs_sel)) if len(subs_sel) == 1 else "Todo Nariño")
        muni_x = sel[0]
    else:
        vista, terr, alcance, muni_x = "25 más críticos", TERR_NARINO, "Todo Nariño", "Pasto"
    try:
        perfil = html_perfil(subs, muns, a0, a1)
    except Exception as e:
        perfil = f'<div class="perfil-vacio">No fue posible construir el perfil: {e}</div>'
    return (gr.update(value=vista), gr.update(value=terr), gr.update(value=alcance), gr.update(value=muni_x),
            estado_filtros(subs, muns, a0, a1), perfil, clave_filtros(subs, muns, a0, a1))


def restablecer_todo():
    return restablecer() + sincronizar([], [], A0, ANIO_MAX)


def muni_xai_default(subs, muns):
    sel = municipios_sel(subs, muns)
    return gr.update(value=sel[0] if len(sel) < 64 else "Pasto")


with gr.Blocks(**_kw_blocks) as demo:
    gr.HTML(f"<style>{CSS}</style>")
    gr.HTML(html_topbar())
    with gr.Column(elem_classes="panel-control"):
        gr.HTML('<div class="panel-titulo">🎛️ Panel de control territorial</div>')
        with gr.Row(equal_height=True):
            f_sub = gr.Dropdown(OPC_SUB, value=[], multiselect=True, label="Subregión (13 subregiones)", scale=3,
                                info="Vacío = todo Nariño. La lista de municipios se ajusta en cascada")
            f_mun = gr.Dropdown(NOMBRES, value=[], multiselect=True, label="Municipios (64 municipios)", scale=3,
                                info="Vacío = todos los municipios de las subregiones elegidas")
            f_a0 = gr.Slider(A0, ANIO_MAX, value=A0, step=1, label="Año inicial", scale=2)
            f_a1 = gr.Slider(A0, ANIO_MAX, value=ANIO_MAX, step=1, label="Año final", scale=2)
            with gr.Column(scale=1, min_width=170):
                b_apl = gr.Button("Aplicar filtros", variant="primary", elem_classes="obs-btn-primary")
                b_res = gr.Button("Restablecer", variant="secondary", elem_classes="obs-btn-sec")
                f_estado = gr.HTML(estado_filtros([], [], A0, ANIO_MAX))
    FILTROS = [f_sub, f_mun, f_a0, f_a1]
    f_aplicado = gr.State(clave_filtros([], [], A0, ANIO_MAX))

    with gr.Tabs():
        with gr.Tab("🏛️ Inicio"):
            gr.HTML(html_hero())
            gr.HTML(html_kpis())
            t1_perfil = gr.HTML(html_perfil([], [], A0, ANIO_MAX))
            with gr.Row():
                with gr.Column(scale=3):
                    gr.Plot(fig_pulso(), show_label=False)
                with gr.Column(scale=2):
                    gr.Plot(fig_sectores(), show_label=False)
            gr.Plot(fig_social(), show_label=False)
            with gr.Row():
                with gr.Column(scale=2):
                    gr.HTML(html_ctei())
                with gr.Column(scale=3):
                    gr.Plot(fig_ctei(), show_label=False)
            gr.HTML(html_guia())
            gr.HTML(html_fuentes())
            with gr.Accordion("🧾 Bitácora de auditoría de datos (calidad, rupturas e imputaciones)", open=False):
                gr.HTML(html_auditoria())
            gr.HTML(html_ficha())

        with gr.Tab("📊 Radiografía"):
            gr.HTML(intro("📊", "Radiografía socioeconómica y explorador municipal",
                          "Compare los 64 municipios con cifras oficiales: quién está mejor y peor, cuán grandes son las brechas entre subregiones, "
                          "cómo han evolucionado y qué territorios se comportan de forma atípica.",
                          ["EDA", "Rankings", "Diagramas de caja", "Outliers IQR / Z-score", "Normalidad y Kruskal-Wallis", "Spearman"]))
            with gr.Row():
                t2_ind = gr.Dropdown(opciones(IND_MUN), value="tasa_homicidios", label="Indicador", scale=3)
                t2_anio = gr.Slider(A0, ANIO_MAX, value=2024, step=1, label="Año de corte", scale=2)
                t2_vista = gr.Radio(["25 más críticos", "25 mejores", "Selección actual"], value="25 más críticos", label="Vista del ranking", scale=3)
                t2_btn = gr.Button("Actualizar", variant="primary", elem_classes="obs-btn-primary", scale=1)
            t2_n = gr.HTML()
            with gr.Row():
                t2_rank = gr.Plot(show_label=False)
                t2_box = gr.Plot(show_label=False)
            t2_tr = gr.Plot(show_label=False)
            t2_out = gr.HTML()
            with gr.Accordion("🔬 Vista técnica / econometrista", open=False):
                t2_tec = gr.HTML()
                t2_corr = gr.Plot(show_label=False)
                t2_csv = gr.File(label="Descargar datos filtrados (CSV)")

        with gr.Tab("🗺️ Espacial"):
            gr.HTML(intro("🗺️", "Geointeligencia y econometría espacial",
                          "Mapas sobre los límites oficiales del MGN-DANE. El I de Moran mide si los municipios vecinos se parecen; LISA localiza "
                          "puntos calientes (Alto-Alto) y núcleos fríos (Bajo-Bajo), y el mapa de significancia muestra la solidez de cada hallazgo.",
                          ["Coroplético temático", "I de Moran global", "C de Geary", "LISA", "Significancia local", "Contigüidad Queen/Rook real", "KNN y distancia inversa"]))
            with gr.Row():
                t3_ind = gr.Dropdown(opciones(IND_MUN), value="ipm", label="Indicador", scale=3)
                t3_anio = gr.Slider(A0, ANIO_MAX, value=2024, step=1, label="Año", scale=2)
                t3_w = gr.Dropdown(["Contigüidad Queen (fronteras MGN)", "Contigüidad Rook (fronteras MGN)", "K vecinos más cercanos", "Distancia inversa (umbral)"],
                                   value="Contigüidad Queen (fronteras MGN)", label="Matriz de pesos espaciales W", scale=3)
                t3_k = gr.Slider(2, 8, value=4, step=1, label="k vecinos (KNN)", scale=1)
                t3_btn = gr.Button("Calcular", variant="primary", elem_classes="obs-btn-primary", scale=1)
            t3_n = gr.HTML()
            with gr.Row():
                t3_map = gr.Plot(show_label=False)
                t3_lisa = gr.Plot(show_label=False)
            with gr.Row():
                t3_sig = gr.Plot(show_label=False)
                t3_sc = gr.Plot(show_label=False)
            t3_t = gr.Plot(show_label=False)
            with gr.Accordion("🔬 Vista técnica / econometrista", open=False):
                t3_tec = gr.HTML()

        with gr.Tab("⛏️ Tipologías"):
            gr.HTML(intro("⛏️", "Tipologías territoriales y minería de datos",
                          "Agrupa municipios con perfiles similares para diseñar políticas diferenciadas; compara tres algoritmos y evalúa la calidad con Silhouette.",
                          ["K-Means", "Jerárquico (Ward)", "DBSCAN", "Silhouette", "Calinski-Harabasz", "PCA 2D"]))
            with gr.Row():
                t4_vars = gr.Dropdown(opciones(IND_MUN), value=VARS_TIPO, multiselect=True, label="Variables de agrupación", scale=4)
                t4_met = gr.Radio(["K-Means", "Jerárquico (Ward)", "DBSCAN"], value="K-Means", label="Algoritmo", scale=2)
            with gr.Row():
                t4_k = gr.Slider(2, 8, value=4, step=1, label="Número de tipologías (k)", scale=2)
                t4_eps = gr.Slider(0.8, 4.0, value=2.4, step=0.1, label="ε de DBSCAN", scale=2)
                t4_log = gr.Checkbox(value=True, label="Log en variables asimétricas", scale=1)
                t4_btn = gr.Button("Agrupar", variant="primary", elem_classes="obs-btn-primary", scale=1)
            t4_n = gr.HTML()
            t4_pca = gr.Plot(show_label=False)
            with gr.Row():
                t4_map = gr.Plot(show_label=False)
                t4_sil = gr.Plot(show_label=False)
            t4_perf = gr.Plot(show_label=False)
            t4_tab = gr.HTML()
            with gr.Accordion("🔬 Vista técnica / econometrista", open=False):
                t4_tec = gr.HTML()
                t4_den = gr.Plot(show_label=False)

        with gr.Tab("📉 Índice PCA"):
            gr.HTML(intro("📉", "Síntesis dimensional por componentes principales",
                          "Resume muchos indicadores en pocas dimensiones y construye un Índice Sintético de Desarrollo Territorial de 0 a 100.",
                          ["PCA", "Scree plot con criterio de Kaiser", "Cargas factoriales", "Biplot", "KMO y Bartlett", "Mapa del índice"]))
            with gr.Row():
                t5_vars = gr.Dropdown(opciones(IND_MUN), value=VARS_PCA, multiselect=True, label="Variables del índice", scale=5)
                t5_btn = gr.Button("Calcular índice", variant="primary", elem_classes="obs-btn-primary", scale=1)
            t5_n = gr.HTML()
            with gr.Row():
                t5_scree = gr.Plot(show_label=False)
                t5_load = gr.Plot(show_label=False)
            with gr.Row():
                t5_map = gr.Plot(show_label=False)
                t5_bi = gr.Plot(show_label=False)
            with gr.Accordion("📋 Ranking completo del índice (64 municipios)", open=False):
                t5_rank = gr.Plot(show_label=False)
            with gr.Accordion("🔬 Vista técnica / econometrista", open=False):
                t5_tec = gr.HTML()

        with gr.Tab("🤖 Modelos"):
            gr.HTML(intro("🤖", "Modelación causal, regularización y diagnóstico de residuos",
                          "Estima qué factores se asocian con un resultado y compara seis modelos con validación fuera de muestra. Incluye residuos vs. ajustados, "
                          "Q-Q de normalidad e importancia comparada entre modelos lineales y de árboles.",
                          ["MCO robusto", "Ridge", "Lasso", "ElasticNet", "SVR", "Random Forest", "Breusch-Pagan", "RESET", "VIF", "Q-Q"]))
            with gr.Row():
                t6_y = gr.Dropdown(opciones(IND_MUN), value="ipm", label="Variable a explicar", scale=2)
                t6_x = gr.Dropdown(opciones(IND_MUN), value=FEATS_ML, multiselect=True, label="Factores explicativos", scale=4)
            with gr.Row():
                t6_mg = gr.Dropdown(["Mejor modelo"] + MODELOS_NOM, value="Mejor modelo", label="Modelo a graficar", scale=2)
                t6_btn = gr.Button("Estimar modelos", variant="primary", elem_classes="obs-btn-primary", scale=1)
            t6_n = gr.HTML()
            t6_met = gr.HTML()
            with gr.Row():
                t6_rp = gr.Plot(show_label=False)
                t6_imp = gr.Plot(show_label=False)
            with gr.Row():
                t6_res = gr.Plot(show_label=False)
                t6_qq = gr.Plot(show_label=False)
            with gr.Accordion("🔬 Vista técnica / econometrista", open=False):
                t6_tec = gr.HTML()

        with gr.Tab("📈 VAR / VECM"):
            gr.HTML(intro("📈", "Econometría dinámica multivariada",
                          "Cómo se transmiten los choques entre series departamentales oficiales: funciones impulso-respuesta con intervalos del 95 %, "
                          "descomposición de la varianza (FEVD) y verificación de estabilidad con raíces inversas.",
                          ["ADF", "Johansen", "VAR", "VECM", "OIRF con IC 95 %", "FEVD", "Raíces inversas", "Granger"]))
            gr.HTML('<div class="nota-alcance">ℹ️ <b>Alcance de este módulo:</b> trabaja con series <b>departamentales</b> de Nariño (PIB, mercado laboral de Pasto A.M., '
                    'seguridad, coca, finanzas). Esas cifras no se publican por municipio con la longitud que exige un VAR/VECM, por eso los filtros de '
                    'subregión y municipio del panel no se aplican aquí.</div>')
            with gr.Row():
                t7_vars = gr.Dropdown(opciones(VARS_VAR_OPC), value=["pib", "desempleo", "tasa_homicidios_dep"], multiselect=True,
                                      label="Series del sistema (2 a 4)", scale=4)
                t7_mod = gr.Radio(["Automático", "VAR en diferencias", "VECM"], value="Automático", label="Modelo", scale=3)
            with gr.Row():
                t7_imp = gr.Dropdown(opciones(["pib", "desempleo", "tasa_homicidios_dep"]), value="pib", label="Variable que recibe el choque", scale=2)
                t7_res = gr.Dropdown(opciones(["pib", "desempleo", "tasa_homicidios_dep"]), value="desempleo", label="Variable que responde", scale=2)
                t7_h = gr.Slider(4, 12, value=10, step=1, label="Horizonte (años)", scale=2)
                t7_cum = gr.Checkbox(value=False, label="Efecto acumulado", scale=1)
                t7_btn = gr.Button("Estimar", variant="primary", elem_classes="obs-btn-primary", scale=1)
            t7_n = gr.HTML()
            t7_irf = gr.Plot(show_label=False)
            with gr.Row():
                t7_fe = gr.Plot(show_label=False)
                t7_ro = gr.Plot(show_label=False)
            t7_s = gr.Plot(show_label=False)
            with gr.Accordion("🔬 Vista técnica / econometrista", open=False):
                t7_tec = gr.HTML()

        with gr.Tab("🧠 Pronóstico"):
            gr.HTML(intro("🧠", "Pronóstico de tendencias a 5 años",
                          "Proyecta la trayectoria probable de un indicador oficial para Nariño o cualquier municipio, con intervalos de predicción del 95 %.",
                          ["ARIMA (AIC)", "ETS amortiguado", "Intervalos 95 %", "MAPE fuera de muestra", "Ljung-Box"]))
            with gr.Row():
                t8_terr = gr.Dropdown([TERR_NARINO] + NOMBRES, value=TERR_NARINO, label="Territorio", scale=2)
                t8_ind = gr.Dropdown(opciones([k for k in SERIES_PRON_DEP if DEPTO[k].notna().sum() >= 8]), value="desempleo", label="Indicador", scale=3)
                t8_mod = gr.Radio(["ARIMA (AIC)", "ETS amortiguado"], value="ARIMA (AIC)", label="Modelo", scale=2)
                t8_btn = gr.Button("Pronosticar", variant="primary", elem_classes="obs-btn-primary", scale=1)
            t8_n = gr.HTML()
            t8_k = gr.HTML()
            t8_f = gr.Plot(show_label=False)
            with gr.Accordion("🔬 Vista técnica / econometrista", open=False):
                t8_tec = gr.HTML()

        with gr.Tab("🎯 Simulador"):
            gr.HTML(intro("🎯", "Laboratorio de simulación de políticas fiscales",
                          "Construya un escenario con las palancas fiscales del DNP y compare su trayectoria 2025–2030 con la línea base. "
                          "El gráfico de abanico muestra la incertidumbre de las elasticidades estimadas con datos oficiales.",
                          ["Panel de efectos fijos bidireccionales", "EE agrupados", "Monte Carlo", "Fan chart", "Ley de Okun"]))
            with gr.Row():
                with gr.Column(scale=1, elem_classes="panel-control"):
                    gr.HTML('<div class="panel-titulo">🧪 Diseño del escenario</div>')
                    t9_alc = gr.Dropdown(["Todo Nariño"] + SUBREGIONES + NOMBRES, value="Todo Nariño", label="Alcance territorial (Nariño, subregión o municipio)")
                    t9_rec = gr.Slider(-10, 20, value=10, step=1, label="Recaudo propio: predial + ICA (Δ p.p. de ingresos corrientes)")
                    t9_tr = gr.Slider(-20, 10, value=-5, step=1, label="Dependencia de transferencias SGP (Δ p.p. de ingresos)")
                    t9_inv = gr.Slider(-5, 5, value=2, step=0.5, label="Magnitud de la inversión (Δ p.p. del gasto)")
                    t9_dur = gr.Slider(1, 5, value=3, step=1, label="Duración del choque (años)")
                    t9_rho = gr.Slider(0.0, 0.9, value=0.5, step=0.1, label="Persistencia de los efectos (ρ)")
                    t9_btn = gr.Button("Simular escenario", variant="primary", elem_classes="obs-btn-primary")
                with gr.Column(scale=3):
                    t9_k = gr.HTML()
                    t9_n = gr.HTML()
            t9_f = gr.Plot(show_label=False)
            with gr.Accordion("🔬 Vista técnica / econometrista", open=False):
                t9_tec = gr.HTML()

        with gr.Tab("🔎 XAI"):
            gr.HTML(intro("🔎", "Interpretabilidad automatizada (XAI) y recomendaciones territoriales",
                          "Explica qué variables pesan más en un modelo de aprendizaje automático y genera un diagnóstico narrativo con fortalezas, "
                          "rezagos y recomendaciones para el municipio elegido.",
                          ["Random Forest", "Importancia por permutación", "Dependencia parcial", "Explicación local", "Percentiles orientados"]))
            with gr.Row():
                t10_y = gr.Dropdown(opciones(OBJ_XAI), value="ipm", label="Resultado a explicar", scale=2)
                t10_m = gr.Dropdown(NOMBRES, value="Pasto", label="Municipio a diagnosticar", scale=2)
                t10_btn = gr.Button("Generar diagnóstico", variant="primary", elem_classes="obs-btn-primary", scale=1)
            t10_n = gr.HTML()
            with gr.Row():
                t10_rad = gr.Plot(show_label=False)
                t10_loc = gr.Plot(show_label=False)
            with gr.Row():
                t10_imp = gr.Plot(show_label=False)
                t10_pdp = gr.Plot(show_label=False)
            with gr.Accordion("🔬 Vista técnica / econometrista", open=False):
                t10_tec = gr.HTML()

    gr.HTML(f'<p class="nota-fuente" style="text-align:center;margin-top:18px">Observatorio Económico y Social de Nariño · '
            f'{CREDITOS["programa"]} · {CREDITOS["universidad"]} · {CREDITOS["ciudad_anio"]} · Datos oficiales: DANE, DNP, MinDefensa, MinEducación, MinSalud, SIMCI</p>')

    E2 = (tab2_run, FILTROS + [t2_ind, t2_anio, t2_vista], [t2_n, t2_rank, t2_box, t2_tr, t2_out, t2_tec, t2_corr, t2_csv])
    E3 = (tab3_run, FILTROS + [t3_ind, t3_anio, t3_w, t3_k], [t3_n, t3_map, t3_lisa, t3_sig, t3_sc, t3_t, t3_tec])
    E4 = (tab4_run, FILTROS + [t4_vars, t4_k, t4_met, t4_eps, t4_log], [t4_n, t4_pca, t4_sil, t4_perf, t4_map, t4_tec, t4_tab, t4_den])
    E5 = (tab5_run, FILTROS + [t5_vars], [t5_n, t5_scree, t5_load, t5_bi, t5_rank, t5_map, t5_tec])
    E6 = (tab6_run, FILTROS + [t6_y, t6_x, t6_mg], [t6_n, t6_met, t6_rp, t6_res, t6_qq, t6_imp, t6_tec])
    E7 = (tab7_run, [t7_vars, t7_mod, t7_imp, t7_res, t7_h, t7_cum], [t7_n, t7_s, t7_irf, t7_fe, t7_ro, t7_tec])
    E8 = (tab8_run, [t8_terr, t8_ind, t8_mod], [t8_n, t8_f, t8_k, t8_tec])
    E9 = (tab9_run, [t9_alc, t9_rec, t9_tr, t9_inv, t9_dur, t9_rho], [t9_k, t9_n, t9_f, t9_tec])
    E10 = (tab10_run, FILTROS + [t10_y, t10_m], [t10_n, t10_imp, t10_loc, t10_pdp, t10_rad, t10_tec])

    f_sub.change(actualizar_municipios, [f_sub, f_mun], [f_mun])
    for ctl in FILTROS:
        ctl.change(marcar_pendiente, FILTROS + [f_aplicado], [f_estado], queue=False, show_progress="hidden")
    SINCRONIZADOS = [t2_vista, t8_terr, t9_alc, t10_m, f_estado, t1_perfil, f_aplicado]

    def encadenar(ev):
        """Tras aplicar o restablecer: recalcula todas las pestañas conectadas al panel."""
        for fn, ins, outs in (E2, E3, E4, E5, E6, E9, E10):
            ev.then(fn, ins, outs)
        ev.then(actualizar_ind_pron, [t8_terr], [t8_ind]).then(*E8)

    encadenar(b_apl.click(sincronizar, FILTROS, SINCRONIZADOS))
    encadenar(b_res.click(restablecer_todo, None, FILTROS + SINCRONIZADOS))
    for btn, ev in ((t2_btn, E2), (t3_btn, E3), (t4_btn, E4), (t5_btn, E5), (t6_btn, E6), (t7_btn, E7), (t8_btn, E8), (t9_btn, E9), (t10_btn, E10)):
        btn.click(*ev)
    t7_vars.change(actualizar_irf_opts, [t7_vars], [t7_imp, t7_res])
    t8_terr.change(actualizar_ind_pron, [t8_terr], [t8_ind])
    t2_ind.change(*E2)
    t2_vista.input(*E2)
    for ctl in (t3_ind, t3_w):
        ctl.change(*E3)
    t4_met.change(*E4)
    t9_alc.input(*E9)
    for ctl in (t9_rec, t9_tr, t9_inv, t9_dur, t9_rho):
        ctl.release(*E9)
    t10_m.input(*E10)
    for fn, ins, outs in (E2, E3, E4, E5, E6, E7, E8, E9, E10):
        demo.load(fn, ins, outs)

if "css" in _params_launch and "css" not in _params_blocks:
    demo.launch = functools.partial(demo.launch, css=CSS, theme=TEMA)

demo.launch(share=True)
