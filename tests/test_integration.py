"""Integration tests for FundCast API with Red Team security validation."""

import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Test environment setup
os.environ.update(
    {
        "SECRET_KEY": "test_secret_key_32_characters_long!!",
        "JWT_SECRET_KEY": "test_jwt_secret_key_32_characters_long!",
        "ENCRYPTION_KEY": "fPL2BaxAYKKjr0ZjN_Tz7rJ1c_Xn_Lz8DhbE9gCGmM0=",  # Base64 encoded 32-byte key
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/1",
        "DEBUG": "true",
        "ENVIRONMENT": "test",
    }
)

from src.api.auth.security import get_password_hash
from src.api.database import Base, User, get_database
from src.api.main import app


# Test database setup
@pytest_asyncio.fixture
async def test_db():
    """Create test database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_database():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_database] = override_get_database

    yield async_session

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(test_db):
    """Create a test user."""
    async with test_db() as session:
        user = User(
            email="test@example.com",
            password_hash=get_password_hash("TestPassword123!"),
            full_name="Test User",
            username="testuser",
            email_verified=True,
            roles=["user"],
            permissions=["user:read", "user:update"],
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def admin_user(test_db):
    """Create an admin user."""
    async with test_db() as session:
        user = User(
            email="admin@example.com",
            password_hash=get_password_hash("AdminPassword123!"),
            full_name="Admin User",
            username="admin",
            email_verified=True,
            roles=["admin"],
            permissions=[
                "admin",
                "user:read",
                "user:create",
                "user:update",
                "user:delete",
            ],
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def authenticated_client(test_user):
    """Create authenticated test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login to get token
        login_data = {"email": "test@example.com", "password": "TestPassword123!"}
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200

        token_data = response.json()
        token = token_data["access_token"]

        # Set authorization header
        client.headers.update({"Authorization": f"Bearer {token}"})

        yield client


@pytest_asyncio.fixture
async def admin_client(admin_user):
    """Create authenticated admin client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login to get token
        login_data = {"email": "admin@example.com", "password": "AdminPassword123!"}
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200

        token_data = response.json()
        token = token_data["access_token"]

        # Set authorization header
        client.headers.update({"Authorization": f"Bearer {token}"})

        yield client


class TestHealthAndSecurity:
    """Test basic health checks and security headers."""

    @pytest_asyncio.async_test
    async def test_health_endpoint(self):
        """Test health endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "healthy"
            assert "version" in data
            assert "timestamp" in data

    @pytest_asyncio.async_test
    async def test_security_headers(self):
        """Test security headers are present."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health")

            # Check security headers
            assert response.headers["X-Content-Type-Options"] == "nosniff"
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["X-XSS-Protection"] == "1; mode=block"
            assert "Content-Security-Policy" in response.headers
            assert "Referrer-Policy" in response.headers

    @pytest_asyncio.async_test
    async def test_cors_headers(self):
        """Test CORS headers."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            headers = {"Origin": "http://localhost:3000"}
            response = await client.options("/health", headers=headers)

            assert "Access-Control-Allow-Origin" in response.headers


class TestAuthentication:
    """Test authentication flows with security validation."""

    @pytest_asyncio.async_test
    async def test_user_registration_success(self, test_db):
        """Test successful user registration."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            user_data = {
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "full_name": "New User",
                "username": "newuser",
            }

            response = await client.post("/api/v1/auth/register", json=user_data)
            assert response.status_code == 201

            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert data["user"]["email"] == user_data["email"]

    @pytest_asyncio.async_test
    async def test_password_strength_validation(self, test_db):
        """Test password strength requirements."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Weak password
            user_data = {
                "email": "weak@example.com",
                "password": "weak",
                "full_name": "Weak Password User",
            }

            response = await client.post("/api/v1/auth/register", json=user_data)
            assert response.status_code == 422

    @pytest_asyncio.async_test
    async def test_duplicate_email_prevention(self, test_user):
        """Test duplicate email prevention."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            user_data = {
                "email": "test@example.com",  # Same as test_user
                "password": "AnotherPassword123!",
                "full_name": "Duplicate User",
            }

            response = await client.post("/api/v1/auth/register", json=user_data)
            assert response.status_code == 409

    @pytest_asyncio.async_test
    async def test_login_success(self, test_user):
        """Test successful login."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            login_data = {"email": "test@example.com", "password": "TestPassword123!"}

            response = await client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 200

            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data

    @pytest_asyncio.async_test
    async def test_login_invalid_credentials(self, test_user):
        """Test login with invalid credentials."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            login_data = {"email": "test@example.com", "password": "WrongPassword"}

            response = await client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 401

    @pytest_asyncio.async_test
    async def test_token_refresh(self, test_user):
        """Test token refresh functionality."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Login first
            login_data = {"email": "test@example.com", "password": "TestPassword123!"}

            response = await client.post("/api/v1/auth/login", json=login_data)
            tokens = response.json()

            # Refresh token
            refresh_data = {"refresh_token": tokens["refresh_token"]}
            response = await client.post("/api/v1/auth/refresh", json=refresh_data)

            assert response.status_code == 200
            new_tokens = response.json()
            assert "access_token" in new_tokens
            assert new_tokens["access_token"] != tokens["access_token"]


