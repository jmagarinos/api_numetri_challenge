# Amazon SP-API Transactions Challenge

Sistema completo para obtener, validar y analizar transacciones de Amazon SP-API con persistencia en PostgreSQL y logging estructurado.

## 🚀 Instalación Rápida

```bash
# 1. Clonar/crear el proyecto
mkdir spapi-challenge && cd spapi-challenge

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar credenciales
cp .env.example .env
# Editar .env con tus credenciales reales

# 4. Configurar PostgreSQL manualmente (ver sección Database Setup)

# 5. Ejecutar en modo mock (sin credenciales)
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
├── logger.py            # Sistema de logging
├── requirements.txt     # Dependencias Python
├── .env.example         # Ejemplo de variables de entorno
├── logs/                # Directorio de logs (se crea automáticamente)
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

### 2. Instalación de PostgreSQL

#### **macOS (Homebrew)**

```bash
# Instalar PostgreSQL
brew install postgresql

# Iniciar servicio
brew services start postgresql

# Verificar que esté corriendo
brew services list | grep postgres
```

#### **macOS (PostgreSQL.app)**

```bash
# Descargar desde: https://postgresapp.com/
# Instalar y ejecutar la app
# PostgreSQL estará disponible en puerto 5432
```

#### **Ubuntu/Debian**

```bash
# Instalar PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Iniciar servicio
sudo systemctl start postgresql
sudo systemctl enable postgresql  # Auto-inicio

# Verificar estado
sudo systemctl status postgresql
```

#### **CentOS/RHEL/Fedora**

```bash
# Instalar PostgreSQL
sudo dnf install postgresql postgresql-server  # Fedora
# o
sudo yum install postgresql postgresql-server  # CentOS/RHEL

# Inicializar base de datos
sudo postgresql-setup initdb

# Iniciar servicio
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### **Windows**

```bash
# Descargar desde: https://www.postgresql.org/download/windows/
# Ejecutar instalador y seguir wizard
# Por defecto queda en puerto 5432
```

### 3. Configuración Inicial de PostgreSQL

#### **Método 1: macOS con Homebrew (más común)**

```bash
# PostgreSQL con Homebrew usa tu usuario actual como superusuario
psql -d postgres

# Dentro de psql, ejecutar:
CREATE DATABASE app_db;
CREATE USER app_user WITH PASSWORD 'app_pass';
GRANT ALL PRIVILEGES ON DATABASE app_db TO app_user;
\c app_db
GRANT ALL ON SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;
\q
```

#### **Método 2: Linux/Windows (usuario postgres)**

```bash
# Conectar como usuario postgres
sudo -u postgres psql

# Dentro de psql, ejecutar los mismos comandos de arriba
CREATE DATABASE app_db;
CREATE USER app_user WITH PASSWORD 'app_pass';
# ... resto igual
\q
```

#### **Verificar configuración:**

```bash
# Probar conexión con el usuario creado
psql -h 127.0.0.1 -U app_user -d app_db -c "SELECT version();"

# Si funciona, verás la versión de PostgreSQL
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

# Con logging detallado
python main.py --mock --scenario ok --log-level DEBUG
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

## 📋 Funcionalidades

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

### 📊 Logging Estructurado

- **Archivos**: `logs/spapi_challenge_YYYYMMDD_HHMMSS.log`
- **Errores**: `logs/spapi_errors_YYYYMMDD_HHMMSS.log`
- **Niveles**: DEBUG, INFO, WARNING, ERROR
- **Consola + Archivo**: Salida dual automática
- **Structured**: API requests, validaciones, DB operations, reintentos

### 📈 Analytics Incluidos

- **KPIs**: Total transacciones, órdenes únicas, bruto/neto, refund rate, AOV
- **Por tipo**: Desglose Order/Refund por moneda
- **Diario**: Evolución día a día
- **Por SKU**: Si está disponible en los detalles

## 🧪 Testing Completo

### **Secuencia recomendada:**

```bash
# 1. Verificar PostgreSQL
brew services list | grep postgres  # macOS
sudo systemctl status postgresql     # Linux

# 2. Test básico exitoso  
python main.py --mock --scenario ok

# 3. Test manejo de errores
python main.py --mock --scenario 401
python main.py --mock --scenario 429

# 4. Test datos vacíos
python main.py --mock --scenario empty

# 5. Test analytics
python main.py --analytics-only

# 6. Test con logging detallado
python main.py --mock --scenario ok --log-level DEBUG

# 7. Si tienes credenciales, test real
python main.py --real --sandbox
```

### **Casos de prueba incluidos:**

- ✅ **Datos válidos**: Transacciones normales Order/Refund
- ❌ **IDs duplicados**: Detecta duplicados en el mismo batch
- ❌ **Fechas inválidas**: Formato incorrecto, fechas futuras
- ⚠️ **Fechas antiguas**: Warning para datos >370 días
- ❌ **Monedas inválidas**: Códigos no ISO 4217
- ⚠️ **Refunds positivos**: Warning por signo incorrecto
- ✅ **Campos opcionales**: Maneja SKUs, reasons, etc.

### **Logs generados:**

```
logs/
├── spapi_challenge_20250831_171530.log    # Log completo
├── spapi_errors_20250831_171530.log       # Solo errores
└── ...
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
brew services start postgresql       # macOS
sudo systemctl start postgresql      # Linux

# Verificar conexión manual
psql -h 127.0.0.1 -U app_user -d app_db -c "SELECT 1;"

# Si falla, recrear base de datos (ver sección Configuración)
```

### Error de credenciales SP-API

```bash
# Verificar variables de entorno
echo $LWA_CLIENT_ID

# Probar con modo mock primero
python main.py --mock
```

### Error de logging o archivos de log

```bash
# Verificar permisos de escritura
ls -la logs/

# Cambiar nivel de logging
python main.py --mock --log-level WARNING
```

## 📚 Recursos

- [SP-API Finances Documentation](https://developer-docs.amazon.com/sp-api/docs/finances-api-v0-reference)
- [Login with Amazon (LWA)](https://developer.amazon.com/docs/login-with-amazon/documentation-overview.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---
**Autor**: Juan Ignacio Magarinos Castro
**Versión**: 1.2
