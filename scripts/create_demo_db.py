"""
Create a SQLite demo database with realistic MES/WMS manufacturing data.

Usage:
    python scripts/create_demo_db.py

Creates ./data/demo.db with 8 tables of interconnected manufacturing data.
Idempotent — drops and recreates all tables on each run.
"""

import os
import sqlite3
import random
from datetime import date, timedelta

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "demo.db")

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

TABLES_DDL = [
    """
    CREATE TABLE PRODUCTION_LINES (
        LINE_ID     TEXT PRIMARY KEY,
        LINE_NAME   TEXT NOT NULL,
        LINE_TYPE   TEXT NOT NULL CHECK(LINE_TYPE IN ('SMT','ASSEMBLY','PACKAGING')),
        CAPACITY_PER_HOUR INTEGER NOT NULL,
        STATUS      TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE PRODUCTS (
        PROD_CODE   TEXT PRIMARY KEY,
        PROD_NAME   TEXT NOT NULL,
        CATEGORY    TEXT NOT NULL,
        UNIT_PRICE  REAL NOT NULL
    )
    """,
    """
    CREATE TABLE PRODUCTION_ORDERS (
        ORDER_ID    TEXT PRIMARY KEY,
        LINE_ID     TEXT NOT NULL REFERENCES PRODUCTION_LINES(LINE_ID),
        PROD_CODE   TEXT NOT NULL REFERENCES PRODUCTS(PROD_CODE),
        ORDER_QTY   INTEGER NOT NULL,
        GOOD_QTY    INTEGER NOT NULL,
        DEFECT_QTY  INTEGER NOT NULL,
        STATUS      TEXT NOT NULL CHECK(STATUS IN ('COMPLETED','IN_PROGRESS','PLANNED')),
        START_DATE  TEXT,
        END_DATE    TEXT
    )
    """,
    """
    CREATE TABLE DEFECTS (
        DEFECT_ID     TEXT PRIMARY KEY,
        ORDER_ID      TEXT NOT NULL REFERENCES PRODUCTION_ORDERS(ORDER_ID),
        DEFECT_TYPE   TEXT NOT NULL CHECK(DEFECT_TYPE IN ('SOLDER','MISSING_PART','ALIGNMENT','SCRATCH','CRACK')),
        DEFECT_COUNT  INTEGER NOT NULL,
        DETECTED_BY   TEXT NOT NULL CHECK(DETECTED_BY IN ('AOI','MANUAL','XRAY')),
        DETECTED_DATE TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE EQUIPMENT (
        EQUIP_ID          TEXT PRIMARY KEY,
        EQUIP_NAME        TEXT NOT NULL,
        LINE_ID           TEXT NOT NULL REFERENCES PRODUCTION_LINES(LINE_ID),
        STATUS            TEXT NOT NULL CHECK(STATUS IN ('RUNNING','MAINTENANCE','IDLE')),
        LAST_MAINTENANCE  TEXT,
        NEXT_MAINTENANCE  TEXT
    )
    """,
    """
    CREATE TABLE WAREHOUSES (
        WH_ID     TEXT PRIMARY KEY,
        WH_NAME   TEXT NOT NULL,
        ZONE      TEXT NOT NULL CHECK(ZONE IN ('A','B','C')),
        CAPACITY  INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE ITEMS (
        ITEM_CODE  TEXT PRIMARY KEY,
        ITEM_NAME  TEXT NOT NULL,
        CATEGORY   TEXT NOT NULL CHECK(CATEGORY IN ('RAW_MATERIAL','COMPONENT','FINISHED')),
        UNIT       TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE INVENTORY (
        INV_ID        TEXT PRIMARY KEY,
        ITEM_CODE     TEXT NOT NULL REFERENCES ITEMS(ITEM_CODE),
        WH_ID         TEXT NOT NULL REFERENCES WAREHOUSES(WH_ID),
        QTY_ON_HAND   INTEGER NOT NULL,
        QTY_RESERVED  INTEGER NOT NULL,
        LAST_UPDATED  TEXT NOT NULL
    )
    """,
]

DROP_ORDER = [
    "INVENTORY", "ITEMS", "WAREHOUSES", "EQUIPMENT",
    "DEFECTS", "PRODUCTION_ORDERS", "PRODUCTS", "PRODUCTION_LINES",
]

# ---------------------------------------------------------------------------
# Seed data generators
# ---------------------------------------------------------------------------

