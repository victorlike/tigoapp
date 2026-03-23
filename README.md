# TigoApp — FastAPI + Supabase + Railway

Sistema de gestión de leads de Tigo construido con Python (FastAPI), base de datos PostgreSQL (Supabase) y deploy en Railway.

## Estructura del proyecto

```
TigoApp/
├── main.py           # FastAPI entry point
├── database.py       # PostgreSQL connection pool
├── models.py         # Pydantic models
├── auth.py           # API key auth for Apps Script
├── auto_assign.py    # Lead auto-assignment engine
├── schema.sql        # Run once in Supabase SQL Editor
├── GmailBridge.gs    # Apps Script (copy to your GAS project)
├── requirements.txt
├── Procfile
├── railway.toml
├── .env.example      # Copy to .env and fill values
├── routes/
│   ├── leads.py
│   ├── agents.py
│   ├── followups.py
│   ├── sales.py
│   └── coordinator.py
└── templates/
    ├── login.html
    ├── leaddesk.html
    └── coordinator.html
```

## Setup en 5 pasos

### 1. Supabase
1. Ve a [supabase.com](https://supabase.com) → New Project
2. Copia el **Connection String** (Settings > Database > Connection string > URI)
3. Abre el **SQL Editor** y ejecuta el contenido de `schema.sql`

### 2. Variables de entorno
```bash
cp .env.example .env
# Edita .env con tu DATABASE_URL y genera un SECRET_KEY y APPS_SCRIPT_KEY únicos
```

### 3. Running local (desarrollo)
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Abre http://localhost:8000
```

### 4. Deploy en Railway
1. Sube el proyecto a GitHub
2. Ve a [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Agrega las variables de entorno en Railway (Settings > Variables):
   - `DATABASE_URL` → tu Supabase connection string
   - `SECRET_KEY` → string aleatorio largo
   - `APPS_SCRIPT_KEY` → string que también pondrás en el Apps Script
4. Railway detecta el `Procfile` automáticamente y hace el deploy

### 5. Apps Script (Gmail Bridge)
1. Ve a tu proyecto de Apps Script en Google
2. Crea un nuevo archivo y pega el contenido de `GmailBridge.gs`
3. Actualiza `RAILWAY_URL` con tu URL de Railway (ej: `https://tigoapp.up.railway.app`)
4. Actualiza `API_KEY` con el mismo valor que `APPS_SCRIPT_KEY` en Railway
5. Crea el label `TIGO-LEADS` en Gmail y ponle ese label a los correos de leads
6. Ejecuta `installTrigger()` una vez

## BI (Looker Studio / Power BI)

Conecta directamente al PostgreSQL de Supabase:
- **Host:** `db.<project-id>.supabase.co`
- **Puerto:** `5432`
- **BD:** `postgres`
- **Usuario:** `postgres`
- **Password:** el que configuraste en Supabase

Usa la vista `vw_daily_queue` para reportes de rendimiento diario.
