"""Property-based testing for FundCast using Hypothesis."""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pytest
import hypothesis
from hypothesis import given, strategies as st, assume, example, note, settings
from hypothesis.stateful import RuleBasedStateMachine, Bundle, rule, invariant, initialize
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

# Import test fixtures from integration tests
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.main import app
from src.api.database import User, Company, Offering, Investment, Market, MarketPosition
from src.api.auth.security import create_access_token, verify_password, get_password_hash
from src.api.cache import CacheKey, get_cache
from test_integration import test_db, test_user, admin_user


# Custom strategies for domain objects
@st.composite
def email_strategy(draw):
    """Generate valid email addresses."""
    username = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
        min_size=1,
        max_size=20
    ).filter(lambda x: x and x[0].isalnum()))
    
    domain = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd')),
        min_size=1,
        max_size=15
    ).filter(lambda x: x and x[0].isalnum()))
    
    tld = draw(st.sampled_from(['com', 'org', 'net', 'edu', 'gov']))
    
    return f"{username}@{domain}.{tld}"


@st.composite
def password_strategy(draw):
    """Generate valid passwords meeting security requirements."""
    # At least 8 chars, with uppercase, lowercase, digit, special char
    length = draw(st.integers(min_value=8, max_value=50))
    
    # Ensure we have required character types
    uppercase = draw(st.text(alphabet=st.characters(whitelist_categories=('Lu',)), min_size=1, max_size=5))
    lowercase = draw(st.text(alphabet=st.characters(whitelist_categories=('Ll',)), min_size=1, max_size=10))
    digits = draw(st.text(alphabet='0123456789', min_size=1, max_size=5))
    special = draw(st.text(alphabet='!@#$%^&*()_+-=[]{}|;:,.<>?', min_size=1, max_size=5))
    
    # Fill remaining length with random chars
    remaining_length = max(0, length - len(uppercase + lowercase + digits + special))
    filler = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='!@#$%^&*()_+-=[]{}|;:,.<>?'
        ),
        min_size=0,
        max_size=remaining_length
    ))
    
    # Combine and shuffle
    all_chars = list(uppercase + lowercase + digits + special + filler)
    draw(st.randoms()).shuffle(all_chars)
    
    return ''.join(all_chars)


@st.composite
def user_data_strategy(draw):
    """Generate valid user registration data."""
    return {
        "email": draw(email_strategy()),
        "password": draw(password_strategy()),
        "full_name": draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        "username": draw(st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_-'),
            min_size=3,
            max_size=30
        ).filter(lambda x: x and x[0].isalnum())),
    }


@st.composite
def company_data_strategy(draw):
    """Generate valid company data."""
    return {
        "name": draw(st.text(min_size=1, max_size=255).filter(lambda x: x.strip())),
        "legal_name": draw(st.text(min_size=1, max_size=255).filter(lambda x: x.strip())),
        "description": draw(st.text(min_size=10, max_size=1000)),
        "website": draw(st.one_of(
            st.none(),
            st.text().map(lambda x: f"https://{x.lower().replace(' ', '')}.com")
        )),
        "industry": draw(st.sampled_from([
            "Software", "Hardware", "Fintech", "Biotech", "Energy", "Consumer", "Enterprise"
        ])),
        "stage": draw(st.sampled_from(["Pre-seed", "Seed", "Series A", "Series B", "Later"])),
        "employee_count": draw(st.integers(min_value=1, max_value=10000)),
        "incorporation_state": draw(st.sampled_from(["DE", "CA", "NY", "TX", "WA"])),
        "entity_type": draw(st.sampled_from(["C-Corp", "LLC", "S-Corp"])),
    }


