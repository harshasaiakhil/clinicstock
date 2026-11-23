# ClinicStock

Homeopathy Clinic Inventory & ERP System

ClinicStock is a modern, unified Homeopathy Clinic Inventory & ERP System designed specifically for clinics to manage homeopathic dilutions, mother tinctures, tablets, and specialty stock batches across multiple branches. It streamlines catalog maintenance, real-time stock operations (receipt, dispensing, adjustments, and branch transfers), storage location tracing, expiration alerts, and dashboard analytics.

---

> [!IMPORTANT]
> **TCS Evaluation Note**: ClinicStock is pre-configured for direct demo access without any login or credential requirements. Opening the application will direct you straight into the fully authenticated Doctor/Admin workspace, ensuring an uninterrupted testing experience.

---

## Key Features

1. **Unified Medicines Module**: Displays medicine details and inventory stock details together. Each record includes name, category, potency, unit, quantity, batch number, expiry date, selling price, GST, HSN, barcode, QR code, status, and description.
2. **Dynamic Storage Tracking**: Fully supports tracking medicine location coordinates by Cupboard, Rack, Row, and Column (e.g. `C-04 → R-02 → Row 05 → Col 03`), persisting coordinates across operations.
3. **Multi-Branch Support**: Track separate inventory quantities and values for Gudivada and Kaikaluru branches.
4. **Real-time Inventory Operations**: Process Stock In, Dispense, Stock Transfer, and Stock Adjustments immediately updating parent inventories.
5. **Dashboard Analytics**: Dynamic breakdown of total inventory, values, expiring stocks, top dispensed medicines, low-stock warnings, and transaction logs.
6. **Master Configuration**: Manage categories, manufacturers, suppliers, medicine units, and potencies dynamically.
7. **Reports & Logs**: Exports CVS/Excel files and provides detailed transaction valuation reports.

---

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy (asyncio), Uvicorn, Alembic.
- **Frontend**: Vite, React, TypeScript, TailwindCSS, Axios, Lucide React, React Query.
- **Database**: SQLite (default / local dev) via aiosqlite, with PostgreSQL support available.

---

## Architecture & Data Flow

ClinicStock runs as a consolidated project where the FastAPI backend builds and serves the React/TypeScript frontend static assets:

```
ClinicStock/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── api/              # API Route Handlers & Dependencies
│   │   ├── crud/             # SQL Alchemy CRUD Operations
│   │   ├── models/           # DB Schema Models
│   │   └── services/         # Business Logic Layer
│   └── tests/                # Pytest Suite
├── frontend/                 # Vite + React + TS Application
│   ├── src/
│   │   ├── components/       # Layouts & Reusable Elements
│   │   ├── context/          # Authentication & User Context
│   │   └── pages/            # Modules (Dashboard, Medicines, etc.)
└── package.json              # Consolidated Project Commands
```

### Location Data Flow Example
```
Frontend Form (React State)
  ──> API Request Payload
    ──> Pydantic Schema Validation (Pydantic / Pydantic Settings)
      ──> Service Layer logic
        ──> SQLAlchemy Async DB Session
          ──> SQLite Database (`clinicstock.db`)
            ──> API JSON Response
              ──> React Query (Cache Invalidation)
                ──> UI Renders Updated Value
```

---

## Database Structure

- **users**: Clinic doctors and assistants.
- **branches**: Branches (`Gudivada`, `Kaikaluru`).
- **categories**: Classifications (`Mother Tincture`, `Dilution`, etc.).
- **manufacturers**: Optional medicine makers.
- **potencies**: Homeopathy strength metrics (`Q`, `30C`, `200C`, etc.).
- **medicine_units**: Packaging units (`Bottle`, `Tube`, etc.).
- **medicines**: Core catalog specifications.
- **inventory_summaries**: Aggregated stock per medicine and branch.
- **inventory_batches**: Batches with specific suppliers, prices, locations, and expiration.
- **stock_transactions**: Historical record of every stock in, dispense, transfer, or adjustment.

---

## Installation & Setup

1. **Prerequisites**: Ensure you have Node.js (v18+) and Python (v3.10+) installed.
2. **Install Dependencies**:
   Initialize and install packages for both frontend and backend by running:
   ```bash
   npm run install:all
   ```

3. **Database Seeding**:
   Initial master data and branches are automatically seeded. To manually run the database migrations and seed default records:
   ```bash
   cd backend
   venv\Scripts\python -m app.seed
   ```

---

## Running the Application

To build the frontend and run the FastAPI server together in one command:

```bash
npm run dev
```

The application will be accessible at:
👉 **[https://clinicstock-wine.vercel.app/](https://clinicstock-wine.vercel.app/)**

- Direct URL paths (like `/medicines`, `/reports`) and browser refreshes are handled gracefully by client-side routing on the backend.
- API documentation can be accessed directly at `http://localhost:8000/docs`.
