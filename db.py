"""
================================================================================
DATABASE LAYER - database/db.py
================================================================================
PRINCIPIO DE RESPONSABILIDAD ÚNICA (SRP):
  Este archivo es el ÚNICO punto de contacto con SQLite.
  Los módulos de UI y lógica de negocio importan DatabaseManager y llaman
  sus métodos — nunca escriben SQL directamente.

DIAGRAMA DE TABLAS:
  ingredientes ──< receta_ingredientes >── recetas
  recetas      ──< detalle_venta       >── ventas
  categorias_egreso ──< egresos
  ingresos_extra (ventas no relacionadas con recetas)

MIGRACIÓN A POSTGRESQL:
  Solo cambiar get_connection() para usar psycopg2/SQLAlchemy.
  Los tipos: AUTOINCREMENT→SERIAL, REAL→NUMERIC, TEXT→VARCHAR.
================================================================================
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional

# ── Ruta de la base de datos ──────────────────────────────────────────────────
DB_DIR  = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "fast_erp.db"


class DatabaseManager:
    """
    Capa de acceso a datos (DAL).
    Cada método agrupa una operación de negocio completa.
    """

    def __init__(self, path: str = None):
        self.path = str(path or DB_PATH)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    # ── Conexión ──────────────────────────────────────────────────────────────
    def get_connection(self) -> sqlite3.Connection:
        """
        Retorna conexión con row_factory para acceso por nombre de columna.
        PRAGMA foreign_keys activa integridad referencial (OFF por defecto en SQLite).
        PRAGMA journal_mode=WAL mejora concurrencia lectura/escritura.
        """
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    # ══════════════════════════════════════════════════════════════════════════
    # DDL — CREACIÓN DE TABLAS
    # ══════════════════════════════════════════════════════════════════════════
    def create_tables(self):
        """
        Crea todas las tablas si no existen.
        Ejecutar una sola vez al iniciar la app.
        """
        with self.get_connection() as conn:
            conn.executescript("""

            -- ── INGREDIENTES (insumos base) ──────────────────────────────────
            -- Cada fila es un insumo comprable a un proveedor.
            -- 'unidad' determina cómo se mide: kg, gr, unidad, lt, ml, etc.
            -- 'stock_minimo' dispara alertas cuando stock_actual lo toca.
            CREATE TABLE IF NOT EXISTS ingredientes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre          TEXT    NOT NULL UNIQUE,
                descripcion     TEXT,
                unidad          TEXT    NOT NULL DEFAULT 'unidad',
                stock_actual    REAL    NOT NULL DEFAULT 0.0,
                stock_minimo    REAL    NOT NULL DEFAULT 1.0,
                costo_unitario  REAL    NOT NULL DEFAULT 0.0,
                proveedor       TEXT,
                activo          INTEGER NOT NULL DEFAULT 1,
                creado_en       TEXT    DEFAULT (date('now'))
            );

            -- ── RECETAS (escandallos / productos finales) ─────────────────────
            -- Un producto vendible que se compone de varios ingredientes.
            CREATE TABLE IF NOT EXISTS recetas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre          TEXT    NOT NULL UNIQUE,
                descripcion     TEXT,
                categoria       TEXT    DEFAULT 'Hamburguesa',
                precio_venta    REAL    NOT NULL DEFAULT 0.0,
                activa          INTEGER NOT NULL DEFAULT 1,
                creado_en       TEXT    DEFAULT (date('now'))
            );

            -- ── RECETA_INGREDIENTES (detalle del escandallo) ──────────────────
            -- Por cada receta, qué ingredientes usa y en qué cantidad.
            -- La cantidad está en la misma unidad que el ingrediente.
            CREATE TABLE IF NOT EXISTS receta_ingredientes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                receta_id       INTEGER NOT NULL REFERENCES recetas(id)     ON DELETE CASCADE,
                ingrediente_id  INTEGER NOT NULL REFERENCES ingredientes(id),
                cantidad        REAL    NOT NULL,
                UNIQUE(receta_id, ingrediente_id)
            );

            -- ── VENTAS ────────────────────────────────────────────────────────
            -- Cada venta de una receta: descuenta stock automáticamente.
            CREATE TABLE IF NOT EXISTS ventas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                receta_id       INTEGER NOT NULL REFERENCES recetas(id),
                cantidad        INTEGER NOT NULL DEFAULT 1,
                precio_unitario REAL    NOT NULL,
                descuento       REAL    DEFAULT 0.0,
                total           REAL    NOT NULL,
                metodo_pago     TEXT    DEFAULT 'efectivo',
                notas           TEXT,
                fecha           TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            -- ── MOVIMIENTOS_STOCK ─────────────────────────────────────────────
            -- Log de auditoría: cada cambio de inventario queda registrado.
            -- tipo: 'venta', 'compra', 'ajuste', 'merma', 'inicial'
            CREATE TABLE IF NOT EXISTS movimientos_stock (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ingrediente_id  INTEGER NOT NULL REFERENCES ingredientes(id),
                tipo            TEXT    NOT NULL,
                cantidad        REAL    NOT NULL,   -- (+) entrada, (-) salida
                stock_antes     REAL,
                stock_despues   REAL,
                ref_id          INTEGER,            -- id de venta, egreso, etc.
                ref_tipo        TEXT,
                notas           TEXT,
                fecha           TEXT    DEFAULT (datetime('now'))
            );

            -- ── EGRESOS ───────────────────────────────────────────────────────
            -- Gastos del negocio: compras, servicios, nómina, etc.
            -- categoria: 'compra_ingredientes', 'servicios', 'nomina', 'arriendo', 'otro'
            CREATE TABLE IF NOT EXISTS egresos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                descripcion     TEXT    NOT NULL,
                categoria       TEXT    NOT NULL DEFAULT 'otro',
                monto           REAL    NOT NULL,
                proveedor       TEXT,
                metodo_pago     TEXT    DEFAULT 'efectivo',
                comprobante     TEXT,
                notas           TEXT,
                fecha           TEXT    NOT NULL DEFAULT (date('now'))
            );

            -- ── INGRESOS_EXTRA ────────────────────────────────────────────────
            -- Ingresos que NO son ventas de recetas (ej. domicilios, eventos).
            CREATE TABLE IF NOT EXISTS ingresos_extra (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                descripcion     TEXT    NOT NULL,
                categoria       TEXT    DEFAULT 'otro',
                monto           REAL    NOT NULL,
                fecha           TEXT    NOT NULL DEFAULT (date('now'))
            );
            """)

    # ══════════════════════════════════════════════════════════════════════════
    # DATOS DE DEMOSTRACIÓN
    # ══════════════════════════════════════════════════════════════════════════
    def seed_demo_data(self):
        """
        Inserta datos de ejemplo solo si la BD está vacía.
        Simula una hamburguesería colombiana con insumos y 2 productos estrella.
        """
        with self.get_connection() as conn:
            if conn.execute("SELECT COUNT(*) FROM ingredientes").fetchone()[0] > 0:
                return  # Ya tiene datos

            # ── Ingredientes base ─────────────────────────────────────────────
            ings = [
                # nombre,            unidad,   stock, min, costo,  proveedor
                ("Pan para hamburguesa", "unidad", 50,  10, 800,   "Panadería El Maíz"),
                ("Pan para perro",       "unidad", 40,  10, 600,   "Panadería El Maíz"),
                ("Carne de res (150g)",  "porción", 30, 8,  4500,  "Carnes El Rodeo"),
                ("Salchicha tipo alemán","unidad", 35,  8,  2800,  "Carnes El Rodeo"),
                ("Queso amarillo",       "loncha",  60, 15, 450,   "Lácteos Norte"),
                ("Lechuga",              "gr",     500, 100, 15,   "Verduras Frescas"),
                ("Tomate",               "gr",     400, 80,  12,   "Verduras Frescas"),
                ("Cebolla caramelizada", "gr",     300, 50,  18,   "Producción propia"),
                ("Salsa especial",       "ml",     500, 100, 10,   "Producción propia"),
                ("Mayonesa",             "ml",     400, 80,  8,    "Dist. Andina"),
                ("Mostaza",              "ml",     300, 60,  7,    "Dist. Andina"),
                ("Papas fritas (porción)","porción",25, 5,  2200,  "Dist. Andina"),
                ("Gaseosa 350ml",        "unidad", 48,  12, 1200,  "Postobon"),
            ]
            conn.executemany(
                """INSERT INTO ingredientes
                   (nombre, unidad, stock_actual, stock_minimo, costo_unitario, proveedor)
                   VALUES (?,?,?,?,?,?)""", ings
            )

            # ── Recetas (productos del menú) ──────────────────────────────────
            recetas = [
                ("Hamburguesa Clásica",   "La clásica de siempre",          "Hamburguesa", 15000),
                ("Hamburguesa Especial",  "Con queso doble y salsa especial","Hamburguesa", 19000),
                ("Perro Caliente Simple", "Salchicha, mostaza y ketchup",   "Perro",       9000),
                ("Perro Caliente Loco",   "Todo incluido, papas y gaseosa", "Perro",       16500),
                ("Combo Clásico",         "Hamburguesa + Papas + Gaseosa",  "Combo",       22000),
            ]
            conn.executemany(
                "INSERT INTO recetas (nombre, descripcion, categoria, precio_venta) VALUES (?,?,?,?)",
                recetas
            )

            # ── Ingredientes por receta (escandallo) ──────────────────────────
            # Hamburguesa Clásica (id=1): pan, carne, lechuga, tomate, mayonesa
            ri = [
                (1, 1, 1),    # 1 pan hamburguesa
                (1, 3, 1),    # 1 porción carne
                (1, 6, 30),   # 30g lechuga
                (1, 7, 40),   # 40g tomate
                (1, 10, 20),  # 20ml mayonesa
                # Hamburguesa Especial (id=2): + queso doble + salsa + cebolla
                (2, 1, 1),
                (2, 3, 1),
                (2, 5, 2),    # 2 lonchas queso
                (2, 6, 30),
                (2, 7, 40),
                (2, 8, 25),   # 25g cebolla caramelizada
                (2, 9, 30),   # 30ml salsa especial
                # Perro Simple (id=3)
                (3, 2, 1),    # 1 pan perro
                (3, 4, 1),    # 1 salchicha
                (3, 11, 15),  # 15ml mostaza
                (3, 10, 10),  # 10ml mayonesa
                # Perro Loco (id=4)
                (4, 2, 1),
                (4, 4, 1),
                (4, 5, 1),    # 1 loncha queso
                (4, 8, 20),
                (4, 9, 20),
                (4, 11, 15),
                (4, 10, 10),
                (4, 12, 1),   # papas
                (4, 13, 1),   # gaseosa
                # Combo Clásico (id=5) = Hamburguesa + Papas + Gaseosa
                (5, 1, 1),
                (5, 3, 1),
                (5, 6, 30),
                (5, 7, 40),
                (5, 10, 20),
                (5, 12, 1),
                (5, 13, 1),
            ]
            conn.executemany(
                "INSERT OR IGNORE INTO receta_ingredientes (receta_id, ingrediente_id, cantidad) VALUES (?,?,?)",
                ri
            )

            # ── Egresos de ejemplo (últimos 7 días) ───────────────────────────
            hoy = date.today()
            egresos = [
                ("Compra carnes semana",   "compra_ingredientes", 85000, "Carnes El Rodeo",   hoy.isoformat()),
                ("Compra panes semana",    "compra_ingredientes", 32000, "Panadería El Maíz", (hoy - timedelta(1)).isoformat()),
                ("Gas domiciliario",       "servicios",           45000, None,                (hoy - timedelta(2)).isoformat()),
                ("Salario cocinero",       "nomina",             350000, None,                (hoy - timedelta(3)).isoformat()),
                ("Compra bebidas",         "compra_ingredientes", 58000, "Postobon",          (hoy - timedelta(4)).isoformat()),
                ("Arriendo local",         "arriendo",           800000, None,                (hoy - timedelta(5)).isoformat()),
            ]
            conn.executemany(
                "INSERT INTO egresos (descripcion, categoria, monto, proveedor, fecha) VALUES (?,?,?,?,?)",
                egresos
            )

    # ══════════════════════════════════════════════════════════════════════════
    # INGREDIENTES
    # ══════════════════════════════════════════════════════════════════════════
    def get_ingredientes(self, solo_activos: bool = True) -> list:
        filtro = "WHERE activo=1" if solo_activos else ""
        with self.get_connection() as conn:
            rows = conn.execute(f"SELECT * FROM ingredientes {filtro} ORDER BY nombre").fetchall()
            return [dict(r) for r in rows]

    def get_ingrediente(self, ing_id: int) -> Optional[dict]:
        with self.get_connection() as conn:
            r = conn.execute("SELECT * FROM ingredientes WHERE id=?", (ing_id,)).fetchone()
            return dict(r) if r else None

    def crear_ingrediente(self, datos: dict) -> int:
        """
        Crea ingrediente y registra movimiento inicial de stock.
        Retorna el id del nuevo ingrediente.
        """
        with self.get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO ingredientes
                   (nombre, descripcion, unidad, stock_actual, stock_minimo, costo_unitario, proveedor)
                   VALUES (?,?,?,?,?,?,?)""",
                (datos["nombre"], datos.get("descripcion"), datos["unidad"],
                 datos.get("stock_actual", 0), datos["stock_minimo"],
                 datos["costo_unitario"], datos.get("proveedor"))
            )
            ing_id = cur.lastrowid

        # Registrar stock inicial como movimiento
        if datos.get("stock_actual", 0) > 0:
            self._registrar_movimiento(
                ing_id, "inicial", datos["stock_actual"],
                0, datos["stock_actual"], notas="Stock inicial al crear"
            )
        return ing_id

    def actualizar_ingrediente(self, ing_id: int, datos: dict):
        with self.get_connection() as conn:
            conn.execute(
                """UPDATE ingredientes SET
                   nombre=?, descripcion=?, unidad=?, stock_minimo=?,
                   costo_unitario=?, proveedor=?
                   WHERE id=?""",
                (datos["nombre"], datos.get("descripcion"), datos["unidad"],
                 datos["stock_minimo"], datos["costo_unitario"],
                 datos.get("proveedor"), ing_id)
            )

    def ajustar_stock_ingrediente(self, ing_id: int, delta: float,
                                   tipo: str, notas: str = "",
                                   ref_id: int = None, ref_tipo: str = None):
        """
        Ajusta el stock de un ingrediente en ±delta.
        delta positivo = entrada (compra), negativo = salida (venta/merma).
        Registra el movimiento en el log de auditoría.
        """
        with self.get_connection() as conn:
            antes = conn.execute(
                "SELECT stock_actual FROM ingredientes WHERE id=?", (ing_id,)
            ).fetchone()[0]
            despues = max(0.0, round(antes + delta, 4))
            conn.execute(
                "UPDATE ingredientes SET stock_actual=? WHERE id=?",
                (despues, ing_id)
            )
        self._registrar_movimiento(ing_id, tipo, delta, antes, despues,
                                    ref_id, ref_tipo, notas)

    def _registrar_movimiento(self, ing_id: int, tipo: str, cantidad: float,
                               antes: float, despues: float,
                               ref_id: int = None, ref_tipo: str = None,
                               notas: str = ""):
        """Escribe en el log de auditoría. Método privado."""
        with self.get_connection() as conn:
            conn.execute(
                """INSERT INTO movimientos_stock
                   (ingrediente_id, tipo, cantidad, stock_antes, stock_despues,
                    ref_id, ref_tipo, notas)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (ing_id, tipo, cantidad, antes, despues, ref_id, ref_tipo, notas)
            )

    def get_stock_critico(self) -> list:
        """Ingredientes cuyo stock_actual <= stock_minimo."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM ingredientes
                WHERE activo=1 AND stock_actual <= stock_minimo
                ORDER BY (stock_actual / NULLIF(stock_minimo,0)) ASC
            """).fetchall()
            return [dict(r) for r in rows]

    # ══════════════════════════════════════════════════════════════════════════
    # RECETAS
    # ══════════════════════════════════════════════════════════════════════════
    def get_recetas(self) -> list:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM recetas WHERE activa=1 ORDER BY categoria, nombre"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_receta_completa(self, receta_id: int) -> dict:
        """
        Retorna receta con:
          - Lista de ingredientes y sus costos por porción
          - Costo total de producción
          - Margen bruto
          - Food cost %
        """
        with self.get_connection() as conn:
            receta = dict(conn.execute(
                "SELECT * FROM recetas WHERE id=?", (receta_id,)
            ).fetchone())

            ings = conn.execute("""
                SELECT ri.cantidad,
                       i.id as ing_id, i.nombre, i.unidad,
                       i.costo_unitario, i.stock_actual,
                       ROUND(ri.cantidad * i.costo_unitario, 2) as subtotal
                FROM receta_ingredientes ri
                JOIN ingredientes i ON ri.ingrediente_id = i.id
                WHERE ri.receta_id = ?
            """, (receta_id,)).fetchall()

        receta["ingredientes"]  = [dict(r) for r in ings]
        receta["costo_total"]   = round(sum(r["subtotal"] for r in ings), 2)
        receta["margen"]        = round(receta["precio_venta"] - receta["costo_total"], 2)
        receta["food_cost_pct"] = round(
            receta["costo_total"] / receta["precio_venta"] * 100, 1
        ) if receta["precio_venta"] > 0 else 0
        return receta

    def crear_receta(self, datos: dict, ingredientes: list) -> int:
        """Transacción atómica: crea receta + detalle ingredientes."""
        with self.get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO recetas (nombre, descripcion, categoria, precio_venta) VALUES (?,?,?,?)",
                (datos["nombre"], datos.get("descripcion"),
                 datos.get("categoria", "Hamburguesa"), datos["precio_venta"])
            )
            rid = cur.lastrowid
            conn.executemany(
                "INSERT OR IGNORE INTO receta_ingredientes (receta_id, ingrediente_id, cantidad) VALUES (?,?,?)",
                [(rid, i["ing_id"], i["cantidad"]) for i in ingredientes]
            )
        return rid

    def verificar_stock_receta(self, receta_id: int, porciones: int = 1) -> dict:
        """
        Verifica si hay stock suficiente para preparar N porciones.
        Retorna {'puede': bool, 'faltantes': list}
        """
        receta = self.get_receta_completa(receta_id)
        faltantes = []
        for ing in receta["ingredientes"]:
            necesario = ing["cantidad"] * porciones
            if ing["stock_actual"] < necesario:
                faltantes.append({
                    "nombre":    ing["nombre"],
                    "necesario": necesario,
                    "disponible": ing["stock_actual"],
                })
        return {"puede": len(faltantes) == 0, "faltantes": faltantes}

    # ══════════════════════════════════════════════════════════════════════════
    # VENTAS — PROCESO CENTRAL DEL SISTEMA
    # ══════════════════════════════════════════════════════════════════════════
    def registrar_venta(self, receta_id: int, cantidad: int,
                         metodo_pago: str = "efectivo",
                         descuento: float = 0.0, notas: str = "") -> dict:
        """
        FLUJO COMPLETO DE UNA VENTA:
          1. Verifica stock suficiente
          2. Crea registro en tabla ventas
          3. Descuenta cada ingrediente del stock
          4. Registra movimientos de auditoría
        Es ATÓMICA: si algo falla, nada queda guardado.
        """
        # Paso 1: verificar stock
        check = self.verificar_stock_receta(receta_id, cantidad)
        if not check["puede"]:
            return {"ok": False, "error": "Stock insuficiente",
                    "faltantes": check["faltantes"]}

        receta = self.get_receta_completa(receta_id)
        total = round(receta["precio_venta"] * cantidad * (1 - descuento / 100), 2)

        # Paso 2: insertar venta
        with self.get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO ventas
                   (receta_id, cantidad, precio_unitario, descuento, total, metodo_pago, notas)
                   VALUES (?,?,?,?,?,?,?)""",
                (receta_id, cantidad, receta["precio_venta"], descuento, total,
                 metodo_pago, notas)
            )
            venta_id = cur.lastrowid

        # Paso 3 y 4: descontar cada ingrediente
        for ing in receta["ingredientes"]:
            self.ajustar_stock_ingrediente(
                ing_id=ing["ing_id"],
                delta=-(ing["cantidad"] * cantidad),
                tipo="venta",
                notas=f"Venta #{venta_id} · {receta['nombre']} ×{cantidad}",
                ref_id=venta_id,
                ref_tipo="venta"
            )

        return {"ok": True, "venta_id": venta_id, "total": total}

    def get_ventas(self, fecha_desde: str = None, fecha_hasta: str = None,
                   limit: int = 100) -> list:
        cond = ""
        params = []
        if fecha_desde:
            cond += " AND date(v.fecha) >= ?" ; params.append(fecha_desde)
        if fecha_hasta:
            cond += " AND date(v.fecha) <= ?" ; params.append(fecha_hasta)

        with self.get_connection() as conn:
            rows = conn.execute(f"""
                SELECT v.*, r.nombre as receta_nombre, r.categoria
                FROM ventas v JOIN recetas r ON v.receta_id = r.id
                WHERE 1=1 {cond}
                ORDER BY v.fecha DESC LIMIT ?
            """, (*params, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_ventas_resumen_dia(self) -> dict:
        """Métricas del día actual para el dashboard."""
        with self.get_connection() as conn:
            hoy = date.today().isoformat()
            total = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM ventas WHERE date(fecha)=?", (hoy,)
            ).fetchone()[0]
            cant = conn.execute(
                "SELECT COALESCE(SUM(cantidad),0) FROM ventas WHERE date(fecha)=?", (hoy,)
            ).fetchone()[0]
            por_receta = conn.execute("""
                SELECT r.nombre, SUM(v.cantidad) as unidades, SUM(v.total) as total
                FROM ventas v JOIN recetas r ON v.receta_id = r.id
                WHERE date(v.fecha) = ?
                GROUP BY r.id ORDER BY total DESC
            """, (hoy,)).fetchall()
        return {
            "total_dia": total,
            "unidades_dia": cant,
            "por_receta": [dict(r) for r in por_receta]
        }

    # ══════════════════════════════════════════════════════════════════════════
    # EGRESOS
    # ══════════════════════════════════════════════════════════════════════════
    def registrar_egreso(self, datos: dict) -> int:
        """
        Registra un gasto.
        Si la categoría es 'compra_ingredientes', opcionalmente actualiza stock.
        """
        with self.get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO egresos
                   (descripcion, categoria, monto, proveedor, metodo_pago, comprobante, notas, fecha)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (datos["descripcion"], datos["categoria"], datos["monto"],
                 datos.get("proveedor"), datos.get("metodo_pago", "efectivo"),
                 datos.get("comprobante"), datos.get("notas"),
                 datos.get("fecha", date.today().isoformat()))
            )
            return cur.lastrowid

    def get_egresos(self, fecha_desde: str = None, fecha_hasta: str = None) -> list:
        cond, params = "", []
        if fecha_desde: cond += " AND fecha >= ?"; params.append(fecha_desde)
        if fecha_hasta: cond += " AND fecha <= ?"; params.append(fecha_hasta)
        with self.get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM egresos WHERE 1=1 {cond} ORDER BY fecha DESC LIMIT 200",
                params
            ).fetchall()
        return [dict(r) for r in rows]

    def get_egresos_por_categoria(self, mes: str = None) -> list:
        """Agrupa egresos por categoría para el período indicado (YYYY-MM)."""
        filtro = f"WHERE strftime('%Y-%m', fecha) = '{mes}'" if mes else ""
        with self.get_connection() as conn:
            rows = conn.execute(f"""
                SELECT categoria, COUNT(*) as n, COALESCE(SUM(monto),0) as total
                FROM egresos {filtro}
                GROUP BY categoria ORDER BY total DESC
            """).fetchall()
        return [dict(r) for r in rows]

    # ══════════════════════════════════════════════════════════════════════════
    # FOOD COST — ANÁLISIS DE RENTABILIDAD
    # ══════════════════════════════════════════════════════════════════════════
    def get_food_cost_todas_recetas(self) -> list:
        """
        Retorna análisis food cost de todas las recetas activas:
          food_cost_pct = (costo_producción / precio_venta) × 100
          meta industria comidas rápidas: 25–35%
        """
        recetas = self.get_recetas()
        resultado = []
        for r in recetas:
            rc = self.get_receta_completa(r["id"])
            resultado.append({
                "id":           rc["id"],
                "nombre":       rc["nombre"],
                "categoria":    rc["categoria"],
                "precio_venta": rc["precio_venta"],
                "costo_total":  rc["costo_total"],
                "margen":       rc["margen"],
                "food_cost_pct":rc["food_cost_pct"],
                "estado":       (
                    "óptimo"   if rc["food_cost_pct"] <= 30 else
                    "aceptable" if rc["food_cost_pct"] <= 40 else
                    "revisar"
                ),
            })
        resultado.sort(key=lambda x: x["food_cost_pct"])
        return resultado

    def get_rentabilidad_periodo(self, fecha_desde: str, fecha_hasta: str) -> dict:
        """
        P&L simplificado de un período:
          ingresos_ventas − egresos = utilidad_bruta
        """
        with self.get_connection() as conn:
            ventas_total = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM ventas WHERE date(fecha) BETWEEN ? AND ?",
                (fecha_desde, fecha_hasta)
            ).fetchone()[0]

            egresos_total = conn.execute(
                "SELECT COALESCE(SUM(monto),0) FROM egresos WHERE fecha BETWEEN ? AND ?",
                (fecha_desde, fecha_hasta)
            ).fetchone()[0]

            ventas_cnt = conn.execute(
                "SELECT COALESCE(SUM(cantidad),0) FROM ventas WHERE date(fecha) BETWEEN ? AND ?",
                (fecha_desde, fecha_hasta)
            ).fetchone()[0]

            egresos_cat = conn.execute("""
                SELECT categoria, COALESCE(SUM(monto),0) as total
                FROM egresos WHERE fecha BETWEEN ? AND ?
                GROUP BY categoria ORDER BY total DESC
            """, (fecha_desde, fecha_hasta)).fetchall()

        utilidad = ventas_total - egresos_total
        margen_pct = (utilidad / ventas_total * 100) if ventas_total > 0 else 0

        return {
            "ventas_total":   ventas_total,
            "egresos_total":  egresos_total,
            "utilidad_bruta": utilidad,
            "margen_pct":     round(margen_pct, 1),
            "unidades_vendidas": ventas_cnt,
            "egresos_por_cat": [dict(r) for r in egresos_cat],
        }

    # ══════════════════════════════════════════════════════════════════════════
    # DASHBOARD
    # ══════════════════════════════════════════════════════════════════════════
    def get_dashboard_metrics(self) -> dict:
        hoy  = date.today().isoformat()
        mes_inicio = date.today().replace(day=1).isoformat()

        with self.get_connection() as conn:
            ventas_hoy = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM ventas WHERE date(fecha)=?", (hoy,)
            ).fetchone()[0]
            ventas_mes = conn.execute(
                "SELECT COALESCE(SUM(total),0) FROM ventas WHERE date(fecha)>=?", (mes_inicio,)
            ).fetchone()[0]
            egresos_mes = conn.execute(
                "SELECT COALESCE(SUM(monto),0) FROM egresos WHERE fecha>=?", (mes_inicio,)
            ).fetchone()[0]
            n_criticos = conn.execute(
                "SELECT COUNT(*) FROM ingredientes WHERE activo=1 AND stock_actual<=stock_minimo"
            ).fetchone()[0]
            n_recetas = conn.execute(
                "SELECT COUNT(*) FROM recetas WHERE activa=1"
            ).fetchone()[0]
            valor_inv = conn.execute(
                "SELECT COALESCE(SUM(stock_actual*costo_unitario),0) FROM ingredientes WHERE activo=1"
            ).fetchone()[0]

        return {
            "ventas_hoy":    ventas_hoy,
            "ventas_mes":    ventas_mes,
            "egresos_mes":   egresos_mes,
            "utilidad_mes":  ventas_mes - egresos_mes,
            "n_criticos":    n_criticos,
            "n_recetas":     n_recetas,
            "valor_inventario": valor_inv,
        }
