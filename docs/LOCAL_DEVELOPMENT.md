# ClinicStock Local Development Guide

This guide details the step-by-step setup to run and verify ClinicStock completely in a local development environment.

---

## 1. Prerequisites

- **Python**: 3.11+ (Python 3.14+ supported)
- **Node.js**: 18+ (Node 20+ LTS recommended) & `npm`
- **PostgreSQL**: 15+ or 16+ running locally on port `5432`

---

## 2. Environment Configuration

Copy `.env.example` to `backend/.env` (and optionally `frontend/.env`):

```bash
cp .env.example backend/.env
```

Ensure the following variables are defined:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/clinicstock
SECRET_KEY=dev-secret-key-replace-in-production-abcdef123456
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

---

## 3. Database Initialization & Alembic Migrations

1. Ensure PostgreSQL is running and the database `clinicstock` is created:
   ```sql
   CREATE DATABASE clinicstock;
   ```

2. Activate backend virtual environment and install dependencies:
   ```bash
   cd backend
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate

   pip install -r requirements.txt
   ```

3. Run Alembic database migrations:
   ```bash
   alembic upgrade head
   ```

---

## 4. Database Seeding (Explicit & Idempotent)

Seeding is **not** performed automatically on FastAPI startup. Seed the database explicitly using the idempotent seeding CLI:

```bash
# From backend directory with venv activated:
python -m app.seed
```

This seeds:
- Branches: `Gudivada (GDV)`, `Kaikaluru (KKL)`
- Master Data: Categories, Manufacturers, Potencies, Units, Suppliers
- Seed Users (see credentials below)
- Baseline catalog medicines and inventory batches

---

## 5. Running the Application Locally

### Starting Backend (FastAPI)
```bash
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- Interactive Swagger API Documentation: `http://127.0.0.1:8000/docs`
- Liveness Probe: `http://127.0.0.1:8000/healthz`
- Readiness Probe (DB health check): `http://127.0.0.1:8000/readyz`

### Starting Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
- Frontend application URL: `http://localhost:5173`

---

## 6. Seed Credentials for Local Testing

| Role | Email | Password | Assigned Branch | Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Doctor** | `doctor@clinicstock.com` | `Password123` | Gudivada (`GDV`) | Full admin, all branches, master data, stock adjustments, transfers, reports |
| **Assistant** | `assistant@clinicstock.com` | `Password123` | Kaikaluru (`KKL`) | Confined strictly to Kaikaluru branch, dispensing, viewing assigned stock |

---

## 7. Running Backend Tests & Frontend Build

### Backend Tests (pytest)
```bash
cd backend
python -m pytest
```

### Frontend Build & Typecheck
```bash
cd frontend
npm run build
```
