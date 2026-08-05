# Changelog

All notable changes to FundCast are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (2026-08-06 — Structural Repair)
- **Security framework completed**: implemented 5 missing modules
  (`behavioral_analyzer`, `adversarial_filter`, `incident_response`,
  `red_team_simulator`, `market_security`) so the full 12-symbol package imports.
- **AI defense degraded gracefully**: heavy ML deps (torch/transformers/sklearn)
  are now optional with a pure-Python fallback shim.
- **Configuration**: added LemonSqueezy (11 fields), `DATABASE_READ_URL`,
  `AI_DEFENSE_ENABLED`, Polygon crypto (USDC), and IPQS geo-enforcement settings.
- **Frontend**: replaced a `package.json` that belonged to an unrelated project;
  added Vite + React + TypeScript build (tsconfig, vite, tailwind, postcss,
  entry point). Implemented the 9 missing `src/ui/lib` modules and the
  `lib/index.ts` barrel.
- **Exceptions**: added `CacheError`, `TaskError`, `DatabaseError`,
  `CircuitBreakerError`, `ServiceUnavailableError`.
- **Docs**: added `docs/PLATFORM_OVERVIEW.md`, `docs/architecture.md`,
  `docs/api.md`, `docs/deployment.md`, `docs/compliance.md`.

### Changed
- **Subscriptions module converted to async SQLAlchemy 2.0** (router, service,
  featuring, lemonsqueezy); fixed import paths; added `get_admin_user`.
- **Database**: money columns re-typed `Mapped[int]` → `Mapped[Decimal]`;
  renamed reserved `metadata` attributes to `metadata_json` (column preserved);
  engine pool args now applied only for PostgreSQL (SQLite tests work).
- **Pydantic v2 migration**: `Field(regex=…)` → `Field(pattern=…)` (12 sites).
- **`@task` decorator** defers registration until a running event loop exists.
- **Tests**: `asyncio_mode = "auto"` in pytest config; `pytest_asyncio.async_test`
  compatibility shim; collection now succeeds (19 integration + 21 property/
  benchmark tests).

### Removed
- Aspirational "95%+ coverage", "10x performance", "99.9% uptime" claims moved
  to explicit targets in `docs/PLATFORM_OVERVIEW.md` (not yet measured).

## [1.0.0] - 2024-01-15

### Added
- **Core Platform**: FastAPI async backend, JWT auth + RBAC, PostgreSQL +
  pgvector models, Redis caching, security middleware stack.
- **AI Inference**: semantic search (pgvector), content sanitization/PII
  protection, query validation, rate limiting.
- **Compliance**: Reg CF + 506(c) workflows, KYC/KYB models, audit trails.
- **Trading**: prediction market models (binary/categorical/scalar), AMM price
  math, position tracking, risk controls.
- **Security**: OWASP ASVS L2 header stack, AES-GCM at rest, threat detection.
- **API documentation**: OpenAPI 3.0 spec + Swagger/ReDoc.

> Note: 1.0.0 entries reflect the original scaffold. Several capabilities were
> verified as partial during the 2026-08-06 audit (see Unreleased + docs).

## [0.1.0] - 2024-01-01

### Added
- Initial project structure and basic FastAPI application setup.

- Database models and relationships
- Authentication middleware
- Basic API endpoints

---

## Release Notes Format

### Types of Changes
- **Added** for new features
- **Changed** for changes in existing functionality  
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

### Semantic Versioning
- **MAJOR** version for incompatible API changes
- **MINOR** version for backward-compatible functionality additions
- **PATCH** version for backward-compatible bug fixes