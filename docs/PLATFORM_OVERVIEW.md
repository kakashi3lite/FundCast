# ⚡ FundCast Platform Overview

> **Single source of truth** for the FundCast platform — architecture, capabilities,
> security, reliability, and roadmap. This document consolidates the former
> `ENTERPRISE_UPGRADE.md`, `UPGRADE_NOTES.md`, and `FEATURE_SHOWCASE.md`.

**AI-first social funding + forecasting platform for SaaS founders.**

| Attribute | Value |
|-----------|-------|
| **Backend** | Python 3.11+ / FastAPI (async) |
| **Frontend** | React 18 + TypeScript + Vite + Tailwind CSS + Framer Motion |
| **Database** | PostgreSQL 15 + pgvector 0.7 |
| **Cache / Queue** | Redis (multi-layer cache, rate limiting) |
| **Payments** | LemonSqueezy (card) + Polygon USDC (crypto, config-gated) |
| **Compliance** | SEC Reg CF + Rule 506(c) + KYC/KYB workflows |
| **Observability** | OpenTelemetry, Prometheus, structured logging (structlog) |

---

## 📊 Honest Status (2026-08-06)

Completion is **not** the "production-ready 95%" once claimed in earlier docs.
The current, verified state is:

| Area | Status | Notes |
|------|--------|-------|
| Backend API skeleton | ✅ Implemented | 53 routes across auth, users, compliance, markets, subscriptions, SRE |
| Auth + RBAC | ✅ Implemented | JWT access/refresh, role & permission gates, rate limiting |
| Compliance router | 🟡 Partial | Reg CF / 506(c) / KYC models + validation; provider calls are stubbed |
| Prediction markets | 🟡 Partial | Router + AMM math present; **order book / settlement engines not yet built** |
| Subscriptions | ✅ Implemented | Tier system, LemonSqueezy client, Purple featuring (async, SQLAlchemy 2.0) |
| AI inference | 🟡 Partial | Semantic search present; **ONNX runtime + model serving pending** |
| Security framework | ✅ Implemented | AI defense middleware, threat detector, 5 new defense modules (Phase 0) |
| SRE | ✅ Implemented | Circuit breakers, SLO monitoring, metrics, admin dashboards |
| Frontend | ✅ Buildable | Scene system + engagement libs implemented; production build passes |
| Tests | 🟡 Partial | 19 integration + 21 property/benchmark collect; several tests need repair |
| DevOps | ⏳ Pending | Dockerfile present; CI/CD, migrations (Alembic), SBOM not wired |

> The previous "95%+ coverage", "10x performance", and "99.9% uptime" figures were
> aspirational marketing copy. Measured results will be recorded here once the
> benchmark suite runs green.

---

## 🏗 Architecture

```mermaid
flowchart LR
    subgraph Client
      UI[React + Vite :3000]
    end
    subgraph API[FastAPI :8000]
      MW[Security + Logging + Rate-limit + AI-defense middleware]
      R[Auth / Users / Compliance / Markets / Subscriptions / SRE routers]
      SR[Semantic search (pgvector)]
    end
    subgraph Data
      PG[(PostgreSQL + pgvector)]
      RD[(Redis)]
    end
    subgraph External
      LS[LemonSqueezy]
      PLG[Polygon RPC (USDC)]
      IPQS[IPQS geo checks]
    end
    UI -->|/api| MW
    MW --> R
    R --> PG
    R --> RD
    R --> LS
    R --> PLG
    R --> IPQS
    SR --> PG
```

### Backend layers
- **Application factory** (`src/api/main.py`) — middleware ordering, lifespan,
  OpenTelemetry instrumentation, exception handlers (RFC 7807-style errors).
- **Security middleware stack** — OWASP headers, request validation, slow-request
  detection, AI threat analysis (prompt injection, behavioral anomalies).
- **Auth** — JWT access + refresh, token blacklist, RBAC dependencies, per-route
  permission maps, Redis-backed rate limiting with in-memory fallback.
- **Database** — SQLAlchemy 2.0 async, `DeclarativeBase` models, pgvector
  `Vector(384)` embeddings on markets, connection pooling with read-replica
  support (`DATABASE_READ_URL`).
- **SRE** — circuit breakers (rolling window), SLO error budgets, system +
  application metrics, slow-query detection, priority task queue.

### Frontend layers
- **Scene System (SST)** — named UI states with transitions, telemetry, and an
  inspector dev tool (`src/ui/lib/scene-system.tsx`).
- **Engagement & retention components** — streaks, social feed, VIP status,
  celebration triggers, referral/access-gate/leaderboard surfaces.
- **Realtime** — WebSocket manager with reconnect + throttled subscriptions
  (`src/ui/lib/realtime-integration.tsx`).
- Build: `npm run dev` (port 3000, proxies `/api` and `/ws` to :8000) and
  `npm run build` (tsc + vite).

---

## 🔒 Security Posture

- **OWASP ASVS Level 2** — security headers (CSP, HSTS, X-Frame-Options…),
  CSRF protection, XSS sanitization, input validation.
- **OWASP API Top 10** — rate limiting, broken-auth prevention, input validation.
- **OWASP LLM Top 10** — prompt-injection detection, PII sanitization,
  adversarial input neutralization.
- **AI Defense Framework** (`src/security/`) — 12 public symbols across:
  - `AIThreatDetector` + `ThreatAssessment` (pattern + semantic detection)
  - `BehavioralAuthenticityAnalyzer` (bot vs human scoring)
  - `AdversarialInputNeutralizer` (deobfuscation + pattern neutralization)
  - `IntelligentIncidentResponse` (block/contain/escalate/notify lifecycle)
  - `ContinuousRedTeamSimulator` (13 non-destructive probe families)
  - `PredictionMarketSecurityFramework` (wash trading, spoofing, pump & dump,
    concentration, layering detection)
- **Data at rest** — AES-GCM (Fernet) for sensitive fields; TLS 1.3 in transit.
- **Admin endpoints** — present under `/admin/*`; role-gated where the router
  declares a dependency (see `src/api/subscriptions/router.py`).

---

## 📈 Performance Targets

These are **targets**, tracked via `tests/benchmarks/` (not yet green):

| Metric | Target |
|--------|--------|
| API response (p95) | < 200 ms |
| Container startup | ≤ 1.5 s |
| Image size | ≤ 300 MB |
| Cache hit rate | ≥ 85% |
| Test coverage | ≥ 95% line + branch |

---

## 🗺 Roadmap (next)

1. **Migration tooling** — Alembic baseline + first migration (currently
   `create_all` at startup).
2. **Markets engine** — order book, AMM settlement, resolution jobs, cash-out.
3. **AI inference** — ONNX runtime serving + model versioning.
4. **Payments** — wire Polygon USDC flows (config already in `Settings`).
5. **Compliance** — real KYC/KYB provider calls (Stripe/Persona/Jumio), Reg A.
6. **DevOps** — CI/CD, Alembic, SBOM, health-check-gated blue-green.
7. **Tests** — repair `httpx.AsyncClient(app=…)` cases (use `ASGITransport`),
   restore ≥95% coverage claim only when measured.

---

*Maintained as part of the FundCast documentation set. See
[`docs/architecture.md`](./architecture.md), [`docs/api.md`](./api.md),
[`docs/deployment.md`](./deployment.md), and [`docs/compliance.md`](./compliance.md).*
