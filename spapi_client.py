"""
Cliente para Amazon SP-API con soporte para modo mock y real
"""
import time
import json
import datetime
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

from config import (
    LWA_CLIENT_ID, LWA_CLIENT_SECRET, LWA_REFRESH_TOKEN,
    SPAPI_REGIONS, SPAPI_ENDPOINTS, DEFAULT_TIMEOUT, DEFAULT_MAX_RETRIES
)
from logger import get_logger, log_api_request, log_api_response, log_retry_attempt


class SPAPIClient:
    def __init__(self, region: str = "na", sandbox: bool = False):
        self.region = region
        self.sandbox = sandbox
        self.base_url = self._build_base_url()
        self.logger = get_logger()
        
    def _build_base_url(self) -> str:
        """Construye la URL base según región y entorno"""
        env = "sandbox" if self.sandbox else "production"
        host = SPAPI_ENDPOINTS[env]
        suffix = SPAPI_REGIONS[self.region]
        return f"https://{host}{suffix}"
    
    def _log(self, msg: str) -> None:
        """Log simple para seguimiento"""
        self.logger.info(msg)
    
    def _validate_iso8601_utc(self, dt_iso: str) -> None:
        """Valida formato de fecha ISO 8601 UTC"""
        try:
            datetime.datetime.fromisoformat(dt_iso.replace("Z", "+00:00"))
        except Exception as e:
            raise ValueError(
                f"Fecha inválida (usar ISO8601 UTC, ej: 2025-08-23T00:00:00Z). "
                f"Valor: {dt_iso}"
            ) from e
    
    def _get_lwa_token(self) -> str:
        """Obtiene access token usando LWA refresh token"""
        if not requests:
            raise ImportError("requests requerido para modo real: pip install requests")
        
        if not all([LWA_CLIENT_ID, LWA_CLIENT_SECRET, LWA_REFRESH_TOKEN]):
            raise EnvironmentError(
                "Faltan credenciales LWA. Verificar: "
                "LWA_CLIENT_ID, LWA_CLIENT_SECRET, LWA_REFRESH_TOKEN"
            )
        
        response = requests.post(
            "https://api.amazon.com/auth/o2/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": LWA_REFRESH_TOKEN,
                "client_id": LWA_CLIENT_ID,
                "client_secret": LWA_CLIENT_SECRET,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["access_token"]
    
    def list_transactions_real(
        self,
        posted_after: str,
        marketplace_id: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES
    ) -> Dict[str, Any]:
        """
        Llama a /finances/2024-06-19/transactions con manejo de errores
        """
        if not requests:
            raise ImportError("requests requerido para modo real: pip install requests")
        
        self._validate_iso8601_utc(posted_after)
        
        url = f"{self.base_url}/finances/2024-06-19/transactions"
        params = {"postedAfter": posted_after}
        if marketplace_id:
            params["marketplaceId"] = marketplace_id
        
        token = self._get_lwa_token()
        backoff = 1.0
        token_refreshed = False
        
        for attempt in range(1, max_retries + 1):
            log_api_request(self.logger, "GET", url, params)
            
            response = requests.get(
                url,
                headers={
                    "x-amz-access-token": token,
                    "accept": "application/json",
                    "user-agent": "spapi-transactions-challenge/1.0"
                },
                params=params,
                timeout=timeout,
            )
            
            log_api_response(self.logger, response.status_code, len(response.content))
            
            # Manejar 401 (token expirado) - renovar una vez
            if response.status_code == 401 and not token_refreshed:
                log_retry_attempt(self.logger, attempt, max_retries, "Token expirado")
                token = self._get_lwa_token()
                token_refreshed = True
                continue
            
            # Manejar 429 (throttling)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait_time = float(retry_after) if retry_after else backoff
                log_retry_attempt(self.logger, attempt, max_retries, "Throttling", wait_time)
                time.sleep(wait_time)
                backoff = min(backoff * 2, 60)
                continue
            
            # Manejar errores 5xx (server errors)
            if 500 <= response.status_code < 600:
                log_retry_attempt(self.logger, attempt, max_retries, f"Server error {response.status_code}", backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            
            # Otros errores HTTP
            response.raise_for_status()
            
            # Éxito
            data = response.json()
            transactions = data.get("transactions", [])
            
            if not transactions:
                return {
                    "status": "ok",
                    "transactions": [],
                    "note": "Sin datos (pueden demorar ~48h en aparecer)"
                }
            
            return data
        
        raise RuntimeError("No se pudo completar por throttling/errores transitorios")


class MockSPAPIClient:
    """Cliente mock para testing sin credenciales reales"""
    
    MOCK_RESPONSES = {
        "ok": {
            "transactions": [
                {
                    "transactionId": "tx-mock-001",
                    "postedDate": "2025-08-30T12:15:00Z",
                    "type": "Order",
                    "amount": {"currencyCode": "USD", "amount": "19.99"},
                    "marketplaceId": "ATVPDKIKX0DER",
                    "details": {"orderId": "903-1234567-1234567"}
                },
                {
                    "transactionId": "tx-mock-002", 
                    "postedDate": "2025-08-30T13:40:00Z",
                    "type": "Refund",
                    "amount": {"currencyCode": "USD", "amount": "-5.00"},
                    "marketplaceId": "ATVPDKIKX0DER",
                    "details": {"orderId": "903-1234567-1234567", "reason": "CustomerReturn"}
                }
            ],
            "nextToken": None
        },
        "empty": {"transactions": [], "nextToken": None}
    }
    
    def __init__(self):
        pass
    
    def _log(self, msg: str) -> None:
        print(f"[MOCK] {msg}", flush=True)
    
    def list_transactions_mock(
        self,
        posted_after: str,
        scenario: str = "ok",
        max_retries: int = DEFAULT_MAX_RETRIES
    ) -> Dict[str, Any]:
        """
        Simula diferentes escenarios de la API
        
        Args:
            scenario: "ok", "empty", "401", "429"
        """
        # Validar fecha
        try:
            datetime.datetime.fromisoformat(posted_after.replace("Z", "+00:00"))
        except Exception as e:
            raise ValueError(f"Fecha inválida: {posted_after}") from e
        
        backoff = 1.0
        attempts = 0
        remaining_401 = 1 if scenario == "401" else 0
        remaining_429 = 2 if scenario == "429" else 0
        
        while attempts < max_retries:
            attempts += 1
            
            # Simular 401 (token expirado)
            if remaining_401 > 0:
                remaining_401 -= 1
                self._log(f"Intento {attempts}: 401 (token expirado). Renovando...")
                time.sleep(0.1)
                continue
            
            # Simular 429 (throttling)
            if remaining_429 > 0:
                remaining_429 -= 1
                self._log(f"Intento {attempts}: 429 (throttling). Esperando {backoff:.1f}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            
            # Respuesta exitosa
            if scenario in ["ok", "401", "429"]:
                response = self.MOCK_RESPONSES["ok"]
                self._log(f"Intento {attempts}: OK con {len(response['transactions'])} transacciones")
                return response
            elif scenario == "empty":
                response = self.MOCK_RESPONSES["empty"]
                self._log(f"Intento {attempts}: OK vacío (sin transacciones)")
                return response
            else:
                raise ValueError(f"Escenario desconocido: {scenario}")
        
        raise RuntimeError("Se agotaron los reintentos en modo mock")