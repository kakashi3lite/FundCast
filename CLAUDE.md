# Claude Code Context

## Project: FundCast ⚡
AI-first social funding + forecasting platform for SaaS founders

## 📊 **Progress Status: ~45% Complete** (accurate as of 2026-08-06)
✅ **Backend Foundation**: FastAPI + Security + Auth + RBAC + Database  
✅ **Compliance System**: Reg CF + 506(c) + KYC/KYB workflows (models + validation)  
🟡 **Prediction Markets**: Router + AMM math present; order book/settlement engines pending  
✅ **Subscriptions**: Tier system, LemonSqueezy client, Purple featuring (async, SQLAlchemy 2.0)  
✅ **Security Framework**: AI defense middleware, threat detector, 5 defense modules (behavioral, adversarial, incident response, red team, market integrity)  
🟡 **AI Inference**: Semantic search implemented; ONNX runtime + model serving pending  
🟡 **Frontend**: React + Vite + TS + Tailwind + Framer Motion — buildable, production build passes  
🟡 **Tests**: 19 integration + 21 property/benchmark collect; several tests need repair  
⏳ **DevOps**: Dockerfile present; CI/CD + Alembic migrations + SBOM pending

> Earlier claims of "70% complete" and "≥95% test coverage" were aspirational.
> Coverage figures will be reported only when the suite runs green.

## Architecture
- **Backend**: Python FastAPI + async SQLAlchemy 2.0 + pgvector ✅
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS + Framer Motion 🟡
- **Database**: PostgreSQL + pgvector 0.7 ✅
- **Payments**: LemonSqueezy + Polygon USDC (config-gated) 🟡
- **Deployment**: Docker + GitHub Actions CI/CD ⏳

## Key Commands
```bash
# Development
make dev          # Start development servers
make test         # Run all tests with coverage
make lint         # Run linting and formatting
make bench        # Run performance benchmarks
make check        # Run all checks (lint + test + security)

# Build & Deploy
make build        # Build Docker containers
make up           # Start with docker-compose
make sbom         # Generate SBOM

# Security & Testing
make security     # Run security scans (bandit, safety, semgrep)
make test-unit    # Unit tests only
make test-e2e     # End-to-end tests
```

## Security Standards ✅ **IMPLEMENTED**
- **OWASP ASVS Level 2**: Complete middleware stack with headers, CSRF, XSS protection
- **OWASP API Security Top 10**: Input validation, rate limiting, broken authentication prevention
- **OWASP LLM Security Top 10**: Prompt injection prevention, PII sanitization, model access controls
- **AI Defense Framework**: Threat detector, behavioral authenticity, adversarial input neutralizer, incident response, red team simulator, prediction-market integrity
- **Encryption**: AES-GCM for data at rest, TLS 1.3 in transit
- **Red Team Protection**: SQL injection, path traversal, code injection prevention
- **RBAC**: Fine-grained permissions with role inheritance

## Performance Targets (aspirational — to be measured)
- Container startup: ≤1.5s
- Image size: ≤300MB  
- Test coverage: ≥95% line+branch (target; suite not yet green)
- API response time: <200ms p95

## Compliance Features ✅ **COMPLETED**
- **Reg CF**: Full SEC Regulation Crowdfunding workflows ($5M limits)
- **Rule 506(c)**: Accredited investor verification with Stripe/Persona
- **KYC/KYB**: Multi-provider identity and business verification
- **Audit Trails**: Comprehensive compliance tracking and reporting
- **Market Regulation**: Accredited investor controls for restricted markets

## AI Features ✅ **CORE IMPLEMENTED**
- **Semantic Search**: Security-hardened codebase context search
- **Content Sanitization**: PII and sensitive data protection
- **Query Validation**: Anti-injection and path traversal protection
- **Rate Limiting**: AI request throttling and abuse prevention

## Trading System 🟡 **PARTIALLY IMPLEMENTED**
- **Dual Engine**: Router + AMM math present; **order book engine + settlement pending**
- **Market Types**: Binary, categorical, and scalar prediction markets  
- **Risk Management**: Position limits, balance verification, settlement controls
- **Real-time Analytics**: Live market statistics and portfolio tracking

## API Coverage ✅ **COMPREHENSIVE**
- **Authentication**: Registration, login, token refresh, logout
- **User Management**: Profile CRUD, admin controls, role management
- **Compliance**: KYC/KYB workflows, accreditation verification, audit reports
- **Markets**: Market creation, trading, position tracking, resolution
- **Subscriptions**: Tiers, LemonSqueezy checkout, Purple featuring, webhooks, metrics
- **Security**: All endpoints protected with RBAC and input validation