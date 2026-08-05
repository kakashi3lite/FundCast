# FundCast Deployment Guide

> Status: **Dockerfile + docker-compose present; CI/CD and Alembic migrations
> are pending.** This guide documents the current state and the intended
> production path.

## 1. Prerequisites

- Python 3.11+
- Node.js 18+ (frontend build)
- PostgreSQL 15 with `pgvector` extension
- Redis 7
- Node 18+ for `npm run build`

## 2. Local Development

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Frontend
npm install

# Environment
export SECRET_KEY="<32+ chars>"
export JWT_SECRET_KEY="<32+ chars>"
export ENCRYPTION_KEY="$(python -c 'import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())')"
export DATABASE_URL="postgresql+asyncpg://fundcast:fundcast@localhost:5432/fundcast"
export REDIS_URL="redis://localhost:6379/0"

# Run (two terminals)
make dev            # uvicorn on :8000
npm run dev         # Vite on :3000 (proxies /api to :8000)
```

Database bootstrap (dev only, until Alembic lands):

```bash
python -c "from src.api.database import Base; from src.api.main import app; import asyncio"
# or rely on the lifespan create_all path
```

## 3. Docker

```bash
make build    # docker compose build
make up       # docker compose up -d
```

`docker-compose.yml` defines `api`, `db` (postgres + pgvector), and `redis`.
The `Dockerfile` is a multi-stage build; container startup ≤ 1.5 s and image
size ≤ 300 MB are **targets** and must be re-measured after the CI pipeline is
wired.

## 4. Environment Variables

See `src/api/config.py` for the authoritative list. Key variables:

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SECRET_KEY` / `JWT_SECRET_KEY` | ✅ | — | signing (≥ 32 chars) |
| `ENCRYPTION_KEY` | ✅ | — | Fernet key (32-byte url-safe base64) |
| `DATABASE_URL` | ✅ | — | asyncpg DSN |
| `DATABASE_READ_URL` | | — | read-replica DSN |
| `REDIS_URL` | | `redis://localhost:6379/0` | cache + rate limit |
| `CORS_ORIGINS` / `ALLOWED_HOSTS` | | localhost | security |
| `LEMONSQUEEZY_*` | | — | payment client |
| `CRYPTO_PAYMENT_ENABLED` / `POLYGON_RPC_URL` / `USDC_CONTRACT_ADDRESS` | | — | Polygon USDC |
| `IPQS_API_KEY` / `IPQS_ENABLED` / `ALLOWED_JURISDICTIONS` | | `["MA"]` | geo-enforcement |
| `AI_DEFENSE_ENABLED` | | `true` | threat detection |
| `DEBUG` | | `false` | docs + reload |

## 5. Production Checklist (pending items)

- [ ] **Alembic** baseline + first migration (replace `create_all`).
- [ ] **CI/CD** (GitHub Actions): lint, test, build, SBOM, container scan.
- [ ] **Secrets management** (vault/env-file in CI).
- [ ] **Observability**: OTEL collector endpoint (`OTEL_EXPORTER_OTLP_ENDPOINT`),
      Prometheus scrape, Sentry DSN.
- [ ] **Geo-enforcement**: enable `IPQS_ENABLED` + wire IPQS middleware.
- [ ] **Crypto payments**: enable `CRYPTO_PAYMENT_ENABLED` after contract
      review + MA legal sign-off.
- [ ] **Health-check gated blue-green** deployment.
- [ ] **Backups**: pg_dump schedule + SLO monitoring persistence.