class TestAuthorization:
    """Test RBAC and permission system."""

    @pytest_asyncio.async_test
    async def test_protected_endpoint_without_auth(self):
        """Test accessing protected endpoint without authentication."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/users/me")
            assert response.status_code == 401

    @pytest_asyncio.async_test
    async def test_user_profile_access(self, authenticated_client):
        """Test user can access their own profile."""
        response = await authenticated_client.get("/api/v1/users/me")
        assert response.status_code == 200

        data = response.json()
        assert data["email"] == "test@example.com"

    @pytest_asyncio.async_test
    async def test_admin_only_endpoint(self, authenticated_client, admin_client):
        """Test admin-only endpoint access."""
        # Regular user should be denied
        response = await authenticated_client.get("/api/v1/users/")
        assert response.status_code == 403

        # Admin should have access
        response = await admin_client.get("/api/v1/users/")
        assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest_asyncio.async_test
    async def test_rate_limiting(self):
        """Test rate limiting prevents abuse."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make many requests quickly
            responses = []
            for _ in range(70):  # Exceed default limit of 60/minute
                response = await client.get("/health")
                responses.append(response.status_code)

            # Should get some 429 responses
            assert 429 in responses


class TestInputValidation:
    """Test input validation and security."""

    @pytest_asyncio.async_test
    async def test_sql_injection_prevention(self, authenticated_client):
        """Test SQL injection prevention."""
        # Try SQL injection in search parameter
        malicious_query = "'; DROP TABLE users; --"
        response = await authenticated_client.get(
            f"/api/v1/users/?search={malicious_query}"
        )

        # Should not cause server error (should be handled gracefully)
        assert response.status_code in [200, 400, 422]

    @pytest_asyncio.async_test
    async def test_xss_prevention(self, authenticated_client):
        """Test XSS prevention in user input."""
        xss_payload = "<script>alert('xss')</script>"

        update_data = {"full_name": xss_payload, "bio": xss_payload}

        response = await authenticated_client.put("/api/v1/users/me", json=update_data)

        if response.status_code == 200:
            # If update succeeds, ensure XSS payload is sanitized in response
            data = response.json()
            assert "<script>" not in data.get("full_name", "")
            assert "<script>" not in data.get("bio", "")

    @pytest_asyncio.async_test
    async def test_large_request_rejection(self):
        """Test large request rejection."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create large payload (over 10MB)
            large_data = {
                "email": "large@example.com",
                "password": "Password123!",
                "full_name": "x" * (11 * 1024 * 1024),  # 11MB
            }

            response = await client.post("/api/v1/auth/register", json=large_data)
            assert response.status_code == 413  # Request Too Large


class TestSemanticSearch:
    """Test semantic search functionality and security."""

    @pytest_asyncio.async_test
    async def test_semantic_search_basic(self):
        """Test basic semantic search functionality."""
        from src.ai_inference.semantic_search import get_semantic_search

        search_engine = await get_semantic_search()

        # Test with a simple query
        results = await search_engine.search_context("authentication", "test_client")

        # Should return some results
        assert isinstance(results, list)
        # Results should have proper structure
        if results:
            result = results[0]
            assert hasattr(result, "file_path")
            assert hasattr(result, "content")
            assert hasattr(result, "similarity_score")
            assert hasattr(result, "is_safe")

    @pytest_asyncio.async_test
    async def test_semantic_search_security(self):
        """Test semantic search security controls."""
        from src.ai_inference.semantic_search import get_semantic_search

        search_engine = await get_semantic_search()

        # Test SQL injection prevention
        with pytest.raises(Exception):  # Should raise ValidationError
            await search_engine.search_context("SELECT * FROM users", "test_client")

        # Test path traversal prevention
        with pytest.raises(Exception):  # Should raise ValidationError
            await search_engine.search_context("../../../etc/passwd", "test_client")

    @pytest_asyncio.async_test
    async def test_rate_limiting_semantic_search(self):
        """Test rate limiting for semantic search."""
        from src.ai_inference.semantic_search import get_semantic_search

        search_engine = await get_semantic_search()

        # Make many requests quickly
        client_id = "test_rate_limit"
        successful_searches = 0

        for i in range(15):  # Try to exceed rate limit
            try:
                await search_engine.search_context(f"test query {i}", client_id)
                successful_searches += 1
            except Exception:
                break

        # Should hit rate limit before completing all searches
        assert successful_searches < 15


if __name__ == "__main__":
    # Run specific test
    pytest.main([__file__, "-v"])