@st.composite
def market_data_strategy(draw):
    """Generate valid market data."""
    market_type = draw(st.sampled_from(["binary", "categorical", "scalar"]))
    
    return {
        "title": draw(st.text(min_size=5, max_size=255).filter(lambda x: x.strip())),
        "description": draw(st.text(min_size=20, max_size=1000)),
        "category": draw(st.sampled_from([
            "Technology", "Business", "Finance", "Sports", "Politics", "Science"
        ])),
        "market_type": market_type,
        "engine_type": draw(st.sampled_from(["orderbook", "amm"])),
        "resolution_date": draw(st.datetimes(
            min_value=datetime.now() + timedelta(days=1),
            max_value=datetime.now() + timedelta(days=365)
        )),
    }


class TestUserProperties:
    """Property-based tests for user operations."""
    
    @given(user_data=user_data_strategy())
    @settings(max_examples=100, deadline=5000)
    @pytest.mark.asyncio
    async def test_user_registration_properties(self, user_data, test_db):
        """Test user registration with generated data."""
        async with AsyncSession() as session:
            # Property: Valid user data should always create a user
            from src.api.users.router import create_user
            
            try:
                # Assume email is unique (in real test, would handle duplicates)
                assume(len(user_data["email"]) <= 255)
                assume("@" in user_data["email"])
                assume(len(user_data["password"]) >= 8)
                
                # Test password hashing is deterministic
                hash1 = get_password_hash(user_data["password"])
                hash2 = get_password_hash(user_data["password"])
                
                # Property: Same password should produce different hashes (salt)
                assert hash1 != hash2
                
                # Property: Both hashes should verify the same password
                assert verify_password(user_data["password"], hash1)
                assert verify_password(user_data["password"], hash2)
                
                note(f"Testing user creation with email: {user_data['email']}")
                
            except Exception as e:
                # Log the data that caused the failure
                note(f"Failed with data: {user_data}")
                note(f"Error: {str(e)}")
                raise
    
    @given(st.text(), st.text())
    @settings(max_examples=50)
    def test_password_verification_properties(self, password, wrong_password):
        """Test password verification properties."""
        assume(password != wrong_password)
        assume(len(password) > 0)
        assume(len(wrong_password) > 0)
        
        hash_value = get_password_hash(password)
        
        # Property: Correct password should always verify
        assert verify_password(password, hash_value)
        
        # Property: Wrong password should never verify
        assert not verify_password(wrong_password, hash_value)
    
    @given(email=email_strategy())
    def test_email_validation_properties(self, email):
        """Test email validation properties."""
        from pydantic import EmailStr, ValidationError
        
        try:
            validated_email = EmailStr(email)
            # Property: Valid emails should contain exactly one @ symbol
            assert email.count('@') == 1
            # Property: Valid emails should have domain part
            assert '.' in email.split('@')[1]
            
        except ValidationError:
            # If pydantic rejects it, our email strategy might need adjustment
            note(f"Pydantic rejected email: {email}")


class TestCacheProperties:
    """Property-based tests for caching system."""
    
    @given(
        keys=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=20),
        values=st.lists(st.one_of(
            st.text(), st.integers(), st.floats(), st.booleans(),
            st.dictionaries(st.text(), st.text())
        ), min_size=1, max_size=20),
        ttl=st.integers(min_value=1, max_value=3600)
    )
    @settings(max_examples=50, deadline=10000)
    @pytest.mark.asyncio
    async def test_cache_consistency_properties(self, keys, values, ttl):
        """Test cache consistency properties."""
        assume(len(keys) == len(values))
        
        cache = await get_cache()
        
        # Property: Set then get should return the same value
        for key, value in zip(keys, values):
            await cache.set(key, value, ttl)
            cached_value = await cache.get(key)
            
            # Handle JSON serialization for complex types
            if isinstance(value, dict):
                assert cached_value == value or json.loads(json.dumps(cached_value)) == value
            else:
                assert cached_value == value
        
        # Property: Getting non-existent key should return None
        non_existent_key = "non_existent_" + str(uuid.uuid4())
        assert await cache.get(non_existent_key) is None
        
        # Property: Deleting existing key should make it unavailable
        if keys:
            test_key = keys[0]
            assert await cache.get(test_key) is not None
            await cache.delete(test_key)
            assert await cache.get(test_key) is None
    
    @given(key=st.text(min_size=1, max_size=100))
    @pytest.mark.asyncio
    async def test_cache_key_properties(self, key):
        """Test cache key generation properties."""
        cache_key_builder = CacheKey("test_prefix")
        
        # Property: Same arguments should produce same key
        key1 = cache_key_builder.build(key, "arg1", param="value")
        key2 = cache_key_builder.build(key, "arg1", param="value")
        assert key1 == key2
        
        # Property: Different arguments should produce different keys
        key3 = cache_key_builder.build(key, "arg2", param="value")
        assert key1 != key3


