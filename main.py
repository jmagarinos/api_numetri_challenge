#!/usr/bin/env python3
"""
Amazon SP-API Transactions Challenge - Script principal
Ejecuta el flujo completo: obtener datos → validar → guardar → analizar
"""
import sys
import argparse
import datetime
import time
from typing import Optional

from logger import setup_logger, log_validation_results, log_database_operation, log_process_summary
from spapi_client import SPAPIClient, MockSPAPIClient
from validator import validate_and_report
from database import save_transactions, get_saved_transactions
from analytics import print_analytics_report, get_transaction_count


def _default_posted_after(days: int = 1) -> str:
    """Genera fecha por defecto (últimas 24h)"""
    dt = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    return dt.replace(microsecond=0).isoformat() + "Z"


def main():
    start_time = time.time()
    
    parser = argparse.ArgumentParser(
        description="Amazon SP-API Transactions Challenge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Modo mock (testing sin credenciales)
  python main.py --mock --scenario ok
  python main.py --mock --scenario empty
  python main.py --mock --scenario 401
  python main.py --mock --scenario 429

  # Modo real (requiere credenciales en .env)
  python main.py --real
  python main.py --real --marketplace-id ATVPDKIKX0DER --region na
  python main.py --real --sandbox

  # Solo mostrar analytics de datos existentes
  python main.py --analytics-only
  
  # Logs se guardan en: logs/spapi_challenge_YYYYMMDD_HHMMSS.log
        """
    )
    
    # Modo de operación
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--mock", action="store_true",
        help="Ejecuta en modo simulación (sin credenciales)"
    )
    mode_group.add_argument(
        "--real", action="store_true", 
        help="Ejecuta contra SP-API real (requiere credenciales)"
    )
    mode_group.add_argument(
        "--analytics-only", action="store_true",
        help="Solo muestra analytics de datos existentes en DB"
    )
    
    # Parámetros de logging
    parser.add_argument(
        "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
        default="INFO", help="Nivel de logging (default: INFO)"
    )
    
    # Parámetros para mock
    parser.add_argument(
        "--scenario", choices=["ok", "empty", "401", "429"], default="ok",
        help="Escenario para modo mock (default: ok)"
    )
    
    # Parámetros para API
    parser.add_argument(
        "--posted-after", 
        help="Fecha ISO 8601 UTC (ej: 2025-08-23T00:00:00Z). Default: últimas 24h"
    )
    parser.add_argument(
        "--marketplace-id",
        help="ID del marketplace (ej: ATVPDKIKX0DER para US)"
    )
    parser.add_argument(
        "--region", choices=["na", "eu", "fe"], default="na",
        help="Región SP-API (default: na)"
    )
    parser.add_argument(
        "--sandbox", action="store_true",
        help="Usar endpoint sandbox"
    )
    
    args = parser.parse_args()
    
    # Configurar logger
    logger = setup_logger(log_level=args.log_level)
    logger.info("=== INICIANDO SP-API CHALLENGE ===")
    
    # Si no especifica modo, usar mock por defecto
    if not any([args.mock, args.real, args.analytics_only]):
        logger.info("No se especificó modo. Usando --mock por defecto.")
        print("ℹ️  No se especificó modo. Usando --mock por defecto.")
        args.mock = True
    
    # Modo analytics-only
    if args.analytics_only:
        logger.info("Modo analytics-only solicitado")
        count = get_transaction_count()
        if count == 0:
            logger.warning("No hay transacciones en la base de datos")
            print("❌ No hay transacciones en la base de datos.")
            print("💡 Ejecuta primero con --mock o --real para obtener datos.")
            return
        
        logger.info(f"Analizando {count} transacciones existentes")
        print(f"📊 Analizando {count} transacciones existentes...")
        print_analytics_report()
        return
    
    # Obtener datos
    posted_after = args.posted_after or _default_posted_after(1)
    
    logger.info(f"Configuración: modo={'MOCK' if args.mock else 'REAL'}, fecha_desde={posted_after}")
    print("🚀 Iniciando Amazon SP-API Transactions Challenge")
    print(f"📅 Fecha desde: {posted_after}")
    
    try:
        if args.mock:
            logger.info(f"Ejecutando modo MOCK con escenario: {args.scenario}")
            print(f"🧪 Modo: MOCK (escenario: {args.scenario})")
            client = MockSPAPIClient()
            api_data = client.list_transactions_mock(posted_after, args.scenario)
        else:
            logger.info(f"Ejecutando modo REAL - región: {args.region}, sandbox: {args.sandbox}")
            print(f"🌐 Modo: REAL (región: {args.region}, sandbox: {args.sandbox})")
            client = SPAPIClient(region=args.region, sandbox=args.sandbox)
            api_data = client.list_transactions_real(
                posted_after=posted_after,
                marketplace_id=args.marketplace_id
            )
        
        # Validar datos
        valid_transactions, has_errors = validate_and_report(api_data)
        
        # Log de validación
        normalized_count = len(api_data.get("transactions", []))
        errors_list = []  # validate_and_report ya maneja el logging internamente
        warnings_list = []
        
        if has_errors:
            logger.warning("Hay errores en los datos. Solo se procesarán las transacciones válidas.")
            print("⚠️  Hay errores en los datos. Solo se procesarán las transacciones válidas.")
        
        # Guardar en DB
        if valid_transactions:
            logger.info(f"Guardando {len(valid_transactions)} transacciones válidas en PostgreSQL")
            print("\n💾 Guardando en PostgreSQL...")
            
            try:
                saved_count = save_transactions(valid_transactions)
                log_database_operation(logger, "UPSERT transactions", saved_count)
                print(f"✅ {saved_count} transacciones guardadas/actualizadas")
                
                # Verificar datos guardados
                transaction_ids = [tx["transaction_id"] for tx in valid_transactions]
                saved_data = get_saved_transactions(transaction_ids)
                
                logger.info(f"Verificación DB: {len(saved_data)} transacciones recuperadas")
                print(f"\n🔍 Verificación DB: {len(saved_data)} transacciones recuperadas")
                
                for tx in saved_data[:3]:  # Mostrar primeras 3
                    print(f"  - {tx['transaction_id']}: {tx['type']} {tx['amount']} {tx['currency_code']}")
                if len(saved_data) > 3:
                    print(f"  ... y {len(saved_data) - 3} más")
                    
            except Exception as e:
                log_database_operation(logger, "UPSERT transactions", error=e)
                print(f"❌ Error guardando en DB: {e}")
                raise
        else:
            logger.warning("No hay transacciones válidas para guardar")
            print("❌ No hay transacciones válidas para guardar")
        
        # Generar analytics
        logger.info("Generando reporte de analytics")
        print_analytics_report()
        
        # Log final
        execution_time = time.time() - start_time
        mode = "MOCK" if args.mock else "REAL"
        scenario = args.scenario if args.mock else None
        log_process_summary(logger, mode, scenario, len(valid_transactions), execution_time)
        
        print("\n🎉 Challenge completado!")
        logger.info("Challenge completado exitosamente")
        
    except Exception as e:
        logger.error(f"Error en ejecución principal: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Cancelado por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)