random.seed(42)  # reproducible


def _d(y: int, m: int, d: int) -> str:
    """Return ISO date string."""
    return date(y, m, d).isoformat()


def seed_production_lines(cur: sqlite3.Cursor) -> None:
    rows = [
        ("LINE-A", "SMT Line Alpha",    "SMT",       120, "RUNNING"),
        ("LINE-B", "Assembly Line Beta", "ASSEMBLY",   80, "RUNNING"),
        ("LINE-C", "Packaging Line C",  "PACKAGING", 200, "RUNNING"),
    ]
    cur.executemany(
        "INSERT INTO PRODUCTION_LINES VALUES (?,?,?,?,?)", rows
    )


def seed_products(cur: sqlite3.Cursor) -> None:
    rows = [
        ("PRD-001", "PCB Controller v2",    "ELECTRONIC", 45.00),
        ("PRD-002", "Sensor Module A",       "ELECTRONIC", 28.50),
        ("PRD-003", "Power Supply Unit 12V", "POWER",      62.00),
        ("PRD-004", "LED Driver Board",      "ELECTRONIC", 33.75),
        ("PRD-005", "Enclosure Kit Standard","MECHANICAL",  18.00),
    ]
    cur.executemany(
        "INSERT INTO PRODUCTS VALUES (?,?,?,?)", rows
    )


def seed_production_orders(cur: sqlite3.Cursor) -> list[dict]:
    """Generate 30 production orders with a narrative.

    Story:
    - LINE-A (SMT): experienced solder-quality issues in March 2026,
      leading to elevated defect rates (8-15%). Feb and Apr are normal (~2%).
    - LINE-B (Assembly): consistently stable, defect rate ~1-3%.
    - LINE-C (Packaging): moderate scratch issues in late Feb, otherwise fine.
    """
    orders: list[dict] = []
    prod_codes = ["PRD-001", "PRD-002", "PRD-003", "PRD-004", "PRD-005"]
    order_num = 0

    # Helper to create one order
    def _make_order(
        line_id: str,
        prod_code: str,
        qty: int,
        defect_pct: float,
        status: str,
        start: date,
        duration_days: int,
    ) -> dict:
        nonlocal order_num
        order_num += 1
        good = int(qty * (1 - defect_pct))
        defect = qty - good
        end = start + timedelta(days=duration_days) if status == "COMPLETED" else None
        oid = f"WO-2026-{order_num:04d}"
        row = {
            "ORDER_ID": oid,
            "LINE_ID": line_id,
            "PROD_CODE": prod_code,
            "ORDER_QTY": qty,
            "GOOD_QTY": good,
            "DEFECT_QTY": defect,
            "STATUS": status,
            "START_DATE": start.isoformat(),
            "END_DATE": end.isoformat() if end else None,
        }
        return row

    # --- LINE-A (SMT) — 12 orders ---
    # Feb: normal
    orders.append(_make_order("LINE-A", "PRD-001", 500, 0.02, "COMPLETED", date(2026, 2, 3), 3))
    orders.append(_make_order("LINE-A", "PRD-002", 800, 0.03, "COMPLETED", date(2026, 2, 10), 4))
    orders.append(_make_order("LINE-A", "PRD-004", 350, 0.01, "COMPLETED", date(2026, 2, 18), 2))
    # March: solder crisis — defect spike
    orders.append(_make_order("LINE-A", "PRD-001", 600, 0.12, "COMPLETED", date(2026, 3, 2), 5))
    orders.append(_make_order("LINE-A", "PRD-002", 900, 0.15, "COMPLETED", date(2026, 3, 9), 6))
    orders.append(_make_order("LINE-A", "PRD-004", 450, 0.10, "COMPLETED", date(2026, 3, 16), 4))
    orders.append(_make_order("LINE-A", "PRD-001", 700, 0.08, "COMPLETED", date(2026, 3, 22), 4))
    orders.append(_make_order("LINE-A", "PRD-003", 300, 0.13, "COMPLETED", date(2026, 3, 28), 3))
    # April: recovery
    orders.append(_make_order("LINE-A", "PRD-001", 550, 0.02, "COMPLETED", date(2026, 4, 1), 3))
    orders.append(_make_order("LINE-A", "PRD-002", 650, 0.03, "IN_PROGRESS", date(2026, 4, 5), 0))
    orders.append(_make_order("LINE-A", "PRD-004", 400, 0.00, "PLANNED", date(2026, 4, 10), 0))
    orders.append(_make_order("LINE-A", "PRD-003", 500, 0.00, "PLANNED", date(2026, 4, 14), 0))

    # --- LINE-B (Assembly) — 10 orders, stable ---
    for i, (pc, qty) in enumerate([
        ("PRD-001", 400), ("PRD-003", 350), ("PRD-005", 600),
        ("PRD-002", 500), ("PRD-001", 450), ("PRD-005", 700),
        ("PRD-003", 300), ("PRD-004", 550), ("PRD-002", 380),
        ("PRD-005", 520),
    ]):
        start = date(2026, 2, 5) + timedelta(days=i * 7)
        status = "COMPLETED" if start < date(2026, 4, 1) else "IN_PROGRESS"
        defect_pct = random.uniform(0.01, 0.03)
        orders.append(_make_order("LINE-B", pc, qty, defect_pct, status, start, 3))

    # --- LINE-C (Packaging) — 8 orders ---
    # Late Feb: scratch issues
    orders.append(_make_order("LINE-C", "PRD-005", 1000, 0.02, "COMPLETED", date(2026, 2, 3), 2))
    orders.append(_make_order("LINE-C", "PRD-001", 800, 0.07, "COMPLETED", date(2026, 2, 20), 2))
    orders.append(_make_order("LINE-C", "PRD-003", 900, 0.06, "COMPLETED", date(2026, 2, 25), 2))
    # March: resolved
    orders.append(_make_order("LINE-C", "PRD-005", 1200, 0.01, "COMPLETED", date(2026, 3, 5), 2))
    orders.append(_make_order("LINE-C", "PRD-002", 750,  0.02, "COMPLETED", date(2026, 3, 15), 2))
    orders.append(_make_order("LINE-C", "PRD-001", 950,  0.01, "COMPLETED", date(2026, 3, 25), 2))
    # April
    orders.append(_make_order("LINE-C", "PRD-004", 600,  0.01, "IN_PROGRESS", date(2026, 4, 2), 0))
    orders.append(_make_order("LINE-C", "PRD-005", 1100, 0.00, "PLANNED", date(2026, 4, 8), 0))

    # Insert
    for o in orders:
        cur.execute(
            "INSERT INTO PRODUCTION_ORDERS VALUES (?,?,?,?,?,?,?,?,?)",
            (
                o["ORDER_ID"], o["LINE_ID"], o["PROD_CODE"],
                o["ORDER_QTY"], o["GOOD_QTY"], o["DEFECT_QTY"],
                o["STATUS"], o["START_DATE"], o["END_DATE"],
            ),
        )
    return orders


