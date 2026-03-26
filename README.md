# 🍔 FastERP — Sistema de Gestión para Comidas Rápidas

ERP liviano para hamburgueserías y negocios de comidas rápidas.
Construido con **Python · Streamlit · SQLite** siguiendo principio de responsabilidad única.

---

## 🚀 Instalación

```bash
pip install -r requirements.txt
streamlit run app.py
```

Abre: **http://localhost:8501** — Carga datos demo automáticamente.

---

## 📁 Estructura

```
fast_erp/
├── app.py                  # Router principal + CSS global
├── requirements.txt
├── data/fast_erp.db        # SQLite — auto-creado al primer arranque
├── database/
│   └── db.py               # TODA la lógica SQL (DAL)
└── modules/
    ├── dashboard.py         # KPIs diarios + alertas rápidas
    ├── ingredientes.py      # CRUD de insumos + ajuste de stock
    ├── recetas.py           # Escandallos + food cost por producto
    ├── ventas.py            # Registro ventas → descuento automático
    ├── egresos.py           # Gastos del negocio por categoría
    ├── food_cost.py         # Food Cost % + P&L del período
    └── alertas.py           # Stock crítico con acción sugerida
```

---

## 🏗️ Principios de Diseño

### SRP — Responsabilidad Única
- `database/db.py` es el ÚNICO archivo que toca SQLite
- Cada `modules/*.py` solo contiene código de UI (Streamlit)
- Separación total: cambiar la BD no requiere tocar la UI

### Transacciones Atómicas
- `registrar_venta()` usa una sola transacción: si algo falla, nada queda guardado
- Stock siempre consistente con las ventas registradas

### Log de Auditoría
- Tabla `movimientos_stock`: cada cambio de inventario queda trazado
- Tipo: `venta`, `compra`, `ajuste`, `merma`, `inicial`

---

## 📐 Diagrama de Base de Datos

```
ingredientes ──< receta_ingredientes >── recetas
                                              │
                                         ventas
                                              │
                                    movimientos_stock

egresos (independiente)
ingresos_extra (independiente)
```

---

## 📊 Fórmulas de Negocio

| Métrica | Fórmula |
|---------|---------|
| Costo producción | Σ (cantidad_ing × costo_unitario) |
| Food Cost % | (Costo producción / Precio venta) × 100 |
| Margen bruto | Precio venta − Costo producción |
| Utilidad período | Total ventas − Total egresos |

**Referencia industria (comidas rápidas):**
- Food Cost óptimo: ≤ 30%
- Food Cost aceptable: 30–40%
- Food Cost a revisar: > 40%

---

## ☁️ Migración a la Nube

Solo cambiar `database/db.py → get_connection()`:

```python
# Para PostgreSQL
import psycopg2
conn = psycopg2.connect("postgresql://user:pass@host/db")

# Para MySQL
import mysql.connector
conn = mysql.connector.connect(host="...", user="...", password="...", database="...")
```

El resto del sistema no requiere cambios.
