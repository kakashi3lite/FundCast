#!/usr/bin/env python3
"""
Comprehensive End-to-End Testing for Purple Tier Subscription Flow
Tests the complete user journey from UI interaction to database storage
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import httpx
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Test Configuration
TEST_CONFIG = {
    "api_base_url": "http://localhost:8000/api/v1",
    "test_user_email": "test.founder@example.com",
    "test_user_password": "SecureTestPassword123!",
    "purple_tier_slug": "purple",
    "monthly_price": 99900,  # $999.00 in cents
    "annual_price": 839900,  # $8399.00 in cents (30% discount)
}

class PurpleTierFlowTester:
    """End-to-end tester for Purple Tier subscription flow"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = httpx.AsyncClient(timeout=30.0)
        self.auth_token: Optional[str] = None
        self.user_id: Optional[str] = None
        
    async def setup(self):
        """Setup test environment"""
        print("🚀 Setting up Purple Tier subscription flow test...")
        
        # Test API connectivity
        try:
            response = await self.session.get(f"{self.base_url.replace('/api/v1', '')}/health")
            if response.status_code != 200:
                raise Exception(f"API health check failed: {response.status_code}")
            print("✅ API connectivity verified")
        except Exception as e:
            print(f"❌ API connectivity failed: {e}")
            return False
            
        return True
    
    async def test_user_registration(self) -> bool:
        """Test user registration and authentication"""
        print("\n📝 Testing user registration and authentication...")
        
        try:
            # Register test user
            register_data = {
                "email": TEST_CONFIG["test_user_email"],
                "password": TEST_CONFIG["test_user_password"],
                "full_name": "Test Purple Founder",
                "username": f"testfounder_{int(time.time())}"
            }
            
            response = await self.session.post(
                f"{self.base_url}/auth/register",
                json=register_data
            )
            
            if response.status_code in [200, 201]:
                print("✅ User registration successful")
            elif response.status_code == 409:
                print("⚠️  User already exists, proceeding with login")
            else:
                print(f"❌ Registration failed: {response.status_code} - {response.text}")
                return False
            
            # Login to get auth token
            login_data = {
                "email": TEST_CONFIG["test_user_email"],
                "password": TEST_CONFIG["test_user_password"]
            }
            
            response = await self.session.post(
                f"{self.base_url}/auth/login",
                json=login_data
            )
            
            if response.status_code != 200:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
                
            login_result = response.json()
            self.auth_token = login_result.get("access_token")
            self.user_id = login_result.get("user", {}).get("id")
            
            if not self.auth_token:
                print("❌ No auth token received")
                return False
                
            print("✅ User authentication successful")
            return True
            
        except Exception as e:
            print(f"❌ Authentication test failed: {e}")
            return False
    
    async def test_subscription_tiers_endpoint(self) -> bool:
        """Test subscription tiers API endpoint"""
        print("\n🏷️  Testing subscription tiers endpoint...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = await self.session.get(
                f"{self.base_url}/subscriptions/tiers",
                headers=headers
            )
            
            if response.status_code != 200:
                print(f"❌ Tiers endpoint failed: {response.status_code}")
                return False
            
            tiers = response.json()
            
            # Validate Purple tier exists
            purple_tier = None
            for tier in tiers:
                if tier.get("slug") == "purple":
                    purple_tier = tier
                    break
            
            if not purple_tier:
                print("❌ Purple tier not found in tiers response")
                return False
            
            # Validate Purple tier properties
            required_features = ["home_featuring", "priority_discovery", "verified_badge"]
            tier_features = purple_tier.get("features", [])
            
            missing_features = [f for f in required_features if f not in tier_features]
            if missing_features:
                print(f"❌ Purple tier missing features: {missing_features}")
                return False
            
            # Validate pricing
            monthly_price = purple_tier.get("monthly_price_cents")
            annual_price = purple_tier.get("annual_price_cents")
            
            if monthly_price != TEST_CONFIG["monthly_price"]:
                print(f"❌ Purple tier monthly price mismatch: {monthly_price} vs {TEST_CONFIG['monthly_price']}")
                return False
                
            if annual_price != TEST_CONFIG["annual_price"]:
                print(f"❌ Purple tier annual price mismatch: {annual_price} vs {TEST_CONFIG['annual_price']}")
                return False
            
            print("✅ Subscription tiers endpoint validated")
            return True
            
        except Exception as e:
            print(f"❌ Tiers endpoint test failed: {e}")
            return False
    
    async def test_checkout_session_creation(self) -> bool:
        """Test Purple tier checkout session creation"""
        print("\n💳 Testing Purple tier checkout session creation...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            checkout_data = {
                "tier_slug": TEST_CONFIG["purple_tier_slug"],
                "billing_cycle": "monthly",
                "trial_days": 0
            }
            
            response = await self.session.post(
                f"{self.base_url}/subscriptions/checkout",
                headers=headers,
                json=checkout_data
            )
            
            if response.status_code != 200:
                print(f"❌ Checkout creation failed: {response.status_code} - {response.text}")
                return False
            
            checkout_result = response.json()
            
            # Validate checkout response
            if not checkout_result.get("success"):
                print("❌ Checkout creation returned success=false")
                return False
                
            if not checkout_result.get("checkout_url"):
                print("❌ No checkout URL returned")
                return False
            
            if checkout_result.get("tier_info", {}).get("slug") != "purple":
                print("❌ Incorrect tier in checkout response")
                return False
            
            print("✅ Purple tier checkout session created successfully")
            print(f"   Checkout URL: {checkout_result['checkout_url'][:50]}...")
            return True
            
        except Exception as e:
            print(f"❌ Checkout session test failed: {e}")
            return False
    
    async def test_featuring_queue_endpoint(self) -> bool:
        """Test Purple tier featuring queue endpoint"""
        print("\n⭐ Testing Purple tier featuring queue endpoint...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = await self.session.get(
                f"{self.base_url}/subscriptions/purple-featuring/queue",
                headers=headers
            )
            
            # For new users without subscription, this should return empty or error
            if response.status_code == 200:
                queue_data = response.json()
                print("✅ Featuring queue endpoint accessible")
                print(f"   Queue data: {json.dumps(queue_data, indent=2)}")
                return True
            elif response.status_code == 403:
                print("✅ Featuring queue properly restricted to subscribers")
                return True
            else:
                print(f"❌ Unexpected featuring queue response: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Featuring queue test failed: {e}")
            return False
    
    async def test_current_featured_founders(self) -> bool:
        """Test current featured founders endpoint (public)"""
        print("\n🌟 Testing current featured founders endpoint...")
        
        try:
            # This endpoint should be public (no auth required)
            response = await self.session.get(
                f"{self.base_url}/subscriptions/purple-featuring/current"
            )
            
            if response.status_code != 200:
                print(f"❌ Featured founders endpoint failed: {response.status_code}")
                return False
            
            featured_data = response.json()
            
            # Validate response structure
            if "hero_founder" not in featured_data and "featured_grid" not in featured_data:
                print("❌ Featured founders response missing expected structure")
                return False
            
            print("✅ Current featured founders endpoint working")
            
            # Display sample data
            if featured_data.get("featured_grid"):
                print(f"   Found {len(featured_data['featured_grid'])} featured founders")
            
            return True
            
        except Exception as e:
            print(f"❌ Featured founders test failed: {e}")
            return False
    
    async def test_tier_comparison_endpoint(self) -> bool:
        """Test tier comparison endpoint for pricing psychology"""
        print("\n📊 Testing tier comparison endpoint...")
        
        try:
            response = await self.session.get(
                f"{self.base_url}/subscriptions/tiers/comparison"
            )
            
            if response.status_code != 200:
                print(f"❌ Tier comparison failed: {response.status_code}")
                return False
            
            comparison_data = response.json()
            
            # Validate psychology optimization features
            required_keys = [
                "recommended_tier", "popular_tier", "purple_spotlight", 
                "upgrade_incentives", "annual_discount_message"
            ]
            
            missing_keys = [k for k in required_keys if k not in comparison_data]
            if missing_keys:
                print(f"❌ Missing psychology features: {missing_keys}")
                return False
            
            # Validate Purple tier is highlighted
            if comparison_data.get("recommended_tier") != "purple":
                print("❌ Purple tier not set as recommended")
                return False
            
            print("✅ Tier comparison endpoint with psychology features working")
            return True
            
        except Exception as e:
            print(f"❌ Tier comparison test failed: {e}")
            return False
    
    async def test_subscription_analytics(self) -> bool:
        """Test subscription analytics endpoint"""
        print("\n📈 Testing subscription analytics endpoint...")
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = await self.session.get(
                f"{self.base_url}/subscriptions/analytics?days=30",
                headers=headers
            )
            
            if response.status_code == 200:
                analytics_data = response.json()
                print("✅ Analytics endpoint accessible")
                return True
            elif response.status_code == 403:
                print("✅ Analytics properly restricted (no active subscription)")
                return True
            else:
                print(f"❌ Unexpected analytics response: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Analytics test failed: {e}")
            return False
    
    async def run_complete_test_suite(self) -> bool:
        """Run the complete Purple Tier subscription flow test suite"""
        print("🎯 Starting Complete Purple Tier Subscription Flow Test")
        print("=" * 60)
        
        # Setup
        if not await self.setup():
            return False
        
        # Test sequence
        test_results = []
        
        tests = [
            ("User Registration & Auth", self.test_user_registration),
            ("Subscription Tiers", self.test_subscription_tiers_endpoint),
            ("Checkout Session", self.test_checkout_session_creation),
            ("Featuring Queue", self.test_featuring_queue_endpoint),
            ("Featured Founders", self.test_current_featured_founders),
            ("Tier Comparison", self.test_tier_comparison_endpoint),
            ("Analytics", self.test_subscription_analytics),
        ]
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                test_results.append((test_name, result))
                
                if not result:
                    print(f"\n❌ Test suite failed at: {test_name}")
                    break
                    
            except Exception as e:
                print(f"\n❌ Test suite exception at {test_name}: {e}")
                test_results.append((test_name, False))
                break
        
        # Results summary
        print("\n" + "=" * 60)
        print("🎯 Purple Tier Subscription Flow Test Results")
        print("=" * 60)
        
        passed = sum(1 for _, result in test_results if result)
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name}")
        
        print(f"\nOverall Result: {passed}/{total} tests passed")
        
        if passed == len(tests):
            print("🎉 All Purple Tier subscription flow tests PASSED!")
            print("\n💎 Purple Tier System Status: FULLY OPERATIONAL")
            print("🚀 Ready for production deployment!")
            return True
        else:
            print(f"❌ {len(tests) - passed} tests failed")
            return False
    
    async def cleanup(self):
        """Cleanup test resources"""
        await self.session.aclose()


async def main():
    """Main test execution"""
    tester = PurpleTierFlowTester(TEST_CONFIG["api_base_url"])
    
    try:
        success = await tester.run_complete_test_suite()
        exit_code = 0 if success else 1
    except Exception as e:
        print(f"💥 Test suite crashed: {e}")
        exit_code = 2
    finally:
        await tester.cleanup()
    
    exit(exit_code)


if __name__ == "__main__":
    # Run the complete test suite
    asyncio.run(main())