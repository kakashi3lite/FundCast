# FundCast Compliance Guide

> FundCast combines SEC-regulated investment workflows (Reg CF / 506(c)) with
> prediction markets. This guide documents the compliance model as implemented
> and the operating constraints for prediction/tournament play
> (**Massachusetts only, IPQS-enforced**).

## 1. Regulatory Framework

### Securities crowdfunding
- **Regulation Crowdfunding (Reg CF)** — offerings up to $5M/year via a
  registered intermediary; per-offering validation in
  `src/api/compliance/router.py` (`OfferingComplianceRequest`).
- **Rule 506(c)** — general solicitation with verified accredited investors
  (income/net-worth/professional methods).
- **Reg A** — modeled in the enum but **not yet validated** (Tier 1 $20M /
  Tier 2 $75M limits pending).

### Prediction / tournament play
- Operated as **information markets** — prediction on business outcomes, not
  casino games.
- **Jurisdiction**: Massachusetts only (`ALLOWED_JURISDICTIONS=["MA"]`),
  enforced via **IPQS** (IP reputation + proxy/VPN detection + geolocation) with
  billing-address fallback.
- **MA statutes under review**: MGL c.10 §29–36, MGL c.271 §5A, 205 CMR.
  A MA gaming attorney opinion is **required before launch** — classification of
  prediction markets with engagement mechanics is novel territory.
- Engagement mechanics (streaks, leaderboards, near-miss presentation) are
  documented as retention tooling with responsible-play guardrails.

## 2. Identity & Business Verification

### KYC (individual)
- Providers: Stripe Identity, Persona, Jumio (`provider` field validated).
- Flow: `POST /compliance/kyc` → provider session → status poll.
- **Status**: models + validation implemented; provider calls currently stubbed
  (return reference URLs) — wire real SDK calls before production.

### KYB (business)
- Company verification with EIN validation (`^\d{2}-\d{7}$`), entity type,
  incorporation country (ISO-2).
- `Company.kyb_status` lifecycle: pending → verified / rejected / expired.

### Accreditation (506(c))
- Methods: income / net worth / professional certification.
- Endpoint: `POST /compliance/accreditation`.

## 3. Model-Level Enforcement

`src/api/database.py`:
- `User.kyc_status`, `User.accredited_status` drive the dependency gates
  `require_kyc_verified_user` / `require_accredited_user`.
- Restricted markets (high-stakes) require accredited status
  (`validate_market_access` in `src/api/markets/router.py`).
- `Offering` carries Reg CF / 506(c) qualification + `Decimal` amounts.

## 4. Audit & Reporting

- `FundCastException` hierarchy + structured logs (structlog, request IDs).
- Compliance endpoints log reference IDs for audit trails.
- `docs/api.md` documents the compliance endpoint surface.

## 5. Operating Controls (Prediction Play)

| Control | Mechanism |
|---------|-----------|
| Jurisdiction gating | IPQS middleware (`IPQS_API_KEY`, `IPQS_ENABLED`) |
| Self-exclusion | 30/90/180-day or permanent, enforced at API layer |
| Deposit/loss limits | per-user daily/weekly caps |
| Cool-downs | strategy-review panel after sustained losing sessions |
| No recovery up-sells | losses surface review, never "double down" |
| Payments | LemonSqueezy (cards) + Polygon USDC (config-gated) |

## 6. Pending Compliance Work

- [ ] Real KYC/KYB provider integrations (Stripe/Persona/Jumio)
- [ ] Reg A tier validation (Tier 1 / Tier 2 limits)
- [ ] Audit-trail persistence + compliance reporting exports
- [ ] MA legal opinion + regulator engagement
- [ ] IPQS middleware wiring (config present in `Settings`)
