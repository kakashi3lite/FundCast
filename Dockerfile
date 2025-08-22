# Multi-stage production Dockerfile for FundCast
# Optimized for security, performance, and minimal size

# ============================================================================
# BUILD STAGE
# ============================================================================
FROM python:3.12-slim as builder

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Metadata
LABEL org.opencontainers.image.title="FundCast Platform"
LABEL org.opencontainers.image.description="AI-first social funding + forecasting platform"
LABEL org.opencontainers.image.version="${VERSION:-latest}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.vendor="FundCast"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.url="https://fundcast.ai"
LABEL org.opencontainers.image.source="https://github.com/kakashi3lite/FundCast"

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gcc \
    g++ \
    git \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Create build user
RUN useradd --create-home --shell /bin/bash builder

# Switch to build user and working directory
USER builder
WORKDIR /home/builder

# Copy dependency files
COPY --chown=builder:builder pyproject.toml poetry.lock* ./

# Install Python dependencies
RUN poetry install --no-dev --no-root && rm -rf $POETRY_CACHE_DIR

# Copy source code
COPY --chown=builder:builder src/ ./src/
COPY --chown=builder:builder README.md ./

# Install the application
RUN poetry install --no-dev

# ============================================================================
# RUNTIME STAGE
# ============================================================================
FROM python:3.12-slim as runtime

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# Runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000 \
    HOST=0.0.0.0

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Runtime libraries
    libpq5 \
    # Security utilities
    ca-certificates \
    # Monitoring utilities
    curl \
    # Process management
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove \
    && apt-get clean

# Create application user
RUN groupadd -r fundcast && \
    useradd -r -g fundcast -d /app -s /bin/bash -c "FundCast App User" fundcast

# Create application directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=fundcast:fundcast /home/builder/.venv /app/.venv

# Copy application source
COPY --from=builder --chown=fundcast:fundcast /home/builder/src /app/src

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/tmp && \
    chown -R fundcast:fundcast /app

# Copy startup script
COPY --chown=fundcast:fundcast << 'EOF' /app/entrypoint.sh
#!/bin/bash
set -e

# Health check function
health_check() {
    echo "🏥 Performing health check..."
    
    # Check Python dependencies
    python -c "import fastapi, sqlalchemy, pydantic, redis" || {
        echo "❌ Critical dependencies missing"
        exit 1
    }
    
    # Check database connectivity (if DATABASE_URL is set)
    if [ -n "$DATABASE_URL" ]; then
        python -c "
import asyncio
import asyncpg
import sys
async def check_db():
    try:
        conn = await asyncpg.connect('$DATABASE_URL')
        await conn.execute('SELECT 1')
        await conn.close()
        print('✅ Database connection successful')
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        sys.exit(1)
asyncio.run(check_db())
        "
    fi
    
    echo "✅ Health check passed"
}

# Run database migrations (if applicable)
migrate_database() {
    if [ -f "/app/alembic.ini" ] && [ -n "$DATABASE_URL" ]; then
        echo "🔄 Running database migrations..."
        alembic upgrade head || {
            echo "⚠️ Migration failed, continuing anyway"
        }
    fi
}

# Main execution
main() {
    echo "🚀 Starting FundCast Platform..."
    echo "   Version: ${VERSION:-unknown}"
    echo "   Build: ${VCS_REF:-unknown}"
    echo "   Date: ${BUILD_DATE:-unknown}"
    
    # Perform health check
    health_check
    
    # Run migrations
    migrate_database
    
    # Start the application
    echo "🌐 Starting web server on $HOST:$PORT"
    exec uvicorn api.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers "${WORKERS:-1}" \
        --worker-class uvicorn.workers.UvicornWorker \
        --access-log \
        --log-level "${LOG_LEVEL:-info}"
}

# Handle different commands
case "${1:-}" in
    "health")
        health_check
        ;;
    "migrate")
        migrate_database
        ;;
    "shell")
        exec python
        ;;
    "bash")
        exec bash
        ;;
    "")
        main
        ;;
    *)
        exec "$@"
        ;;
esac
EOF

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Security hardening
RUN chown root:root /app/entrypoint.sh && \
    chmod 755 /app/entrypoint.sh

# Switch to application user
USER fundcast

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use tini for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]

# Default command (can be overridden)
CMD []

# Add metadata
LABEL org.opencontainers.image.title="FundCast Platform" \
      org.opencontainers.image.description="AI-first social funding + forecasting platform" \
      org.opencontainers.image.version="${VERSION:-latest}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.vendor="FundCast" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.url="https://fundcast.ai" \
      org.opencontainers.image.source="https://github.com/kakashi3lite/FundCast"