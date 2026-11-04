# verwIQ Backend

Standalone FastAPI starter. It does not connect to the existing SQLite/MySQL
databases and does not call OCR, Ollama, or invoice services.

## Run locally

From this directory, create/activate a Python virtual environment, install the
listed requirements, then run:

```powershell
uvicorn app.main:app --reload
```

Health check: `GET http://127.0.0.1:8000/api/v1/health`.

The default CORS origin is `http://localhost:5173`. To explicitly allow another
local Vite origin, set `VERWIQ_CORS_ORIGINS` to a comma-separated list containing
only `http://localhost[:port]` or `http://127.0.0.1[:port]` origins. Wildcards,
HTTPS origins, and non-local hosts are rejected.

## Test

```powershell
python -m pytest
```
