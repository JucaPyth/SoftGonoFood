"""
================================================================================
MÓDULO ALERTAS - modules/alertas.py
Alertas de stock crítico con acción sugerida.
================================================================================
"""
import streamlit as st
from db import DatabaseManager


def render_alertas(db: DatabaseManager):
    st.markdown("# 🔔 Alertas de Stock Crítico")
    st.markdown(
        "<p style='color:#7a7f9a;margin-top:-.7rem;font-size:.9rem;'>"
        "Ingredientes por debajo del nivel mínimo establecido.</p>",
        unsafe_allow_html=True
    )

    alertas = db.get_stock_critico()

    if not alertas:
        st.markdown(
            '<div class="alerta al-green">✅ ¡Excelente! Todos los ingredientes están sobre el nivel mínimo.</div>',
            unsafe_allow_html=True
        )
        return

    sin_stock = [a for a in alertas if a["stock_actual"] <= 0]
    c1, c2 = st.columns(2)
    c1.metric("🔴 Sin Stock",  len(sin_stock))
    c2.metric("🟡 Stock Bajo", len(alertas) - len(sin_stock))
    st.divider()

    tbl = """<table class="tbl"><thead><tr>
        <th>Nivel</th><th>Ingrediente</th><th>Stock Actual</th>
        <th>Mínimo</th><th>Unidad</th><th>% del Mínimo</th><th>Acción</th>
    </tr></thead><tbody>"""
    for a in alertas:
        pct = (a["stock_actual"] / a["stock_minimo"] * 100) if a["stock_minimo"] else 0
        sin = a["stock_actual"] <= 0
        nivel_badge = '<span class="badge b-red">SIN STOCK</span>' if sin else '<span class="badge b-yellow">BAJO</span>'
        barra_c = "#e8344a" if sin else "#ffc233"
        accion  = "🚨 Compra urgente" if sin else "⚠️ Programar compra"
        tbl += f"""<tr>
            <td>{nivel_badge}</td>
            <td><strong>{a['nombre']}</strong><br>
                <span style="font-size:.78rem;color:#7a7f9a;">{a.get('proveedor','—')}</span></td>
            <td class="mono" style="color:{barra_c};">{a['stock_actual']:.3f}</td>
            <td class="mono" style="color:#7a7f9a;">{a['stock_minimo']:.2f}</td>
            <td>{a['unidad']}</td>
            <td>
                <div style="width:80px;background:#2e3347;border-radius:3px;height:7px;display:inline-block;margin-right:.5rem;">
                  <div style="width:{min(100,pct):.0f}%;height:100%;background:{barra_c};border-radius:3px;"></div>
                </div>
                <span class="mono" style="font-size:.8rem;color:{barra_c};">{pct:.0f}%</span>
            </td>
            <td style="font-size:.85rem;">{accion}</td>
        </tr>"""
    tbl += "</tbody></table>"
    st.markdown(tbl, unsafe_allow_html=True)
    st.divider()
    st.markdown("💡 **Tip**: Ve a **Ingredientes → Ajuste de Stock** para registrar una compra.")
