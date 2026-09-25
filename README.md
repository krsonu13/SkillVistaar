# SkillVistaar

SkillVistaar is a unified National Skill Verification & Stakeholder Management Platform connecting Candidates, Employers, Educational Institutions, and Statutory Government Verifiers.

---

## Local Architecture

- **Frontend**: React 18, TypeScript, Tailwind CSS, Vite
  - Local URL: [http://127.0.0.1:3000](http://127.0.0.1:3000)
  - Vite dev server proxies `/api` requests directly to `http://127.0.0.1:8000`.
- **Backend**: FastAPI, SQLAlchemy 2.0 (Async), Alembic, Pydantic v2
  - Local URL: [http://127.0.0.1:8000](http://127.0.0.1:8000)
  - Interactive API Docs (Swagger UI): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
  - ReDoc Documentation: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
  - Health Diagnostic Endpoint: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## Getting Started Locally

### 1. Prerequisites
- **Node.js**: v18+ or v20+
- **Python**: v3.12+
- **npm**: v9+

### 2. Environment Configuration

The backend and frontend are already preconfigured for `localhost`:
- `backend/.env` is configured to bind to `127.0.0.1:8000`.
- `frontend/.env` is configured to target `http://127.0.0.1:8000/api/v1`.

### 3. Running the Applications

You can start each service from the project root:

#### Run Backend
```bash
npm run backend:dev
```
*(Or directly: `cd backend && venv/bin/python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`)*

#### Run Frontend
```bash
npm run dev
```
*(Or directly: `cd frontend && npm run dev`)*

The frontend will be accessible at **http://127.0.0.1:3000**.

---

## Testing & Verification

- **Backend Pytest Suite**:
  ```bash
  npm run backend:test
  ```
- **Frontend Production Build**:
  ```bash
  npm run build
  ```
