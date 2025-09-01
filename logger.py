"""
Sistema de logging para Amazon SP-API Challenge
"""
import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(name: str = "spapi_challenge", log_level: str = "INFO") -> logging.Logger:
    """
    Configura logger con salida a consola y archivo
    
    Args:
        name: Nombre del logger
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    
    # Evitar duplicar handlers si ya está configurado
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Crear directorio de logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Formato de logs
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para consola (INFO y superior)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Handler para archivo (DEBUG y superior)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"spapi_challenge_{timestamp}.log"
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Handler para errores separado
    error_file = log_dir / f"spapi_errors_{timestamp}.log"
    error_handler = logging.FileHandler(error_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # Agregar handlers al logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    
    logger.info(f"Logger configurado. Archivos: {log_file.name}, {error_file.name}")
    
    return logger


def log_api_request(logger: logging.Logger, method: str, url: str, params: dict = None):
    """Log de request a API"""
    params_str = f" params={params}" if params else ""
    logger.info(f"API_REQUEST | {method} {url}{params_str}")


def log_api_response(logger: logging.Logger, status_code: int, response_size: int = None):
    """Log de response de API"""
    size_str = f" size={response_size}" if response_size else ""
    logger.info(f"API_RESPONSE | {status_code}{size_str}")


def log_validation_results(logger: logging.Logger, total: int, valid: int, errors: list, warnings: list):
    """Log de resultados de validación"""
    invalid = len(errors)
    logger.info(f"VALIDATION | Total: {total} | Válidas: {valid} | Inválidas: {invalid} | Warnings: {len(warnings)}")
    
    for error in errors:
        logger.error(f"VALIDATION_ERROR | {error}")
    
    for warning in warnings:
        logger.warning(f"VALIDATION_WARNING | {warning}")


def log_database_operation(logger: logging.Logger, operation: str, affected_rows: int = None, error: Exception = None):
    """Log de operaciones de base de datos"""
    if error:
        logger.error(f"DB_ERROR | {operation} | Error: {error}")
    else:
        rows_str = f" | Rows: {affected_rows}" if affected_rows is not None else ""
        logger.info(f"DB_SUCCESS | {operation}{rows_str}")


def log_retry_attempt(logger: logging.Logger, attempt: int, max_attempts: int, reason: str, wait_time: float = None):
    """Log de reintentos"""
    wait_str = f" | Waiting: {wait_time:.1f}s" if wait_time else ""
    logger.warning(f"RETRY | Attempt {attempt}/{max_attempts} | Reason: {reason}{wait_str}")


def log_process_summary(logger: logging.Logger, mode: str, scenario: str = None, total_processed: int = 0, execution_time: float = None):
    """Log de resumen del proceso completo"""
    mode_str = f"Mode: {mode}"
    scenario_str = f" | Scenario: {scenario}" if scenario else ""
    time_str = f" | Time: {execution_time:.2f}s" if execution_time else ""
    
    logger.info(f"PROCESS_SUMMARY | {mode_str}{scenario_str} | Processed: {total_processed}{time_str}")

_global_logger = None

def get_logger() -> logging.Logger:
    """Obtiene el logger global (crea si no existe)"""
    global _global_logger
    if _global_logger is None:
        _global_logger = setup_logger()
    return _global_logger