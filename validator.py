"""
Validaciones para transacciones SP-API
"""
import json
import re
import decimal
import datetime
from datetime import timezone
from typing import Dict, Any, List, Tuple

from logger import get_logger, log_validation_results


# Regex para validar códigos de moneda ISO 4217
ISO_4217_RE = re.compile(r"^[A-Z]{3}$")


def _parse_iso_z(dt_iso: str) -> datetime.datetime:
    """Convierte ISO 8601 string a datetime UTC"""
    return datetime.datetime.fromisoformat(
        dt_iso.replace("Z", "+00:00")
    ).astimezone(timezone.utc)


def normalize_transactions(api_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normaliza payload de API a formato interno
    
    Args:
        api_payload: Respuesta de /finances/transactions
        
    Returns:
        Lista de transacciones normalizadas
    """
    rows = []
    
    for transaction in api_payload.get("transactions", []):
        # Extraer datos de amount
        currency = None
        amount_str = None
        amount_obj = transaction.get("amount")
        
        if isinstance(amount_obj, dict):
            currency = amount_obj.get("currencyCode")
            amount_str = amount_obj.get("amount")
        
        # Convertir amount a Decimal
        amount_dec = None
        if amount_str not in (None, ""):
            try:
                amount_dec = decimal.Decimal(amount_str)
                amount_dec = amount_dec.quantize(decimal.Decimal("0.01"))
            except (decimal.InvalidOperation, ValueError):
                amount_dec = None
        
        # Extraer detalles
        details = transaction.get("details") or {}
        
        rows.append({
            "transaction_id": transaction.get("transactionId"),
            "posted_date_raw": transaction.get("postedDate"),
            "type": transaction.get("type"),
            "currency_code": currency,
            "amount": amount_dec,
            "marketplace_id": transaction.get("marketplaceId"),
            "order_id": details.get("orderId"),
            "reason": details.get("reason"),
            "raw": json.dumps(transaction, ensure_ascii=False),
        })
    
    return rows


def validate_transactions(
    rows: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """
    Valida transacciones normalizadas
    
    Args:
        rows: Lista de transacciones normalizadas
        
    Returns:
        Tupla con (válidas, errores, warnings)
    """
    now = datetime.datetime.now(timezone.utc)
    seen_ids = set()
    errors = []
    warnings = []
    valid_rows = []
    
    for i, row in enumerate(rows, start=1):
        tag = f"item[{i}]"
        
        # Validar transaction_id
        tid = row.get("transaction_id")
        if not tid:
            errors.append(f"{tag}: falta 'transactionId'")
            continue
        
        if tid in seen_ids:
            errors.append(f"{tag}:{tid}: transactionId duplicado en el batch")
            continue
        seen_ids.add(tid)
        
        # Validar postedDate
        posted_date_raw = row.get("posted_date_raw")
        if not posted_date_raw:
            errors.append(f"{tag}:{tid}: falta 'postedDate'")
            continue
        
        try:
            posted_date = _parse_iso_z(posted_date_raw)
        except Exception:
            errors.append(f"{tag}:{tid}: 'postedDate' no es ISO-8601: {posted_date_raw}")
            continue
        
        # Validar que no sea fecha futura
        if posted_date > now:
            errors.append(f"{tag}:{tid}: 'postedDate' en el futuro: {posted_date_raw}")
            continue
        
        # Warning para fechas muy antiguas
        if (now - posted_date).days > 370:
            warnings.append(
                f"{tag}:{tid}: 'postedDate' muy antigua ({posted_date_raw}); "
                "revisar rango (<=180d recomendado)"
            )
        
        # Validar currency_code
        currency = row.get("currency_code")
        if currency and not ISO_4217_RE.match(currency):
            errors.append(f"{tag}:{tid}: currency_code inválido: {currency}")
            continue
        
        # Warning para refunds con monto positivo
        amount = row.get("amount")
        tx_type = (row.get("type") or "").lower()
        if (amount is not None and 
            tx_type == "refund" and 
            amount > decimal.Decimal("0.00")):
            warnings.append(
                f"{tag}:{tid}: Refund con monto positivo ({amount}). Revisar signo."
            )
        
        # Agregar campos procesados
        processed_row = dict(row)
        processed_row["posted_date"] = posted_date
        processed_row["posted_day"] = posted_date.date()
        del processed_row["posted_date_raw"]
        
        valid_rows.append(processed_row)
    
    return valid_rows, errors, warnings


def validate_and_report(api_payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Proceso completo de normalización y validación
    
    Returns:
        Tupla con (transacciones_válidas, tiene_errores)
    """
    logger = get_logger()
    logger.info("Iniciando validación de transacciones")
    
    print("=== VALIDACIÓN ===")
    
    # Normalizar
    normalized = normalize_transactions(api_payload)
    logger.debug(f"Transacciones normalizadas: {len(normalized)}")
    
    # Validar
    valid_rows, errors, warnings = validate_transactions(normalized)
    
    # Log estructurado de resultados
    log_validation_results(logger, len(normalized), len(valid_rows), errors, warnings)
    
    # Reportar resultados en consola
    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f" - {warning}")
    
    if errors:
        print("ERRORES:")
        for error in errors:
            print(f" - {error}")
    
    print(f"Filas en payload: {len(normalized)} | "
          f"Válidas: {len(valid_rows)} | "
          f"Inválidas: {len(errors)}")
    
    logger.info(f"Validación completada: {len(valid_rows)}/{len(normalized)} válidas")
    
    return valid_rows, len(errors) > 0
    if errors:
        print("ERRORES:")
        for error in errors:
            print(f" - {error}")
    
    print(f"Filas en payload: {len(normalized)} | "
          f"Válidas: {len(valid_rows)} | "
          f"Inválidas: {len(errors)}")
    
    return valid_rows, len(errors) > 0