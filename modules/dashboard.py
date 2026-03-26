"""
================================================================================
MÓDULO DASHBOARD - modules/dashboard.py
================================================================================
"""
import streamlit as st
from datetime import date
from db import DatabaseManager


def render_dashboard(db: DatabaseManager):
    st.markdown("# 📊 Dashboard Operacional")
    st.markdown(
        f"<p style='color:#7a7f9a;margin-top:-.7rem;font-size:.9rem;'>"
        f"{date.today().strftime('%A %d de %B, %Y').capitalize()}</p>",
        unsafe_allow_html=True
    )

    m = db.get_dashboard_metrics()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Ventas Hoy",      f"${m['ventas_hoy']:,.0f}")
    c2.metric("📅 Ventas del Mes",  f"${m['ventas_mes']:,.0f}")
    c3.metric("💸 Egresos del Mes", f"${m['egresos_mes']:,.0f}")
    c4.metric("📈 Utilidad Bruta",  f"${m['utilidad_mes']:,.0f}",
              delta_color="normal" if m["utilidad_mes"] >= 0 else "inverse")

    c5, c6, c7, _ = st.columns(4)
    c5.metric("🔔 Alertas Críticas", m["n_criticos"],
              delta_color="inverse" if m["n_criticos"] > 0 else "normal")
    c6.metric("🍔 Productos en Menú", m["n_recetas"])
    c7.metric("📦 Valor Inventario",  f"${m['valor_inventario']:,.0f}")

    st.divider()

    col_v, col_a = st.columns([3, 2])

    # ── Top ventas del día ────────────────────────────────────────────────────
    with col_v:
        st.markdown("### 🛒 Ventas del Día por Producto")
        res = db.get_ventas_resumen_dia()
        if not res["por_receta"]:
            st.info("Sin ventas registradas hoy.")
        else:
            tbl = """<table class="tbl"><thead><tr>
                <th>Producto</th><th>Unidades</th><th>Total</th>
            </tr></thead><tbody>"""
            for r in res["por_receta"]:
                tbl += f"""<tr>
                    <td><strong>{r['nombre']}</strong></td>
                    <td class="mono">×{r['unidades']}</td>
                    <td class="mono" style="color:#39d98a;">${r['total']:,.0f}</td>
                </tr>"""
            tbl += "</tbody></table>"
            st.markdown(tbl, unsafe_allow_html=True)

    # ── Alertas rápidas ───────────────────────────────────────────────────────
    with col_a:
        st.markdown("### 🔔 Stock Crítico")
        alertas = db.get_stock_critico()
        if not alertas:
            st.markdown('<div class="alerta al-green">✅ Todos los insumos están sobre el mínimo.</div>', unsafe_allow_html=True)
        else:
            for a in alertas[:6]:
                pct = (a["stock_actual"] / a["stock_minimo"] * 100) if a["stock_minimo"] else 0
                clase = "al-red" if pct <= 50 else "al-yellow"
                st.markdown(
                    f'<div class="alerta {clase}">⚠️ <strong>{a["nombre"]}</strong><br>'
                    f'<span style="font-size:.8rem;">Stock: {a["stock_actual"]:.2f} / Mín: {a["stock_minimo"]:.2f} {a["unidad"]}</span></div>',
                    unsafe_allow_html=True
                )
