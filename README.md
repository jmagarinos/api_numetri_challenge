# Amazon SP-API Transactions Challenge

Sistema completo para obtener, validar y analizar transacciones de Amazon SP-API con persistencia en PostgreSQL.

## 🚀 Instalación Rápida

```bash
# 1. Clonar/crear el proyecto
mkdir spapi-challenge && cd spapi-challenge

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar credenciales
cp .env.example .env
# Editar .env con tus credenciales reales

# 4. Ejecutar en modo mock (sin credenciales)
python main.py --mock
```

## 📁 Estructura del Proyecto

```
spapi-challenge/
├── main.py              # Script principal
├── config.py            # Configuración y variables de entorno
├── spapi_client.py      # Cliente SP-API (mock + real)
├── validator.py         # Validaciones de datos
├── database.py          # Manejo de PostgreSQL
├── analytics.py         # Reportes y análisis
├── requirements.txt     # Dependencias Python
├── .env.example         # Ejemplo de variables de entorno
└── README.md           # Este archivo
```

## ⚙️ Configuración

### 1. Variables de Entorno (.env)

```bash
# Amazon LWA Credentials (solo para modo --real)
LWA_CLIENT_ID=tu_client_id
LWA_CLIENT_SECRET=tu_client_secret  
LWA_REFRESH_TOKEN=tu_refresh_token

# PostgreSQL Database
PGHOST=127.0.0.1
PGPORT=5432
PGDATABASE=app_db
PGUSER=app_user
PGPASSWORD=app_pass
```

### 2. PostgreSQL

Asegúrate de tener PostgreSQL corriendo y la base de datos creada:

```sql
CREATE DATABASE app_db;
CREATE USER app_user WITH PASSWORD 'app_pass';
GRANT ALL PRIVILEGES ON DATABASE app_db TO app_user;
```

## 🎯 Uso

### Modo Mock (Testing sin credenciales)

```bash
# Escenario exitoso con datos
python main.py --mock --scenario ok

# Escenario sin datos  
python main.py --mock --scenario empty

# Simular token expirado (401)
python main.py --mock --scenario 401

# Simular throttling (429)
python main.py --mock --scenario 429
```

### Modo Real (SP-API)

```bash
# Básico (últimas 24h)
python main.py --real

# Con parámetros específicos
python main.py --real \
  --marketplace-id ATVPDKIKX0DER \
  --region na \
  --posted-after 2025-08-25T00:00:00Z

# Modo sandbox
python main.py --real --sandbox
```

### Solo Analytics

```bash
# Analizar datos existentes en DB
python main.py --analytics-only
```

## 📊 Funcionalidades

### ✅ Validaciones Implementadas

- **Campos obligatorios**: `transactionId`, `postedDate`
- **Formato de fechas**: ISO 8601 UTC válido
- **Fechas futuras**: No permitidas
- **Duplicados**: Detecta IDs duplicados en el batch
- **Códigos de moneda**: Validación ISO 4217 (3 letras)
- **Refunds**: Warning si tienen monto positivo
- **Fechas antiguas**: Warning si >370 días

### 🔄 Manejo de Errores SP-API

- **401 (Token expirado)**: Renovación automática una vez
- **429 (Throttling)**: Backoff exponencial + Retry-After
- **5xx (Server errors)**: Reintentos con backoff
- **Timeouts**: Configurables por request

### 📈 Analytics Incluidos

- **KPIs**: Total transacciones, órdenes únicas, bruto/neto, refund rate, AOV
- **Por tipo**: Desglose Order/Refund por moneda
- **Diario**: Evolución día a día
- **Por SKU**: Si está disponible en los detalles

## 🧪 Testing

El modo mock incluye datos de prueba que cubren diferentes casos:

```python
# En Python/Jupyter
from main import main

# Mock con datos
main(["--mock", "--scenario", "ok"])

# Mock sin datos
main(["--mock", "--scenario", "empty"])
```

## ⚡ Optimizaciones

### Base de Datos

- **Índices**: `posted_date`, `posted_day`, `(type, currency_code)`
- **UPSERT**: Evita duplicados, actualiza datos existentes
- **Tipos optimizados**: `numeric(14,2)` para amounts, `jsonb` para raw data

### Rendimiento

- **Batch inserts**: Usa `execute_values` para inserción eficiente
- **Connection pooling**: Reutiliza conexiones PostgreSQL
- **Lazy loading**: Solo importa `requests` cuando es necesario

## 🐛 Troubleshooting

### Error de conexión a PostgreSQL

```bash
# Verificar que PostgreSQL esté corriendo
sudo systemctl status postgresql

# Verificar conexión
psql -h 127.0.0.1 -U app_user -d app_db
```

### Error de credenciales SP-API

```bash
# Verificar variables de entorno
echo $LWA_CLIENT_ID

# Probar con modo mock primero
python main.py --mock
```

### Dependencias faltantes

```bash
# Reinstalar dependencias
pip install -r requirements.txt --upgrade
```

## 📚 Recursos

- [SP-API Finances Documentation](https://developer-docs.amazon.com/sp-api/docs/finances-api-v0-reference)
- [Login with Amazon (LWA)](https://developer.amazon.com/docs/login-with-amazon/documentation-overview.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---
**Autor**: Juan  
**Versión**: 1.0
