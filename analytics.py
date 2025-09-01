"""
Análisis y reportes de transacciones SP-API
"""
import pandas as pd
from sqlalchemy import create_engine
from config import DATABASE_URL


def get_engine():
    """Crea engine SQLAlchemy para pandas"""
    return create_engine(DATABASE_URL)


def generate_kpi_report() -> pd.DataFrame:
    """Genera reporte de KPIs principales"""
    query = """
    WITH base AS (
        SELECT 
            type, 
            amount::numeric AS amount, 
            currency_code,
            (raw->'details'->>'orderId') AS order_id
        FROM spapi_transactions
    )
    SELECT
        COUNT(*) AS total_transacciones,
        COUNT(DISTINCT order_id) AS ordenes_unicas,
        SUM(CASE WHEN type='Order' THEN amount ELSE 0 END) AS bruto_orders,
        SUM(CASE WHEN type='Refund' THEN amount ELSE 0 END) AS total_refunds,
        SUM(amount) AS neto_total,
        (COUNT(*) FILTER (WHERE type='Refund')::decimal / 
         NULLIF(COUNT(*)::decimal, 0)) AS refund_rate,
        (SUM(amount) / NULLIF(COUNT(DISTINCT order_id), 0)) AS aov_aprox
    FROM base;
    """
    
    engine = get_engine()
    return pd.read_sql(query, engine)


def generate_type_summary() -> pd.DataFrame:
    """Genera resumen por tipo de transacción y moneda"""
    query = """
    SELECT 
        type, 
        currency_code, 
        COUNT(*) AS cantidad, 
        SUM(amount) AS total_monto
    FROM spapi_transactions
    GROUP BY type, currency_code
    ORDER BY type, currency_code;
    """
    
    engine = get_engine()
    return pd.read_sql(query, engine)


def generate_daily_summary() -> pd.DataFrame:
    """Genera resumen diario de transacciones"""
    query = """
    WITH base AS (
        SELECT 
            posted_date::date AS fecha,
            amount::numeric AS amount 
        FROM spapi_transactions
    )
    SELECT 
        fecha,
        COUNT(*) AS num_transacciones,
        SUM(amount) AS neto_dia
    FROM base
    GROUP BY fecha
    ORDER BY fecha;
    """
    
    engine = get_engine()
    return pd.read_sql(query, engine)


def generate_sku_summary() -> pd.DataFrame:
    """Genera resumen por SKU (si está disponible en details)"""
    query = """
    WITH sku_data AS (
        SELECT 
            (raw->'details'->>'sku') AS sku,
            type,
            amount::numeric AS amount,
            currency_code
        FROM spapi_transactions
        WHERE raw->'details'->>'sku' IS NOT NULL
    )
    SELECT 
        sku,
        COUNT(*) AS total_transacciones,
        SUM(CASE WHEN type='Order' THEN amount ELSE 0 END) AS ventas_brutas,
        SUM(CASE WHEN type='Refund' THEN amount ELSE 0 END) AS refunds,
        SUM(amount) AS neto_sku
    FROM sku_data
    GROUP BY sku
    ORDER BY neto_sku DESC;
    """
    
    engine = get_engine()
    return pd.read_sql(query, engine)


def get_transaction_count() -> int:
    """Obtiene el número total de transacciones en la DB"""
    query = "SELECT COUNT(*) as count FROM spapi_transactions;"
    
    try:
        engine = get_engine()
        df = pd.read_sql(query, engine)
        return df.iloc[0]['count'] if not df.empty else 0
    except Exception:
        return 0


def print_analytics_report():
    """Imprime reporte completo de analytics"""
    try:
        print("\n=== REPORTE DE ANÁLISIS ===")
        
        # KPIs principales
        kpis = generate_kpi_report()
        if not kpis.empty:
            print("\n📊 KPIs Principales:")
            print(kpis.to_string(index=False))
        
        # Por tipo
        by_type = generate_type_summary()
        if not by_type.empty:
            print("\n📈 Por Tipo de Transacción:")
            print(by_type.to_string(index=False))
        
        # Resumen diario
        daily = generate_daily_summary()
        if not daily.empty:
            print(f"\n📅 Resumen Diario (últimas {min(10, len(daily))} fechas):")
            print(daily.tail(10).to_string(index=False))
        
        # Por SKU (si hay datos)
        sku_summary = generate_sku_summary()
        if not sku_summary.empty:
            print(f"\n🏷️ Top SKUs (primeros {min(10, len(sku_summary))}):")
            print(sku_summary.head(10).to_string(index=False))
        else:
            print("\n🏷️ SKUs: No hay datos de SKU en las transacciones")
            
    except Exception as e:
        print(f"❌ Error generando reporte: {e}")