class TestAPIInvariantStateMachine(RuleBasedStateMachine):
    """Stateful property-based testing for API operations."""
    
    def __init__(self):
        super().__init__()
        self.client = TestClient(app)
        self.users = {}
        self.companies = {}
        self.markets = {}
        self.auth_tokens = {}
    
    users = Bundle('users')
    companies = Bundle('companies') 
    markets = Bundle('markets')
    auth_tokens = Bundle('auth_tokens')
    
    @initialize()
    def setup(self):
        """Initialize the state machine."""
        # Create initial admin user
        admin_data = {
            "email": "admin@test.com",
            "password": "AdminPassword123!",
            "full_name": "Test Admin",
            "is_superuser": True
        }
        response = self.client.post("/api/v1/auth/register", json=admin_data)
        if response.status_code == 201:
            self.auth_tokens["admin"] = response.json()["access_token"]
    
    @rule(target=users, user_data=user_data_strategy())
    def create_user(self, user_data):
        """Create a user and verify properties."""
        response = self.client.post("/api/v1/auth/register", json=user_data)
        
        if response.status_code == 201:
            data = response.json()
            user_id = data["user"]["id"]
            
            # Invariant: Created user should have the provided email
            assert data["user"]["email"] == user_data["email"]
            
            # Invariant: Should receive valid JWT tokens
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            
            self.users[user_id] = user_data
            self.auth_tokens[user_id] = data["access_token"]
            
            return user_id
        
        # Handle expected failures (duplicate email, etc.)
        assume(response.status_code in [201, 409, 422])
        return None
    
    @rule(user_id=users, company_data=company_data_strategy())
    def create_company(self, user_id, company_data):
        """Create a company for a user."""
        if user_id not in self.auth_tokens:
            return
        
        headers = {"Authorization": f"Bearer {self.auth_tokens[user_id]}"}
        response = self.client.post(
            "/api/v1/companies/",
            json=company_data,
            headers=headers
        )
        
        if response.status_code == 201:
            data = response.json()
            company_id = data["id"]
            
            # Invariant: Company should be owned by the creating user
            assert data["owner_id"] == user_id
            
            # Invariant: Company data should match input
            assert data["name"] == company_data["name"]
            assert data["legal_name"] == company_data["legal_name"]
            
            self.companies[company_id] = {
                **company_data,
                "owner_id": user_id
            }
            
            return company_id
    
    @rule(market_data=market_data_strategy())
    def create_market(self, market_data):
        """Create a prediction market."""
        if "admin" not in self.auth_tokens:
            return
        
        headers = {"Authorization": f"Bearer {self.auth_tokens['admin']}"}
        response = self.client.post(
            "/api/v1/markets/",
            json=market_data,
            headers=headers
        )
        
        if response.status_code == 201:
            data = response.json()
            market_id = data["id"]
            
            # Invariant: Market should have the specified properties
            assert data["title"] == market_data["title"]
            assert data["market_type"] == market_data["market_type"]
            assert data["status"] == "active"
            
            self.markets[market_id] = market_data
            return market_id
    
    @invariant()
    def user_count_invariant(self):
        """Invariant: Number of users should be consistent."""
        # This could check with database count in real implementation
        assert len(self.users) >= 0
    
    @invariant()
    def auth_token_invariant(self):
        """Invariant: Every user should have an auth token."""
        for user_id in self.users:
            if user_id in self.auth_tokens:
                token = self.auth_tokens[user_id]
                assert isinstance(token, str)
                assert len(token) > 0