def seed_defects(cur: sqlite3.Cursor, orders: list[dict]) -> None:
    """Generate ~50 defect records linked to orders that have defects.

    Story-driven:
    - LINE-A March orders: predominantly SOLDER defects (detected by AOI/XRAY)
    - LINE-C late Feb: SCRATCH defects (detected MANUAL)
    - Others: random mix at low counts
    """
    defect_rows: list[tuple] = []
    defect_seq = 0

    smt_defect_types = ["SOLDER", "SOLDER", "SOLDER", "MISSING_PART", "ALIGNMENT"]
    smt_detectors = ["AOI", "AOI", "XRAY"]
    assy_defect_types = ["MISSING_PART", "ALIGNMENT", "CRACK"]
    assy_detectors = ["MANUAL", "AOI"]
    pkg_defect_types = ["SCRATCH", "SCRATCH", "CRACK"]
    pkg_detectors = ["MANUAL", "MANUAL", "AOI"]

    for o in orders:
        if o["DEFECT_QTY"] == 0:
            continue

        line = o["LINE_ID"]
        total_defects = o["DEFECT_QTY"]
        start = date.fromisoformat(o["START_DATE"])

        # Decide how many defect records to split into (1-3 records per order)
        n_records = min(random.randint(1, 3), total_defects)
        # Distribute defect counts
        counts = []
        remaining = total_defects
        for j in range(n_records):
            if j == n_records - 1:
                counts.append(remaining)
            else:
                c = random.randint(1, max(1, remaining - (n_records - j - 1)))
                counts.append(c)
                remaining -= c

        for c in counts:
            defect_seq += 1
            did = f"DEF-{defect_seq:04d}"

            if line == "LINE-A":
                dtype = random.choice(smt_defect_types)
                dby = random.choice(smt_detectors)
            elif line == "LINE-B":
                dtype = random.choice(assy_defect_types)
                dby = random.choice(assy_detectors)
            else:  # LINE-C
                dtype = random.choice(pkg_defect_types)
                dby = random.choice(pkg_detectors)

            det_date = start + timedelta(days=random.randint(0, 3))
            defect_rows.append((
                did, o["ORDER_ID"], dtype, c, dby, det_date.isoformat()
            ))

    # Trim to exactly 50 if over, or pad if under
    if len(defect_rows) > 50:
        defect_rows = defect_rows[:50]

    high_defect_orders = [o for o in orders if o["DEFECT_QTY"] > 20]
    while len(defect_rows) < 50 and high_defect_orders:
        o = random.choice(high_defect_orders)
        defect_seq += 1
        did = f"DEF-{defect_seq:04d}"
        start = date.fromisoformat(o["START_DATE"])
        line = o["LINE_ID"]

        if line == "LINE-A":
            dtype = random.choice(smt_defect_types)
            dby = random.choice(smt_detectors)
        elif line == "LINE-B":
            dtype = random.choice(assy_defect_types)
            dby = random.choice(assy_detectors)
        else:
            dtype = random.choice(pkg_defect_types)
            dby = random.choice(pkg_detectors)

        det_date = start + timedelta(days=random.randint(0, 5))
        defect_rows.append((
            did, o["ORDER_ID"], dtype, random.randint(1, 5), dby, det_date.isoformat()
        ))

    cur.executemany(
        "INSERT INTO DEFECTS VALUES (?,?,?,?,?,?)", defect_rows
    )


