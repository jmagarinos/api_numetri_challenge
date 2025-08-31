"""
Manejo de base de datos PostgreSQL para transacciones SP-API
"""
import json
import psycopg2
import psycopg2.extras
from typing import List, Dict, Any
from config import POSTGRES_CONFIG


def get_connection():
    """Crea conexión a PostgreSQL"""
    return psycopg2.connect(
        host=POSTGRES_CONFIG["host"],
        port=POSTGRES_CONFIG["port"],
        dbname=POSTGRES_CONFIG["database"],
        user=POSTGRES_CONFIG["user"],
        password=POSTGRES_CONFIG["password"],
        connect_timeout=5,
    )


def ensure_table_and_indexes():
    """Crea tabla e índices si no existen"""
    ddl = """
    CREATE TABLE IF NOT EXISTS spapi_transactions (
        transaction_id  text PRIMARY KEY,
        posted_date     timestamptz,
        posted_day      date,
        type            text,
        currency_code   text,
        amount          numeric(14,2),
        marketplace_id  text,
        order_id        text,
        reason          text,
        raw             jsonb,
        created_at      timestamptz DEFAULT now(),
        updated_at      timestamptz DEFAULT now()
    );
    """
    
    # Agregar columna posted_day si no existe (migración)
    alter_posted_day = """
    ALTER TABLE spapi_transactions 
    ADD COLUMN IF NOT EXISTS posted_day date;
    """
    
    # Índices para optimizar consultas
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_spapi_tx_posted_date ON spapi_transactions (posted_date);",
        "CREATE INDEX IF NOT EXISTS idx_spapi_tx_posted_day ON spapi_transactions (posted_day);", 
        "CREATE INDEX IF NOT EXISTS idx_spapi_tx_type_currency ON spapi_transactions (type, currency_code);",
    ]
    
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(ddl)
        cur.execute(alter_posted_day)
        for idx_sql in indexes:
            cur.execute(idx_sql)
        conn.commit()


def save_transactions(transactions: List[Dict[str, Any]]) -> int:
    """
    Guarda transacciones en PostgreSQL usando UPSERT
    
    Args:
        transactions: Lista de transacciones normalizadas y validadas
        
    Returns:
        Número de filas procesadas
    """
    if not transactions:
        return 0
    
    ensure_table_and_indexes()
    
    columns = [
        "transaction_id", "posted_date", "posted_day", "type", 
        "currency_code", "amount", "marketplace_id", "order_id", 
        "reason", "raw"
    ]
    
    values = []
    for tx in transactions:
        if not tx.get("transaction_id"):
            continue  # Saltar filas sin ID
            
        values.append((
            tx["transaction_id"],
            tx["posted_date"], 
            tx["posted_day"],
            tx.get("type"),
            tx.get("currency_code"),
            tx.get("amount"),
            tx.get("marketplace_id"),
            tx.get("order_id"),
            tx.get("reason"),
            psycopg2.extras.Json(json.loads(tx["raw"]))
        ))
    
    upsert_sql = f"""
    INSERT INTO spapi_transactions ({", ".join(columns)})
    VALUES %s
    ON CONFLICT (transaction_id) DO UPDATE SET
        posted_date    = EXCLUDED.posted_date,
        posted_day     = EXCLUDED.posted_day,
        type           = EXCLUDED.type,
        currency_code  = EXCLUDED.currency_code,
        amount         = EXCLUDED.amount,
        marketplace_id = EXCLUDED.marketplace_id,
        order_id       = EXCLUDED.order_id,
        reason         = EXCLUDED.reason,
        raw            = EXCLUDED.raw,
        updated_at     = now();
    """
    
    with get_connection() as conn, conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur, upsert_sql, values, page_size=1000
        )
        conn.commit()
    
    return len(values)


def get_saved_transactions(transaction_ids: List[str]) -> List[Dict[str, Any]]:
    """Obtiene transacciones guardadas por sus IDs"""
    if not transaction_ids:
        return []
    
    with get_connection() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT transaction_id, type, amount, currency_code, 
                   posted_date, posted_day, order_id, reason
            FROM spapi_transactions
            WHERE transaction_id IN %s
            ORDER BY posted_date;
        """, (tuple(transaction_ids),))
        
        return [dict(row) for row in cur.fetchall()]