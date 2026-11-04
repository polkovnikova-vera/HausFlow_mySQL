# verwIQ Frontend

Standalone React + TypeScript + Vite application using Tailwind CSS. This
starter contains no customer, invoice, property, or financial records and does
not connect to the legacy desktop application or its databases.

## Run locally

Use Node.js 20.19+ (or 22.12+) and npm. From this directory:

```powershell
npm install
npm run dev
```

The Vite server listens on `http://127.0.0.1:5173`. Requests to `/api` are
proxied to the local FastAPI server at `http://127.0.0.1:8000`.

## Build

```powershell
npm run build
npm run preview
```

Start the backend separately; see `../backend/README.md`.