def seed_equipment(cur: sqlite3.Cursor) -> None:
    rows = [
        ("EQ-001", "SMT Printer SP-700",      "LINE-A", "RUNNING",     _d(2026, 3, 1),  _d(2026, 5, 1)),
        ("EQ-002", "Pick & Place PP-2000",     "LINE-A", "RUNNING",     _d(2026, 2, 15), _d(2026, 4, 15)),
        ("EQ-003", "Reflow Oven RF-450",       "LINE-A", "MAINTENANCE", _d(2026, 3, 20), _d(2026, 4, 10)),
        ("EQ-004", "Screw Driver SD-100",      "LINE-B", "RUNNING",     _d(2026, 3, 10), _d(2026, 5, 10)),
        ("EQ-005", "Torque Tester TT-50",      "LINE-B", "IDLE",        _d(2026, 1, 20), _d(2026, 4, 20)),
        ("EQ-006", "Shrink Wrapper SW-300",    "LINE-C", "RUNNING",     _d(2026, 3, 5),  _d(2026, 5, 5)),
    ]
    cur.executemany(
        "INSERT INTO EQUIPMENT VALUES (?,?,?,?,?,?)", rows
    )


def seed_warehouses(cur: sqlite3.Cursor) -> None:
    rows = [
        ("WH-01", "Raw Materials Warehouse", "A", 5000),
        ("WH-02", "Components Warehouse",    "B", 3000),
        ("WH-03", "Finished Goods Warehouse","C", 8000),
    ]
    cur.executemany(
        "INSERT INTO WAREHOUSES VALUES (?,?,?,?)", rows
    )


def seed_items(cur: sqlite3.Cursor) -> None:
    rows = [
        ("ITM-001", "Solder Paste Sn63/Pb37", "RAW_MATERIAL", "KG"),
        ("ITM-002", "FR-4 PCB Blank 10x10",   "RAW_MATERIAL", "PCS"),
        ("ITM-003", "Resistor 10K 0805",       "COMPONENT",    "PCS"),
        ("ITM-004", "Capacitor 100uF",         "COMPONENT",    "PCS"),
        ("ITM-005", "IC Microcontroller STM32", "COMPONENT",   "PCS"),
        ("ITM-006", "LED 5mm White",           "COMPONENT",    "PCS"),
        ("ITM-007", "PCB Controller v2 Assy",  "FINISHED",     "PCS"),
        ("ITM-008", "Sensor Module A Assy",    "FINISHED",     "PCS"),
    ]
    cur.executemany(
        "INSERT INTO ITEMS VALUES (?,?,?,?)", rows
    )


