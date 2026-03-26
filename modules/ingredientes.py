"""
================================================================================
MÓDULO INGREDIENTES - modules/ingredientes.py
================================================================================
CRUD de insumos base + ajustes de stock manuales (compras, mermas).
Principio de responsabilidad única: esta UI solo llama métodos de db.
================================================================================
"""
import streamlit as st
from datetime import date
from db import DatabaseManager


def render_ingredientes(db: DatabaseManager):
    st.markdown("# 🥬 Gestión de Ingredientes")

    tab1, tab2, tab3 = st.tabs(["📋 Inventario", "➕ Nuevo Ingrediente", "🔄 Ajuste de Stock"])

    # ── Tab 1: Listado ────────────────────────────────────────────────────────
    with tab1:
        ings = db.get_ingredientes()
        if not ings:
            st.info("No hay ingredientes registrados.")
            return

        buscar = st.text_input("🔍 Buscar", placeholder="Nombre del ingrediente...")
        if buscar:
            ings = [i for i in ings if buscar.lower() in i["nombre"].lower()]

        st.markdown(f"<p style='color:#7a7f9a;font-size:.82rem;'>{len(ings)} ingredientes</p>", unsafe_allow_html=True)

        tbl = """<table class="tbl"><thead><tr>
            <th>Estado</th><th>Nombre</th><th>Stock</th><th>Mínimo</th>
            <th>Unidad</th><th>Costo Unit.</th><th>Valor Stock</th><th>Proveedor</th>
        </tr></thead><tbody>"""

        for i in ings:
            ok   = i["stock_actual"] > i["stock_minimo"]
            bajo = i["stock_actual"] <= i["stock_minimo"] and i["stock_actual"] > 0
            sin  = i["stock_actual"] <= 0

            if sin:   bdg = '<span class="badge b-red">SIN STOCK</span>'
            elif bajo: bdg = '<span class="badge b-yellow">CRÍTICO</span>'
            else:      bdg = '<span class="badge b-green">OK</span>'

            valor = i["stock_actual"] * i["costo_unitario"]
            tbl += f"""<tr>
                <td>{bdg}</td>
                <td><strong>{i['nombre']}</strong></td>
                <td class="mono">{i['stock_actual']:.3f}</td>
                <td class="mono" style="color:#7a7f9a;">{i['stock_minimo']:.2f}</td>
                <td>{i['unidad']}</td>
                <td class="mono">${i['costo_unitario']:,.0f}</td>
                <td class="mono" style="color:#39d98a;">${valor:,.0f}</td>
                <td style="color:#7a7f9a;font-size:.82rem;">{i.get('proveedor') or '—'}</td>
            </tr>"""
        tbl += "</tbody></table>"
        st.markdown(tbl, unsafe_allow_html=True)

    # ── Tab 2: Crear ──────────────────────────────────────────────────────────
    with tab2:
        st.markdown("### Registrar Nuevo Ingrediente")
        st.markdown('<div class="fcard">', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            nombre    = st.text_input("Nombre *")
            descripcion = st.text_input("Descripción")
            proveedor = st.text_input("Proveedor")
        with c2:
            unidad    = st.selectbox("Unidad de Medida", ["unidad","gr","kg","ml","lt","loncha","porción","paquete"])
            costo     = st.number_input("Costo Unitario ($) *", min_value=0.0, step=50.0, format="%.0f")
            stock_ini = st.number_input("Stock Inicial", min_value=0.0, step=1.0, format="%.2f")
            stock_min = st.number_input("Stock Mínimo *", min_value=0.0, value=5.0, step=1.0)

        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("✅ Crear Ingrediente", type="primary"):
            if not nombre:
                st.error("El nombre es obligatorio.")
            else:
                try:
                    ing_id = db.crear_ingrediente({
                        "nombre": nombre, "descripcion": descripcion,
                        "unidad": unidad, "costo_unitario": costo,
                        "stock_actual": stock_ini, "stock_minimo": stock_min,
                        "proveedor": proveedor
                    })
                    st.success(f"✅ Ingrediente **{nombre}** creado (ID #{ing_id}).")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # ── Tab 3: Ajuste de Stock ────────────────────────────────────────────────
    with tab3:
        st.markdown("### Ajustar Stock Manualmente")
        st.caption("Usa esto para registrar compras a proveedores o mermas puntuales.")

        ings_all = db.get_ingredientes()
        if not ings_all:
            st.info("No hay ingredientes registrados.")
            return

        st.markdown('<div class="fcard">', unsafe_allow_html=True)
        opts = {i["nombre"]: i for i in ings_all}
        sel  = st.selectbox("Ingrediente", list(opts.keys()))
        ing  = opts[sel]

        st.markdown(f"<p style='color:#7a7f9a;font-size:.85rem;'>Stock actual: <span class='mono'>{ing['stock_actual']:.3f} {ing['unidad']}</span></p>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            tipo_ajuste = st.selectbox("Tipo de Movimiento", [
                ("Compra (entrada)",       "compra"),
                ("Merma / Desperdicio",    "merma"),
                ("Ajuste de inventario",   "ajuste"),
            ], format_func=lambda x: x[0])

        with c2:
            cantidad_ajuste = st.number_input(f"Cantidad ({ing['unidad']})", min_value=0.001, step=0.5, format="%.3f")
            notas_ajuste    = st.text_input("Nota", placeholder="Ej: Compra proveedor, factura #123")

        st.markdown("</div>", unsafe_allow_html=True)

        tipo_cod = tipo_ajuste[1]
        delta    = cantidad_ajuste if tipo_cod == "compra" else -cantidad_ajuste

        st.markdown(
            f'<div class="alerta {"al-green" if delta > 0 else "al-yellow"}">'
            f'{"📥 Entrada" if delta > 0 else "📤 Salida"}: '
            f'<strong>{abs(delta):.3f} {ing["unidad"]}</strong> de <strong>{sel}</strong>'
            f'</div>',
            unsafe_allow_html=True
        )

        if st.button("💾 Aplicar Ajuste", type="primary"):
            db.ajustar_stock_ingrediente(ing["id"], delta, tipo_cod, notas_ajuste)
            st.success("✅ Stock actualizado correctamente.")
            st.rerun()
