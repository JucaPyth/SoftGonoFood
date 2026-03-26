"""
================================================================================
MÓDULO FOOD COST - modules/food_cost.py
Análisis de rentabilidad por producto y P&L del período.
================================================================================
"""
import streamlit as st
from datetime import date
from db import DatabaseManager


def render_food_cost(db: DatabaseManager):
    st.markdown("# 📈 Análisis de Food Cost")
    st.markdown(
        "<p style='color:#7a7f9a;margin-top:-.7rem;font-size:.9rem;'>"
        "Referencia industria: Food Cost 25–35% · Margen ideal &gt;60%</p>",
        unsafe_allow_html=True
    )

    tab1, tab2 = st.tabs(["🍔 Por Producto", "📅 P&L del Período"])

    with tab1:
        datos = db.get_food_cost_todas_recetas()
        if not datos:
            st.info("No hay recetas registradas.")
            return

        optimos    = [d for d in datos if d["estado"] == "óptimo"]
        aceptables = [d for d in datos if d["estado"] == "aceptable"]
        revisar    = [d for d in datos if d["estado"] == "revisar"]

        c1, c2, c3 = st.columns(3)
        c1.metric("✅ Óptimos (≤30%)",     len(optimos))
        c2.metric("🟡 Aceptables (30–40%)", len(aceptables))
        c3.metric("🔴 A Revisar (>40%)",    len(revisar))
        st.divider()

        cfg = {
            "óptimo":    ("b-green",  "✅ Óptimo"),
            "aceptable": ("b-yellow", "⚠️ Aceptable"),
            "revisar":   ("b-red",    "🔴 Revisar"),
        }
        fc_colores = {"óptimo": "#39d98a", "aceptable": "#ffc233", "revisar": "#e8344a"}

        tbl = """<table class="tbl"><thead><tr>
            <th>Producto</th><th>Categoría</th><th>Precio Venta</th>
            <th>Costo Prod.</th><th>Margen</th><th>Food Cost %</th><th>Estado</th>
        </tr></thead><tbody>"""
        for d in datos:
            badge_cls, badge_txt = cfg[d["estado"]]
            fc_c = fc_colores[d["estado"]]
            tbl += f"""<tr>
                <td><strong>{d['nombre']}</strong></td>
                <td style="color:#7a7f9a;">{d['categoria']}</td>
                <td class="mono">${d['precio_venta']:,.0f}</td>
                <td class="mono">${d['costo_total']:,.0f}</td>
                <td class="mono" style="color:#39d98a;">${d['margen']:,.0f}</td>
                <td class="mono" style="color:{fc_c};font-weight:700;">{d['food_cost_pct']:.1f}%</td>
                <td><span class="badge {badge_cls}">{badge_txt}</span></td>
            </tr>"""
        tbl += "</tbody></table>"
        st.markdown(tbl, unsafe_allow_html=True)
        st.markdown(
            "<p style='font-size:.78rem;color:#7a7f9a;margin-top:.5rem;'>"
            "🟢 ≤30%: excelente · 🟡 30–40%: aceptable · 🔴 >40%: revisar precios o reducir costos</p>",
            unsafe_allow_html=True
        )

    with tab2:
        col1, col2 = st.columns(2)
        fd = col1.date_input("Desde", value=date.today().replace(day=1))
        fh = col2.date_input("Hasta", value=date.today())

        pl = db.get_rentabilidad_periodo(fd.isoformat(), fh.isoformat())

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Ventas",    f"${pl['ventas_total']:,.0f}")
        c2.metric("💸 Egresos",   f"${pl['egresos_total']:,.0f}")
        c3.metric("📈 Utilidad",  f"${pl['utilidad_bruta']:,.0f}",
                  delta_color="normal" if pl["utilidad_bruta"] >= 0 else "inverse")
        c4.metric("📊 Margen",    f"{pl['margen_pct']:.1f}%")
        st.metric("🍔 Unidades Vendidas", pl["unidades_vendidas"])

        if pl["egresos_por_cat"]:
            st.markdown("**Distribución de Egresos:**")
            for c in pl["egresos_por_cat"]:
                pct = (c["total"] / pl["egresos_total"] * 100) if pl["egresos_total"] else 0
                st.markdown(
                    f"""<div style="display:flex;align-items:center;gap:1rem;margin-bottom:.6rem;">
                        <div style="width:180px;font-size:.85rem;">{c['categoria']}</div>
                        <div style="flex:1;background:#2e3347;border-radius:3px;height:7px;">
                          <div style="width:{pct:.0f}%;height:100%;background:#e8344a;border-radius:3px;"></div>
                        </div>
                        <div class="mono" style="width:110px;text-align:right;">${c['total']:,.0f}</div>
                        <div style="width:50px;color:#7a7f9a;font-size:.8rem;">{pct:.1f}%</div>
                    </div>""",
                    unsafe_allow_html=True
                )
