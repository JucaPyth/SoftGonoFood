"""
================================================================================
FAST FOOD ERP - app.py
================================================================================
Sistema de gestión para negocios de comidas rápidas (hamburguesas / perros
calientes). Inspirado en MarketMan. Construido con:
  · Python 3.10+
  · Streamlit (UI)
  · SQLite  (persistencia local, migrable a PostgreSQL)

ESTRUCTURA DE MÓDULOS:
  database/  → esquema SQL + capa de acceso a datos
  modules/   → lógica de negocio por dominio
  app.py     → router y CSS global

PARA CORRER:
  pip install streamlit
  streamlit run app.py
================================================================================
"""
from db import DatabaseManager
from modules.dashboard   import render_dashboard
from modules.ingredientes import render_ingredientes
from modules.recetas      import render_recetas
from modules.ventas       import render_ventas
from modules.egresos      import render_egresos
from modules.food_cost    import render_food_cost
from modules.alertas      import render_alertas

import streamlit as st
from pathlib import Path
import sys

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN STREAMLIT
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GonoFood · Comidas Rápidas",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# TEMA VISUAL — Rojo/Amarillo estilo fast food, legible en tablet
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=JetBrains+Mono:wght@400;500&family=Inter:wght@300;400;500&display=swap');

:root {
  --bg:       #111318;
  --bg2:      #1c1f28;
  --card:     #232733;
  --border:   #2e3347;
  --red:      #e8344a;
  --yellow:   #ffc233;
  --green:    #39d98a;
  --blue:     #4a9cff;
  --txt:      #eef0f8;
  --muted:    #7a7f9a;
}

.stApp { background: var(--bg); font-family: 'Inter', sans-serif; }
.main .block-container { padding: 1.5rem 2rem; max-width: 1380px; }

/* SIDEBAR */
[data-testid="stSidebar"] { background: var(--bg2) !important; border-right: 1px solid var(--border); }
[data-testid="stSidebar"] .stMarkdown h1 { font-family:'Syne',sans-serif; color:var(--yellow); font-size:1.35rem; }

/* TÍTULOS */
h1,h2,h3 { font-family:'Syne',sans-serif !important; color:var(--txt) !important; letter-spacing:-0.02em; }
h1 { font-size:1.9rem !important; font-weight:800 !important; }
h2 { font-size:1.35rem !important; }

/* MÉTRICAS */
[data-testid="stMetric"] { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:0.9rem 1.1rem; }
[data-testid="stMetricLabel"] { color:var(--muted) !important; font-size:0.75rem !important; text-transform:uppercase; letter-spacing:.06em; }
[data-testid="stMetricValue"] { color:var(--txt) !important; font-family:'JetBrains Mono',monospace !important; font-size:1.55rem !important; }

/* BOTONES */
.stButton>button { background:var(--red); color:#fff; border:none; border-radius:7px; font-weight:600; font-size:.85rem; padding:.45rem 1.1rem; transition:all .15s; }
.stButton>button:hover { background:#c9263a; transform:translateY(-1px); box-shadow:0 4px 14px rgba(232,52,74,.35); }

/* INPUTS */
.stTextInput input,.stNumberInput input,.stSelectbox select,.stTextArea textarea {
  background:var(--card) !important; border:1px solid var(--border) !important;
  color:var(--txt) !important; border-radius:7px !important;
}
.stTextInput input:focus,.stNumberInput input:focus { border-color:var(--yellow) !important; box-shadow:0 0 0 2px rgba(255,194,51,.2) !important; }

/* TABS */
[data-testid="stTabs"] .stTabs [role="tab"] { color:var(--muted); font-weight:500; font-size:.85rem; }
[data-testid="stTabs"] .stTabs [role="tab"][aria-selected="true"] { color:var(--yellow); border-bottom:2px solid var(--yellow); }

/* ALERTAS CUSTOM */
.alerta { display:flex; align-items:flex-start; gap:.7rem; padding:.8rem 1rem; border-radius:8px; margin-bottom:.45rem; font-size:.875rem; }
.al-red    { background:rgba(232,52,74,.12);  border-left:3px solid var(--red);    color:#f9a8b4; }
.al-yellow { background:rgba(255,194,51,.12); border-left:3px solid var(--yellow); color:#fde68a; }
.al-green  { background:rgba(57,217,138,.12); border-left:3px solid var(--green);  color:#a7f3d0; }

/* TABLA CUSTOM */
.tbl { width:100%; border-collapse:collapse; font-size:.87rem; }
.tbl th { background:var(--bg2); color:var(--muted); text-transform:uppercase; font-size:.72rem; letter-spacing:.06em; padding:.6rem .85rem; text-align:left; border-bottom:1px solid var(--border); }
.tbl td { padding:.6rem .85rem; color:var(--txt); border-bottom:1px solid var(--border); }
.tbl tr:last-child td { border-bottom:none; }
.tbl tr:hover td { background:rgba(255,255,255,.02); }

/* BADGE */
.badge { display:inline-block; padding:.18rem .55rem; border-radius:999px; font-size:.72rem; font-weight:600; font-family:'JetBrains Mono',monospace; }
.b-red    { background:rgba(232,52,74,.2);  color:var(--red); }
.b-yellow { background:rgba(255,194,51,.2); color:var(--yellow); }
.b-green  { background:rgba(57,217,138,.2); color:var(--green); }
.b-blue   { background:rgba(74,156,255,.2); color:var(--blue); }

/* MONOSPACE */
.mono { font-family:'JetBrains Mono',monospace; }

/* CARD FORM */
.fcard { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:1.2rem 1.4rem; margin-bottom:1rem; }

hr { border-color:var(--border) !important; }
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# INIT BD — se ejecuta UNA vez por sesión (cache_resource)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def init_db() -> DatabaseManager:
    db = DatabaseManager()
    db.create_tables()
    db.seed_demo_data()
    return db


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
def sidebar(db: DatabaseManager) -> str:
    with st.sidebar:
        st.markdown("# 🍔 GonoFood")
        st.markdown("<p style='color:#7a7f9a;font-size:.78rem;margin-top:-.5rem;'>Sistema HORECA · Comidas Rápidas</p>", unsafe_allow_html=True)
        st.divider()

        # Mini-alertas rápidas
        alertas = db.get_stock_critico()
        if alertas:
            st.markdown(f'<div class="alerta al-red">🚨 <strong>{len(alertas)}</strong> insumo(s) en stock crítico</div>', unsafe_allow_html=True)

        st.divider()

        nav = {
            "📊  Dashboard":            "Dashboard",
            "🥬  Ingredientes":         "Ingredientes",
            "📋  Recetas / Escandallos":"Recetas",
            "🛒  Ventas":               "Ventas",
            "💸  Egresos":              "Egresos",
            "📈  Food Cost":            "Food Cost",
            "🔔  Alertas de Stock":     "Alertas",
        }
        sel = st.radio("", list(nav.keys()), label_visibility="collapsed")
        st.divider()
        st.markdown("<p style='color:#7a7f9a;font-size:.7rem;text-align:center;'>FastERP v1.0 · SQLite local</p>", unsafe_allow_html=True)

    return nav[sel]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    db = init_db()
    pagina = sidebar(db)

    rutas = {
        "Dashboard":    render_dashboard,
        "Ingredientes": render_ingredientes,
        "Recetas":      render_recetas,
        "Ventas":       render_ventas,
        "Egresos":      render_egresos,
        "Food Cost":    render_food_cost,
        "Alertas":      render_alertas,
    }
    rutas[pagina](db)


if __name__ == "__main__":
    main()
