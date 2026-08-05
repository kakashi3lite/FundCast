# FundCast API Reference

> Summary of the HTTP API as implemented. Full machine-readable spec:
> [`api/openapi.yaml`](./api/openapi.yaml). All endpoints are mounted under
> `/api/v1`.

## Conventions

- **Auth**: `Authorization: Bearer <jwt>` (access token; refresh via `/auth/refresh`).
- **Errors**: RFC 7807-style JSON `{ "error": <code>, "message": <text> }`;
  `FundCastException` subclasses carry `status_code` + `error_code`.
- **Rate limiting**: per-user/per-IP, Redis-backed (in-memory fallback).

## Authentication — `src/api/auth/router.py`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create account (validates password strength) |
| POST | `/auth/login` | Exchange credentials for JWT pair |
| POST | `/auth/refresh` | Rotate access token |
| POST | `/auth/logout` | Revoke token (blacklist) |

## Users — `src/api/users/router.py`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users/me` | Current profile |
| PATCH | `/users/me` | Update profile |
| GET | `/users` | List (admin, paginated) |
| GET | `/users/{id}` | Public profile |
| PATCH | `/users/{id}` | Admin update |
| DELETE | `/users/{id}` | Admin deactivate (self-deactivation blocked) |

Dependencies: `get_current_user`, `require_permissions`, `require_roles`,
`require_verified_user`, `require_kyc_verified_user`,
`require_accredited_user`, `get_admin_user`.

## Compliance — `src/api/compliance/router.py`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/compliance/kyc` | Initiate KYC (provider: stripe/persona/jumio) |
| GET | `/compliance/kyc/{reference}` | KYC status |
| POST | `/compliance/accreditation` | Accredited-investor verification |
| POST | `/compliance/kyb` | Business verification |
| POST | `/compliance/offering` | Reg CF / 506(c) offering validation |

> ⚠️ Provider calls are **stubbed** (generate reference URLs); wire to
> Stripe/Persona/Jumio in production.

## Markets — `src/api/markets/router.py`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/markets` | Create market (binary/categorical/scalar) |
| GET | `/markets` | List markets (filters) |
| GET | `/markets/{id}` | Market detail |
| POST | `/markets/{id}/orders` | Place order (market/limit) |
| PATCH | `/markets/{id}` | Update market |
| POST | `/markets/{id}/resolve` | Resolve market |

Includes `calculate_amm_price` (constant-product) and
`calculate_probability_from_shares` helpers.

## Subscriptions — `src/api/subscriptions/router.py`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/subscriptions/tiers` | All tiers |
| GET | `/subscriptions/tiers/comparison` | Pricing-page payload (frontend uses this) |
| GET | `/subscriptions/my-subscription` | Current user's subscription |
| POST | `/subscriptions/checkout` | Create LemonSqueezy checkout |
| POST | `/subscriptions/upgrade` | Upgrade tier (prorated) |
| POST | `/subscriptions/cancel` | Cancel (immediate or end-of-period) |
| POST | `/subscriptions/reactivate` | Reactivate canceled |
| POST | `/subscriptions/billing-cycle` | Toggle monthly/annual |
| GET | `/subscriptions/purple-featuring/queue` | Featuring queue + schedule |
| GET | `/subscriptions/purple-featuring/current` | Live featured founders |
| POST | `/subscriptions/purple-featuring/{id}/content` | Customize featuring content |
| POST | `/subscriptions/purple-featuring/{id}/track` | Track impression/click |
| GET | `/subscriptions/analytics` | User analytics |
| GET | `/subscriptions/admin/metrics` | Platform metrics (admin) |
| POST | `/subscriptions/webhooks/lemonsqueezy` | Payment webhook (HMAC-verified) |
| GET | `/subscriptions/features/{tier_slug}` | Tier feature detail |
| GET | `/subscriptions/referral/{code}` | Referral validation |

## System / SRE — `src/api/main.py`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness (`status`, `version`, `timestamp`) |
| GET | `/admin/stats` | System performance stats |
| GET | `/admin/sre/dashboard` | SRE metrics |
| GET | `/admin/sre/slos` | SLO + error budgets |
| GET | `/admin/cache/clear` | Clear cache |
| GET | `/admin/tasks/{id}` | Task status |

## WebSocket

- `/ws` — realtime updates (used by `src/ui/lib/realtime-integration.tsx`).

## OpenAPI

- Interactive docs at `/docs` (Swagger) and `/redoc` when `DEBUG=true`.
- `docs/api/openapi.yaml` is the hand-maintained spec; regenerate from the app
  (`app.openapi()`) and reconcile endpoint coverage before release.
