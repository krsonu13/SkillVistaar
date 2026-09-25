# SkillVistaar — Deployment Guide

Complete guide for local development and production deployment of the SkillVistaar platform.

## Architecture

```
GitHub Repository
├── backend/          → Render (Web Service + PostgreSQL)
│   ├── FastAPI + SQLAlchemy + Alembic
│   ├── JWT Authentication
│   └── WebSocket real-time events
└── frontend/         → Vercel (Static SPA)
    ├── React + TypeScript + Vite
    └── Tailwind CSS
```

---

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Environment Variables Reference](#environment-variables-reference)
3. [Production Deployment — Backend (Render)](#production-deployment--backend-render)
4. [Production Deployment — Frontend (Vercel)](#production-deployment--frontend-vercel)
5. [Database & Migrations](#database--migrations)
6. [CORS Configuration](#cors-configuration)
7. [File Storage in Production](#file-storage-in-production)
8. [Email & SMS Configuration](#email--sms-configuration)
9. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites

- Python 3.11+ (tested with 3.14)
- Node.js 18+ and npm
- PostgreSQL 14+
- Git

### 1. Backend Setup

```bash
# Clone and navigate to the project
cd SkillVistaar

# Create Python virtual environment
cd backend
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your local PostgreSQL credentials and generate JWT secrets:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 2. PostgreSQL Setup (Local)

```bash
# Create database and user
psql -U postgres
```

```sql
CREATE USER skillvistaar WITH PASSWORD 'your_dev_password';
CREATE DATABASE skillvistaar OWNER skillvistaar;
GRANT ALL PRIVILEGES ON DATABASE skillvistaar TO skillvistaar;
\q
```

Update `backend/.env`:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=skillvistaar
POSTGRES_USER=skillvistaar
POSTGRES_PASSWORD=your_dev_password
DATABASE_URL=postgresql+asyncpg://skillvistaar:your_dev_password@localhost:5432/skillvistaar
```

### 3. Run Database Migrations

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

### 4. Start Backend Server

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

### 5. Frontend Setup

```bash
cd frontend
npm install

# Configure environment (optional for local dev — Vite proxy handles it)
cp .env.example .env
# For local dev, you can leave VITE_API_BASE_URL unset.
# Vite proxy in vite.config.ts routes /api/* to localhost:8000.

# Start development server
npm run dev
```

The frontend will be available at `http://127.0.0.1:3000`

### 6. Run Tests

```bash
# Backend tests
cd backend
source venv/bin/activate
python -m pytest

# Frontend build check
cd frontend
npm run build
```

---

## Environment Variables Reference

### Backend (Required for Production)

| Variable | Description | Example |
|---|---|---|
| `ENVIRONMENT` | `development` or `production` | `production` |
| `DEBUG` | Enable debug mode (forced `false` in production) | `false` |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql+asyncpg://user:pass@host:5432/db` |
| `JWT_SECRET_KEY` | Access token signing secret (min 32 chars) | *(generate with `secrets.token_urlsafe(48)`)* |
| `JWT_REFRESH_SECRET_KEY` | Refresh token signing secret (min 32 chars) | *(generate with `secrets.token_urlsafe(48)`)* |
| `CORS_ORIGINS` | Allowed frontend origins (comma-separated) | `https://skillvistaar.vercel.app` |
| `SMTP_HOST` | SMTP server hostname | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USERNAME` | SMTP username / email | `noreply@example.com` |
| `SMTP_PASSWORD` | SMTP password / app password | *(16-char Google App Password)* |
| `SMTP_FROM_EMAIL` | Sender email address | `noreply@example.com` |

### Backend (Optional)

| Variable | Description | Default |
|---|---|---|
| `PORT` | Server port (set by Render automatically) | `8000` |
| `STORAGE_BACKEND` | `local` or `s3` | `local` |
| `STORAGE_S3_BUCKET_NAME` | S3/R2 bucket name | *(empty)* |
| `STORAGE_S3_ENDPOINT_URL` | S3-compatible endpoint URL | *(empty)* |
| `STORAGE_S3_ACCESS_KEY_ID` | S3 access key | *(empty)* |
| `STORAGE_S3_SECRET_ACCESS_KEY` | S3 secret key | *(empty)* |
| `SMS_PROVIDER` | `sandbox`, `twilio`, or `msg91` | `sandbox` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `AI_ENABLED` | Enable AI features | `true` |
| `BLOCKCHAIN_ENABLED` | Enable blockchain features | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Frontend (Vercel)

| Variable | Description | Example |
|---|---|---|
| `VITE_API_BASE_URL` | Backend API URL **(REQUIRED in production)** | `https://skillvistaar-api.onrender.com/api/v1` |

---

## Production Deployment — Backend (Render)

### 1. Create a Web Service on Render

1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect your GitHub repository
3. Configure:

| Setting | Value |
|---|---|
| **Name** | `skillvistaar-api` |
| **Root Directory** | `backend` |
| **Runtime** | Python |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

> **Note**: For multi-worker production performance, use:
> ```
> gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
> ```
> Adjust `--workers` based on your Render plan's available RAM (1 worker per 256 MB).

### 2. Add PostgreSQL

1. On Render → **New** → **PostgreSQL**
2. Create the database (e.g., `skillvistaar-db`)
3. Copy the **Internal Database URL** from the PostgreSQL dashboard
4. Add it as `DATABASE_URL` in the Web Service's environment variables

### 3. Configure Environment Variables

In the Render Web Service dashboard → **Environment**:

```
ENVIRONMENT=production
DATABASE_URL=<paste Render PostgreSQL Internal URL>
JWT_SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(48))">
JWT_REFRESH_SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(48))">
CORS_ORIGINS=https://your-frontend.vercel.app
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_16_char_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
SMTP_FROM_NAME=SkillVistaar Portal
SMS_PROVIDER=sandbox
ALLOW_DEMO_SMS=true
STORAGE_BACKEND=local
LOG_LEVEL=INFO
```

### 4. Run Database Migrations

After the first deploy, open the Render **Shell** tab and run:

```bash
alembic upgrade head
```

Or add a pre-deploy command in Render's settings:
```
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 5. Verify Deployment

```bash
curl https://skillvistaar-api.onrender.com/health
# Expected: {"status":"healthy","project":"SkillVistaar","database":"connected",...}

curl https://skillvistaar-api.onrender.com/health/live
# Expected: {"status":"alive","project":"SkillVistaar"}
```

---

## Production Deployment — Frontend (Vercel)

### 1. Create a Vercel Project

1. Go to [vercel.com](https://vercel.com) → **New Project**
2. Import your GitHub repository
3. Configure:

| Setting | Value |
|---|---|
| **Root Directory** | `frontend` |
| **Framework Preset** | Vite |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |

### 2. Configure Environment Variables

In Vercel → **Settings** → **Environment Variables**:

```
VITE_API_BASE_URL=https://skillvistaar-api.onrender.com/api/v1
```

> **Important**: Vite bakes `VITE_*` variables into the build at compile time. After changing this variable, you must **redeploy** (trigger a new build) for the change to take effect.

### 3. SPA Routing

The `frontend/vercel.json` file is already configured with rewrites to support React Router's client-side routing:

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

This ensures direct navigation to routes like `/candidate`, `/employer`, `/login` works correctly.

### 4. Verify Deployment

Visit your Vercel URL and test:
- Landing page loads
- Login page works
- Direct navigation to `/login`, `/signup`, `/candidate` works (no 404)
- API calls reach the backend

---

## Database & Migrations

### Alembic Commands

```bash
cd backend
source venv/bin/activate

# Apply all pending migrations
alembic upgrade head

# Check if migrations are up to date
alembic check

# View current migration version
alembic current

# View migration history
alembic history --verbose
```

### Production Migrations

On Render, use the Shell tab or include in your start command:

```bash
# Pre-deploy hook (recommended)
alembic upgrade head
```

> **Warning**: Never run `alembic downgrade` in production without a backup.

### Fresh Database Setup

On a completely new PostgreSQL database, `alembic upgrade head` will create all tables from scratch. No manual SQL is required.

---

## CORS Configuration

CORS is configured via the `CORS_ORIGINS` environment variable.

### Local Development
```
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
```

### Production
```
CORS_ORIGINS=https://your-frontend.vercel.app
```

### Multiple Origins
```
CORS_ORIGINS=https://skillvistaar.vercel.app,https://www.skillvistaar.com
```

### JSON Format (also supported)
```
CORS_ORIGINS=["https://skillvistaar.vercel.app","https://www.skillvistaar.com"]
```

---

## File Storage in Production

### Important: Render's Ephemeral Filesystem

Render's filesystem is **ephemeral** — files stored locally via `STORAGE_BACKEND=local` will be **lost on every redeploy**. This affects uploaded documents, certificates, and profile attachments.

### Recommended: Cloudflare R2 (Free Tier)

Cloudflare R2 offers 10 GB free storage with zero egress fees:

```
STORAGE_BACKEND=s3
STORAGE_S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
STORAGE_S3_BUCKET_NAME=skillvistaar
STORAGE_S3_ACCESS_KEY_ID=<your_r2_access_key>
STORAGE_S3_SECRET_ACCESS_KEY=<your_r2_secret_key>
STORAGE_S3_REGION=auto
```

### Alternative: Supabase Storage (Free Tier)

```
STORAGE_BACKEND=s3
STORAGE_S3_ENDPOINT_URL=https://<project_id>.supabase.co/storage/v1/s3
STORAGE_S3_BUCKET_NAME=skillvistaar
STORAGE_S3_ACCESS_KEY_ID=<supabase_key>
STORAGE_S3_SECRET_ACCESS_KEY=<supabase_secret>
```

The application code automatically selects `S3StorageService` when `STORAGE_BACKEND=s3` is set — no code changes required.

---

## Email & SMS Configuration

### Gmail SMTP

1. Enable 2-Factor Authentication on your Google account
2. Go to Google Account → Security → App Passwords
3. Generate a 16-character App Password
4. Configure:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=<16_char_app_password>
SMTP_FROM_EMAIL=your_email@gmail.com
SMTP_USE_TLS=true
```

### SMS (Sandbox Mode)

For development and free-tier deployment, SMS OTPs are simulated:

```
SMS_PROVIDER=sandbox
ALLOW_DEMO_SMS=true
```

The OTP will be displayed on the verification screen instead of being sent via SMS.

### SMS (Twilio — Production)

```
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

---

## Troubleshooting

### Backend won't start on Render

- Check that `DATABASE_URL` is set and the PostgreSQL addon is running
- Verify `JWT_SECRET_KEY` and `JWT_REFRESH_SECRET_KEY` are at least 32 characters
- Check Render logs for the specific error message

### Frontend API calls fail (CORS errors)

- Verify `CORS_ORIGINS` on the backend includes your exact Vercel URL (with `https://`, no trailing slash)
- Redeploy the backend after changing `CORS_ORIGINS`

### Frontend shows blank page or 404 on routes

- Verify `frontend/vercel.json` is present with the SPA rewrite rule
- Redeploy on Vercel

### Database migrations fail

```bash
# Check current state
alembic current
alembic history

# If stuck, verify DATABASE_URL is correct
python -c "from app.core.config import settings; print(settings.database_url_async)"
```

### WebSocket connection fails in production

- Verify `VITE_API_BASE_URL` points to the backend (the WebSocket URL is derived from it)
- Ensure the backend's CORS allows the frontend origin
- Render supports WebSocket connections on all plans
