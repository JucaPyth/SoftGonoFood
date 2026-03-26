"""
================================================================================
MÓDULO VENTAS - modules/ventas.py
================================================================================
Registra ventas y ejecuta el descuento automático de stock por receta.
================================================================================
"""
import streamlit as st
from db import DatabaseManager


def render_ventas(db: DatabaseManager):
    st.markdown("# 🛒 Registro de Ventas")
    st.markdown(
        "<p style='color:#7a7f9a;margin-top:-.7rem;font-size:.9rem;'>"
        "Al registrar la venta se descuentan los ingredientes del inventario automáticamente.</p>",
        unsafe_allow_html=True
    )

    tab1, tab2 = st.tabs(["🧾 Nueva Venta", "📜 Historial"])

    # ── Tab 1: Nueva venta ────────────────────────────────────────────────────
    with tab1:
        recetas = db.get_recetas()
        if not recetas:
            st.warning("No hay recetas activas. Crea productos en el módulo de Recetas.")
            return

        st.markdown('<div class="fcard">', unsafe_allow_html=True)
        opts_r = {r["nombre"]: r for r in recetas}
        c1, c2 = st.columns(2)
        with c1:
            sel_r    = st.selectbox("Producto / Receta *", list(opts_r.keys()))
            receta   = opts_r[sel_r]
            cantidad = st.number_input("Cantidad *", min_value=1, value=1, step=1)
        with c2:
            metodo  = st.selectbox("Método de Pago", ["efectivo","nequi","daviplata","tarjeta","otro"])
            descuento = st.number_input("Descuento %", min_value=0.0, max_value=100.0, value=0.0, step=5.0)
            notas   = st.text_input("Notas", placeholder="Mesa, domicilio, etc.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Vista previa
        rc = db.get_receta_completa(receta["id"])
        total_prev = rc["precio_venta"] * cantidad * (1 - descuento / 100)
        verif = db.verificar_stock_receta(receta["id"], cantidad)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total a Cobrar",  f"${total_prev:,.0f}")
        c2.metric("Costo Est.",      f"${rc['costo_total'] * cantidad:,.0f}")
        c3.metric("Disponibilidad",
                  "✅ Hay stock" if verif["puede"] else "❌ Sin stock",
                  delta_color="normal" if verif["puede"] else "inverse")

        if not verif["puede"]:
            for f in verif["faltantes"]:
                st.markdown(
                    f'<div class="alerta al-red">🚫 <strong>{f["nombre"]}</strong>: '
                    f'Necesitas {f["necesario"]:.3f}, tienes {f["disponible"]:.3f}</div>',
                    unsafe_allow_html=True
                )

        if st.button("✅ Registrar Venta", type="primary", disabled=not verif["puede"]):
            res = db.registrar_venta(receta["id"], cantidad, metodo, descuento, notas)
            if res["ok"]:
                st.success(f"🎉 Venta registrada — Total: **${res['total']:,.0f}** · Inventario actualizado.")
                st.balloons()
                st.rerun()
            else:
                st.error(f"Error: {res['error']}")

    # ── Tab 2: Historial ──────────────────────────────────────────────────────
    with tab2:
        from datetime import date, timedelta
        c1, c2 = st.columns(2)
        f_desde = c1.date_input("Desde", value=date.today() - timedelta(7))
        f_hasta = c2.date_input("Hasta", value=date.today())

        ventas = db.get_ventas(f_desde.isoformat(), f_hasta.isoformat())
        if not ventas:
            st.info("Sin ventas en el período.")
        else:
            total_periodo = sum(v["total"] for v in ventas)
            st.metric("Total del período", f"${total_periodo:,.0f}",
                      help=f"{len(ventas)} transacciones")

            tbl = """<table class="tbl"><thead><tr>
                <th>#</th><th>Producto</th><th>Cant.</th><th>Precio</th>
                <th>Desc.</th><th>Total</th><th>Pago</th><th>Fecha</th>
            </tr></thead><tbody>"""
            for v in ventas:
                tbl += f"""<tr>
                    <td class="mono" style="color:#7a7f9a;">#{v['id']}</td>
                    <td><strong>{v['receta_nombre']}</strong></td>
                    <td class="mono">×{v['cantidad']}</td>
                    <td class="mono">${v['precio_unitario']:,.0f}</td>
                    <td class="mono">{v['descuento']:.0f}%</td>
                    <td class="mono" style="color:#39d98a;">${v['total']:,.0f}</td>
                    <td><span class="badge b-blue">{v['metodo_pago']}</span></td>
                    <td class="mono" style="color:#7a7f9a;">{v['fecha'][:16]}</td>
                </tr>"""
            tbl += "</tbody></table>"
            st.markdown(tbl, unsafe_allow_html=True)