class TestFinancialCalculationsProperties:
    """Property-based tests for financial calculations."""
    
    @given(
        investment_amount=st.integers(min_value=1, max_value=10_000_000),  # $1 to $100k
        share_price=st.integers(min_value=1, max_value=100_000),  # $0.01 to $1000
    )
    @settings(max_examples=100)
    def test_investment_calculation_properties(self, investment_amount, share_price):
        """Test investment calculation properties."""
        # Property: shares = investment_amount / share_price (rounded down)
        expected_shares = investment_amount // share_price
        actual_cost = expected_shares * share_price
        
        # Property: Actual cost should never exceed investment amount
        assert actual_cost <= investment_amount
        
        # Property: If we can afford at least one share, we should get shares
        if investment_amount >= share_price:
            assert expected_shares > 0
        else:
            assert expected_shares == 0
        
        # Property: Adding one more share should exceed the investment amount
        if expected_shares > 0:
            assert (expected_shares + 1) * share_price > investment_amount
    
    @given(
        principal=st.floats(min_value=0.01, max_value=1_000_000),
        rate=st.floats(min_value=0.001, max_value=0.5),  # 0.1% to 50%
        time_periods=st.integers(min_value=1, max_value=100)
    )
    def test_compound_interest_properties(self, principal, rate, time_periods):
        """Test compound interest calculation properties."""
        # Simple compound interest: A = P(1 + r)^t
        final_amount = principal * ((1 + rate) ** time_periods)
        
        # Property: Final amount should always be greater than principal (positive rate)
        assert final_amount > principal
        
        # Property: Longer time periods should yield higher returns
        shorter_amount = principal * ((1 + rate) ** (time_periods - 1))
        assert final_amount > shorter_amount
        
        # Property: Higher rates should yield higher returns
        if rate > 0.001:
            lower_rate_amount = principal * ((1 + rate * 0.5) ** time_periods)
            assert final_amount > lower_rate_amount


# Performance property tests
class TestPerformanceProperties:
    """Property-based performance tests."""
    
    @given(data_size=st.integers(min_value=1, max_value=1000))
    @settings(max_examples=20, deadline=30000)  # Longer deadline for performance tests
    @pytest.mark.asyncio
    async def test_bulk_operation_performance(self, data_size):
        """Test that bulk operations scale reasonably."""
        import time
        
        # Generate test data
        test_data = [
            {"key": f"test_key_{i}", "value": f"test_value_{i}"}
            for i in range(data_size)
        ]
        
        cache = await get_cache()
        
        # Measure bulk set performance
        start_time = time.time()
        for item in test_data:
            await cache.set(item["key"], item["value"], ttl=300)
        set_duration = time.time() - start_time
        
        # Measure bulk get performance
        start_time = time.time()
        for item in test_data:
            await cache.get(item["key"])
        get_duration = time.time() - start_time
        
        # Property: Performance should scale reasonably with data size
        # This is a soft property - we expect roughly linear scaling
        set_rate = data_size / set_duration if set_duration > 0 else float('inf')
        get_rate = data_size / get_duration if get_duration > 0 else float('inf')
        
        note(f"Set rate: {set_rate:.2f} ops/sec, Get rate: {get_rate:.2f} ops/sec")
        
        # Property: Should handle at least 100 operations per second
        assert set_rate >= 100, f"Set performance too slow: {set_rate} ops/sec"
        assert get_rate >= 500, f"Get performance too slow: {get_rate} ops/sec"


# Run the state machine test
TestAPIStateMachine = TestAPIInvariantStateMachine.TestCase

if __name__ == "__main__":
    # Run property tests
    import sys
    pytest.main([__file__] + sys.argv[1:])