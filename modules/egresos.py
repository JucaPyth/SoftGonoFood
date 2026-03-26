"""
================================================================================
MÓDULO EGRESOS - modules/egresos.py
Registro y análisis de gastos del negocio.
================================================================================
"""
import streamlit as st
from datetime import date, timedelta
from db import DatabaseManager

CATEGORIAS_EGRESO = [
    "compra_ingredientes", "servicios", "nomina",
    "arriendo", "marketing", "equipo", "otro"
]

def render_egresos(db: DatabaseManager):
    st.markdown("# 💸 Egresos y Gastos")
    tab1, tab2, tab3 = st.tabs(["📝 Nuevo Egreso", "📜 Historial", "📊 Por Categoría"])

    with tab1:
        st.markdown('<div class="fcard">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            descripcion = st.text_input("Descripción *")
            categoria   = st.selectbox("Categoría *", CATEGORIAS_EGRESO)
            proveedor   = st.text_input("Proveedor / Beneficiario")
        with c2:
            monto       = st.number_input("Monto ($) *", min_value=0.0, step=1000.0, format="%.0f")
            metodo_pago = st.selectbox("Método de Pago", ["efectivo","transferencia","tarjeta","cheque"])
            comprobante = st.text_input("# Comprobante / Factura")
            fecha_e     = st.date_input("Fecha", value=date.today())
            notas       = st.text_area("Notas", height=60)
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("💾 Registrar Egreso", type="primary"):
            if not descripcion or monto <= 0:
                st.error("Descripción y monto son obligatorios.")
            else:
                eid = db.registrar_egreso({
                    "descripcion": descripcion, "categoria": categoria,
                    "monto": monto, "proveedor": proveedor,
                    "metodo_pago": metodo_pago, "comprobante": comprobante,
                    "notas": notas, "fecha": fecha_e.isoformat()
                })
                st.success(f"✅ Egreso registrado (ID #{eid}). Monto: **${monto:,.0f}**")
                st.rerun()

    with tab2:
        c1, c2 = st.columns(2)
        fd = c1.date_input("Desde", value=date.today() - timedelta(30))
        fh = c2.date_input("Hasta", value=date.today())
        egresos = db.get_egresos(fd.isoformat(), fh.isoformat())
        if not egresos:
            st.info("Sin egresos en el período.")
        else:
            total = sum(e["monto"] for e in egresos)
            st.metric("Total egresos período", f"${total:,.0f}")
            tbl = """<table class="tbl"><thead><tr>
                <th>Fecha</th><th>Descripción</th><th>Categoría</th>
                <th>Monto</th><th>Proveedor</th><th>Pago</th>
            </tr></thead><tbody>"""
            for e in egresos:
                tbl += f"""<tr>
                    <td class="mono" style="color:#7a7f9a;">{e['fecha']}</td>
                    <td><strong>{e['descripcion']}</strong></td>
                    <td><span class="badge b-yellow">{e['categoria']}</span></td>
                    <td class="mono" style="color:#e8344a;">${e['monto']:,.0f}</td>
                    <td style="color:#7a7f9a;">{e.get('proveedor') or '—'}</td>
                    <td>{e.get('metodo_pago','—')}</td>
                </tr>"""
            tbl += "</tbody></table>"
            st.markdown(tbl, unsafe_allow_html=True)

    with tab3:
        mes = st.text_input("Mes (YYYY-MM)", value=date.today().strftime("%Y-%m"))
        cats = db.get_egresos_por_categoria(mes)
        if not cats:
            st.info("Sin egresos ese mes.")
        else:
            total_mes = sum(c["total"] for c in cats)
            st.metric(f"Total egresos {mes}", f"${total_mes:,.0f}")
            for c in cats:
                pct = (c["total"] / total_mes * 100) if total_mes else 0
                st.markdown(
                    f"""<div style="display:flex;align-items:center;gap:1rem;margin-bottom:.65rem;">
                        <div style="width:170px;font-size:.85rem;">{c['categoria']}</div>
                        <div style="flex:1;background:#2e3347;border-radius:3px;height:8px;">
                          <div style="width:{pct:.0f}%;height:100%;background:#ffc233;border-radius:3px;"></div>
                        </div>
                        <div class="mono" style="width:110px;text-align:right;color:#e8344a;">${c['total']:,.0f}</div>
                        <div style="width:50px;color:#7a7f9a;font-size:.8rem;">{pct:.1f}%</div>
                    </div>""",
                    unsafe_allow_html=True
                )
