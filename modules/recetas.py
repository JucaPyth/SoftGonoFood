"""
================================================================================
MÓDULO RECETAS - modules/recetas.py
================================================================================
"""
import streamlit as st
from db import DatabaseManager


def render_recetas(db: DatabaseManager):
    st.markdown("# 📋 Recetas y Escandallos")
    st.markdown(
        "<p style='color:#7a7f9a;margin-top:-.7rem;font-size:.9rem;'>"
        "Define qué ingredientes consume cada producto al ser vendido.</p>",
        unsafe_allow_html=True
    )

    tab1, tab2 = st.tabs(["📖 Menú Actual", "➕ Nueva Receta"])

    # ── Tab 1: Menú ───────────────────────────────────────────────────────────
    with tab1:
        recetas = db.get_recetas()
        if not recetas:
            st.info("No hay recetas. Crea una en la pestaña '➕ Nueva Receta'.")
            return

        for r in recetas:
            rc = db.get_receta_completa(r["id"])
            fc_color = "#39d98a" if rc["food_cost_pct"] <= 30 else "#ffc233" if rc["food_cost_pct"] <= 40 else "#e8344a"
            header = f"🍔 {r['nombre']}  ·  ${r['precio_venta']:,.0f}  ·  Food Cost: {rc['food_cost_pct']:.1f}%"

            with st.expander(header):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Precio Venta",    f"${rc['precio_venta']:,.0f}")
                c2.metric("Costo Producción",f"${rc['costo_total']:,.0f}")
                c3.metric("Margen Bruto",    f"${rc['margen']:,.0f}")
                c4.metric("Food Cost %",     f"{rc['food_cost_pct']:.1f}%")

                st.markdown("**Escandallo de ingredientes:**")
                tbl = """<table class="tbl"><thead><tr>
                    <th>Ingrediente</th><th>Cantidad</th><th>Unidad</th>
                    <th>Costo Unit.</th><th>Subtotal</th>
                </tr></thead><tbody>"""
                for ing in rc["ingredientes"]:
                    tbl += f"""<tr>
                        <td>{ing['nombre']}</td>
                        <td class="mono">{ing['cantidad']:.4f}</td>
                        <td>{ing['unidad']}</td>
                        <td class="mono">${ing['costo_unitario']:,.0f}</td>
                        <td class="mono">${ing['subtotal']:,.0f}</td>
                    </tr>"""
                tbl += f"""<tr style="border-top:2px solid #2e3347;">
                    <td colspan="4" style="text-align:right;color:#7a7f9a;">COSTO TOTAL</td>
                    <td class="mono" style="color:#ffc233;"><strong>${rc['costo_total']:,.0f}</strong></td>
                </tr></tbody></table>"""
                st.markdown(tbl, unsafe_allow_html=True)

    # ── Tab 2: Nueva receta ───────────────────────────────────────────────────
    with tab2:
        ings = db.get_ingredientes()
        if not ings:
            st.warning("Primero registra ingredientes.")
            return

        st.markdown('<div class="fcard">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            nombre_r    = st.text_input("Nombre de la Receta *")
            descripcion = st.text_area("Descripción", height=75)
        with c2:
            categoria   = st.selectbox("Categoría", ["Hamburguesa","Perro Caliente","Combo","Bebida","Snack","Otro"])
            precio_r    = st.number_input("Precio de Venta ($) *", min_value=0.0, step=500.0, format="%.0f")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("### 🥕 Escandallo de Ingredientes")
        if "receta_ings" not in st.session_state:
            st.session_state.receta_ings = []

        opts_ing = {i["nombre"]: i for i in ings}
        ca, cb, cc = st.columns([3, 1, 1])
        sel_ing = ca.selectbox("Ingrediente", list(opts_ing.keys()), key="ri_sel")
        ing_sel = opts_ing[sel_ing]
        cant_r  = cb.number_input(f"Cant. ({ing_sel['unidad']})", min_value=0.001, step=0.1, format="%.4f", key="ri_cant")
        cc.markdown("<br>", unsafe_allow_html=True)
        if cc.button("➕ Agregar"):
            existe = any(x["ing_id"] == ing_sel["id"] for x in st.session_state.receta_ings)
            if existe:
                st.warning(f"{sel_ing} ya está en la receta.")
            else:
                st.session_state.receta_ings.append({
                    "ing_id": ing_sel["id"], "nombre": ing_sel["nombre"],
                    "cantidad": cant_r, "unidad": ing_sel["unidad"],
                    "costo_unitario": ing_sel["costo_unitario"],
                })

        if st.session_state.receta_ings:
            costo_calc = 0
            borrar_idx = []
            for idx, ri in enumerate(st.session_state.receta_ings):
                sub = ri["cantidad"] * ri["costo_unitario"]
                costo_calc += sub
                ca2, cb2, cc2, cd2 = st.columns([3, 1.5, 1.5, 0.7])
                ca2.write(f"**{ri['nombre']}**")
                cb2.write(f"`{ri['cantidad']:.4f} {ri['unidad']}`")
                cc2.markdown(f"<span class='mono'>${sub:,.0f}</span>", unsafe_allow_html=True)
                if cd2.button("🗑", key=f"del_{idx}"):
                    borrar_idx.append(idx)
            for i in reversed(borrar_idx):
                st.session_state.receta_ings.pop(i); st.rerun()

            fc = costo_calc / precio_r * 100 if precio_r > 0 else 0
            fc_c = "#39d98a" if fc <= 30 else "#ffc233" if fc <= 40 else "#e8344a"
            st.markdown(
                f"<p style='text-align:right;'>"
                f"Costo: <span class='mono' style='color:#ffc233;'>${costo_calc:,.0f}</span> · "
                f"Food Cost: <span class='mono' style='color:{fc_c};'>{fc:.1f}%</span></p>",
                unsafe_allow_html=True
            )

        if st.button("✅ Guardar Receta", type="primary"):
            if not nombre_r:
                st.error("El nombre es obligatorio.")
            elif not st.session_state.receta_ings:
                st.error("Agrega al menos un ingrediente.")
            else:
                rid = db.crear_receta(
                    {"nombre": nombre_r, "descripcion": descripcion,
                     "categoria": categoria, "precio_venta": precio_r},
                    st.session_state.receta_ings
                )
                st.success(f"✅ Receta **{nombre_r}** creada (ID #{rid}).")
                st.session_state.receta_ings = []
                st.rerun()
