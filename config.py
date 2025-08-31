"""
Configuración del proyecto Amazon SP-API Challenge
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Amazon LWA Configuration
LWA_CLIENT_ID = os.getenv("LWA_CLIENT_ID")
LWA_CLIENT_SECRET = os.getenv("LWA_CLIENT_SECRET")
LWA_REFRESH_TOKEN = os.getenv("LWA_REFRESH_TOKEN")

# PostgreSQL Configuration
POSTGRES_CONFIG = {
    "host": os.getenv("PGHOST", "127.0.0.1"),
    "port": int(os.getenv("PGPORT", "5432")),
    "database": os.getenv("PGDATABASE", "app_db"),
    "user": os.getenv("PGUSER", "app_user"),
    "password": os.getenv("PGPASSWORD", "app_pass"),
}

# SQLAlchemy Database URL para pandas
DATABASE_URL = f"postgresql://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"

# SP-API Configuration
SPAPI_REGIONS = {
    "na": "-na.amazon.com",
    "eu": "-eu.amazon.com", 
    "fe": "-fe.amazon.com",
}

SPAPI_ENDPOINTS = {
    "production": "sellingpartnerapi",
    "sandbox": "sandbox.sellingpartnerapi",
}

# Configuración por defecto
DEFAULT_REGION = "na"
DEFAULT_MARKETPLACE_ID = "ATVPDKIKX0DER"  # US marketplace
DEFAULT_TIMEOUT = 60
DEFAULT_MAX_RETRIES = 6