def seed_inventory(cur: sqlite3.Cursor) -> None:
    rows = [
        # Raw materials in WH-01
        ("INV-001", "ITM-001", "WH-01", 120,   30,  _d(2026, 4, 5)),
        ("INV-002", "ITM-002", "WH-01", 2500,  800, _d(2026, 4, 6)),
        # Components in WH-02
        ("INV-003", "ITM-003", "WH-02", 15000, 5000, _d(2026, 4, 5)),
        ("INV-004", "ITM-004", "WH-02", 8000,  2000, _d(2026, 4, 4)),
        ("INV-005", "ITM-005", "WH-02", 1200,  600,  _d(2026, 4, 6)),
        ("INV-006", "ITM-006", "WH-02", 20000, 3000, _d(2026, 4, 3)),
        # Finished goods in WH-03
        ("INV-007", "ITM-007", "WH-03", 340,   120,  _d(2026, 4, 6)),
        ("INV-008", "ITM-008", "WH-03", 580,   200,  _d(2026, 4, 5)),
        # Cross-warehouse stock (some items stored in multiple warehouses)
        ("INV-009", "ITM-003", "WH-01", 5000,  0,    _d(2026, 3, 28)),
        ("INV-010", "ITM-001", "WH-02", 50,    10,   _d(2026, 4, 1)),
        ("INV-011", "ITM-005", "WH-01", 300,   100,  _d(2026, 3, 30)),
        ("INV-012", "ITM-007", "WH-02", 45,    45,   _d(2026, 4, 2)),
        # Low-stock items for interesting queries
        ("INV-013", "ITM-002", "WH-02", 80,    75,   _d(2026, 4, 6)),
        ("INV-014", "ITM-004", "WH-01", 150,   140,  _d(2026, 4, 5)),
        ("INV-015", "ITM-006", "WH-03", 25,    20,   _d(2026, 4, 7)),
    ]
    cur.executemany(
        "INSERT INTO INVENTORY VALUES (?,?,?,?,?,?)", rows
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # Drop existing tables (reverse dependency order)
    for table in DROP_ORDER:
        cur.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()

    # Create tables
    for ddl in TABLES_DDL:
        cur.execute(ddl)
    conn.commit()

    # Seed data
    seed_production_lines(cur)
    seed_products(cur)
    orders = seed_production_orders(cur)
    seed_defects(cur, orders)
    seed_equipment(cur)
    seed_warehouses(cur)
    seed_items(cur)
    seed_inventory(cur)
    conn.commit()

    # Print stats
    print(f"\nDemo database created: {DB_PATH}")
    print("-" * 50)
    tables = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    for (table_name,) in tables:
        count = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  {table_name:<25s} {count:>5d} rows")
    print("-" * 50)

    # Quick story summary
    print("\nData story highlights:")
    # Line-A March defect rate
    row = cur.execute("""
        SELECT SUM(DEFECT_QTY) * 100.0 / SUM(ORDER_QTY)
        FROM PRODUCTION_ORDERS
        WHERE LINE_ID = 'LINE-A'
          AND START_DATE BETWEEN '2026-03-01' AND '2026-03-31'
    """).fetchone()
    print(f"  LINE-A March defect rate:   {row[0]:.1f}%")

    row = cur.execute("""
        SELECT SUM(DEFECT_QTY) * 100.0 / SUM(ORDER_QTY)
        FROM PRODUCTION_ORDERS
        WHERE LINE_ID = 'LINE-A'
          AND START_DATE BETWEEN '2026-02-01' AND '2026-02-28'
    """).fetchone()
    print(f"  LINE-A Feb defect rate:     {row[0]:.1f}%")

    row = cur.execute("""
        SELECT SUM(DEFECT_QTY) * 100.0 / SUM(ORDER_QTY)
        FROM PRODUCTION_ORDERS
        WHERE LINE_ID = 'LINE-B'
    """).fetchone()
    print(f"  LINE-B overall defect rate: {row[0]:.1f}%")

    row = cur.execute("""
        SELECT COUNT(*) FROM INVENTORY
        WHERE (QTY_ON_HAND - QTY_RESERVED) < 50
    """).fetchone()
    print(f"  Low-stock items (avail<50): {row[0]}")

    row = cur.execute("""
        SELECT COUNT(*) FROM EQUIPMENT WHERE STATUS = 'MAINTENANCE'
    """).fetchone()
    print(f"  Equipment in maintenance:   {row[0]}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
