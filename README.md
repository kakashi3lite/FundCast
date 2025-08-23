# FundCast

A social funding and prediction market platform for startup founders.

## Overview

FundCast combines prediction markets with social funding to help startup founders raise capital and make informed business decisions. The platform enables founders to participate in prediction markets about industry outcomes while connecting with potential investors through compliance-ready fundraising tools.

## Features

**Prediction Markets**
- Binary and categorical markets for startup and tech industry outcomes
- Real-time price updates and order matching
- Market creation tools for community-driven predictions

**Social Funding**  
- SEC Regulation CF and Rule 506(c) compliant fundraising
- KYC/KYB verification workflows
- Investor accreditation and compliance tracking

**Platform Tools**
- User authentication and role-based access control
- Real-time notifications and activity feeds
- Portfolio tracking and analytics

## Technology Stack

**Backend**
- Python 3.11 with FastAPI
- PostgreSQL with pgvector for semantic search
- Redis for caching and session management
- Docker containerization

**Frontend**
- TypeScript and React
- Next.js framework
- Framer Motion for animations
- Tailwind CSS for styling

**Infrastructure**
- GitHub Actions for CI/CD
- Docker multi-platform builds
- Health checks and monitoring
- Automated testing and linting

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Development Setup

```bash
# Clone the repository
git clone https://github.com/kakashi3lite/fundcast.git
cd fundcast

# Start development environment
make dev

# Run tests
make test

# Run linting
make lint
```

The application will be available at:
- API: http://localhost:8000
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/docs

### Production Deployment

```bash
# Build and deploy with Docker
make build
make up

# Or deploy to cloud platforms
# See deployment documentation for specific instructions
```

## API Documentation

Interactive API documentation is available at `/docs` when running the application. The API follows OpenAPI 3.0 standards and includes:

- Authentication endpoints
- User management
- Market operations  
- Compliance workflows
- Real-time WebSocket connections

## Testing

```bash
# Run all tests
make test

# Run specific test types
make test-unit        # Unit tests
make test-integration # Integration tests
make test-e2e         # End-to-end tests

# Generate coverage report
make coverage
```

## Security

The platform implements multiple security layers:

- OWASP security headers and middleware
- JWT authentication with refresh tokens
- Input validation and sanitization
- Rate limiting and DDoS protection
- Encrypted data storage

See [SECURITY.md](SECURITY.md) for detailed security information.

## Compliance

FundCast supports regulatory compliance for:

- SEC Regulation Crowdfunding (Reg CF)
- SEC Rule 506(c) private placements
- KYC/KYB identity verification
- Audit trails and reporting

Compliance features are configurable and can be adapted for different jurisdictions.

## Contributing

We welcome contributions to FundCast. Please read our [Contributing Guide](CONTRIBUTING.md) for information about:

- Code style and standards
- Pull request process  
- Issue reporting
- Development workflows

## Documentation

Additional documentation is available in the `/docs` directory:

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Compliance Guide](docs/compliance.md)

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Support

For questions and support:

- GitHub Issues: Report bugs and feature requests
- Email: support@fundcast.ai
- Documentation: Comprehensive guides and API reference

---

*FundCast is a financial technology platform. Investment opportunities involve risk and regulatory considerations. Please consult appropriate advisors and review all applicable regulations.*