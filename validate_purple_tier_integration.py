#!/usr/bin/env python3
"""
Purple Tier Integration Validation Script
Validates that all components are properly integrated and configured
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

class PurpleTierValidator:
    """Validates Purple Tier integration completeness"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def error(self, message: str):
        """Add error message"""
        self.errors.append(f"❌ {message}")
        
    def warning(self, message: str):
        """Add warning message"""
        self.warnings.append(f"⚠️  {message}")
        
    def success(self, message: str):
        """Print success message"""
        print(f"✅ {message}")
    
    def validate_backend_integration(self) -> bool:
        """Validate backend API integration"""
        print("\n🔧 Validating Backend API Integration...")
        
        # Check if subscription models exist
        models_path = self.project_root / "src" / "api" / "subscriptions" / "models.py"
        if not models_path.exists():
            self.error("Subscription models file not found")
            return False
        self.success("Subscription models file exists")
        
        # Check router integration in main.py
        main_path = self.project_root / "src" / "api" / "main.py"
        if main_path.exists():
            with open(main_path, 'r') as f:
                main_content = f.read()
                if "subscriptions_router" in main_content:
                    self.success("Subscription router integrated in main.py")
                else:
                    self.error("Subscription router not integrated in main.py")
                    return False
        else:
            self.error("main.py not found")
            return False
        
        # Check database integration
        db_path = self.project_root / "src" / "api" / "database.py"
        if db_path.exists():
            with open(db_path, 'r') as f:
                db_content = f.read()
                if "from .subscriptions.models import" in db_content:
                    self.success("Subscription models imported in database.py")
                else:
                    self.error("Subscription models not imported in database.py")
                    return False
        
        # Validate key subscription files
        subscription_files = [
            "src/api/subscriptions/__init__.py",
            "src/api/subscriptions/router.py", 
            "src/api/subscriptions/service.py",
            "src/api/subscriptions/lemonsqueezy.py",
            "src/api/subscriptions/featuring.py"
        ]
        
        for file_path in subscription_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                self.success(f"{file_path} exists")
            else:
                self.error(f"Missing file: {file_path}")
                return False
        
        return True
    
    def validate_frontend_integration(self) -> bool:
        """Validate frontend UI integration"""
        print("\n🎨 Validating Frontend UI Integration...")
        
        # Check main UI components
        ui_components = [
            "src/ui/App.tsx",
            "src/ui/components/PurpleTierPricing.tsx",
            "src/ui/components/FeaturedFounders.tsx",
            "src/ui/pages/HomePage.tsx",
            "src/ui/pages/PricingPage.tsx"
        ]
        
        for component_path in ui_components:
            full_path = self.project_root / component_path
            if full_path.exists():
                self.success(f"{component_path} exists")
            else:
                self.error(f"Missing UI component: {component_path}")
                return False
        
        # Check UI index exports
        ui_index = self.project_root / "src" / "ui" / "index.ts"
        if ui_index.exists():
            with open(ui_index, 'r') as f:
                index_content = f.read()
                required_exports = [
                    "PurpleTierPricing",
                    "FeaturedFounders", 
                    "HomePage",
                    "PricingPage",
                    "App"
                ]
                
                for export in required_exports:
                    if export in index_content:
                        self.success(f"{export} properly exported")
                    else:
                        self.error(f"{export} not exported in index.ts")
        else:
            self.error("UI index.ts not found")
            return False
        
        # Check Scene System integration
        scene_system_files = [
            "src/ui/lib/scene-system.ts",
            "src/ui/lib/scene-provider.tsx",
            "src/ui/lib/gambling-psychology.tsx"
        ]
        
        for file_path in scene_system_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                self.success(f"Scene System: {file_path} exists")
            else:
                self.warning(f"Scene System file missing: {file_path}")
        
        return True
    
    def validate_database_schema(self) -> bool:
        """Validate subscription database schema"""
        print("\n🗄️  Validating Database Schema...")
        
        models_path = self.project_root / "src" / "api" / "subscriptions" / "models.py"
        if not models_path.exists():
            self.error("Cannot validate schema - models.py missing")
            return False
        
        with open(models_path, 'r') as f:
            models_content = f.read()
        
        # Check required model classes
        required_models = [
            "SubscriptionTier",
            "UserSubscription", 
            "PurpleFeaturingSchedule",
            "FeaturingImpression"
        ]
        
        for model in required_models:
            if f"class {model}" in models_content:
                self.success(f"Database model {model} defined")
            else:
                self.error(f"Missing database model: {model}")
                return False
        
        # Check key fields for Purple tier functionality
        key_fields = [
            "home_featuring_enabled",
            "featuring_weight",
            "last_featured_at",
            "tier_slug",
            "monthly_price_cents",
            "annual_price_cents"
        ]
        
        missing_fields = []
        for field in key_fields:
            if field not in models_content:
                missing_fields.append(field)
        
        if missing_fields:
            self.warning(f"Potentially missing fields: {', '.join(missing_fields)}")
        else:
            self.success("All key Purple tier fields present")
        
        return True
    
    def validate_api_endpoints(self) -> bool:
        """Validate API endpoint completeness"""
        print("\n🌐 Validating API Endpoints...")
        
        router_path = self.project_root / "src" / "api" / "subscriptions" / "router.py"
        if not router_path.exists():
            self.error("Subscription router not found")
            return False
        
        with open(router_path, 'r') as f:
            router_content = f.read()
        
        # Check required endpoints
        required_endpoints = [
            "/subscriptions/tiers",
            "/subscriptions/checkout", 
            "/subscriptions/my-subscription",
            "/subscriptions/upgrade",
            "/subscriptions/purple-featuring/current",
            "/subscriptions/purple-featuring/queue",
            "/subscriptions/webhooks/lemonsqueezy"
        ]
        
        for endpoint in required_endpoints:
            # Check for the endpoint path in router definitions
            if endpoint.split('/')[-1] in router_content or endpoint in router_content:
                self.success(f"API endpoint {endpoint} defined")
            else:
                self.error(f"Missing API endpoint: {endpoint}")
                return False
        
        # Check for authentication dependencies
        if "get_current_user" in router_content:
            self.success("Authentication integration present")
        else:
            self.error("Authentication integration missing")
            return False
        
        return True
    
    def validate_payment_integration(self) -> bool:
        """Validate LemonSqueezy payment integration"""
        print("\n💳 Validating Payment Integration...")
        
        lemon_path = self.project_root / "src" / "api" / "subscriptions" / "lemonsqueezy.py"
        if not lemon_path.exists():
            self.error("LemonSqueezy integration file missing")
            return False
        
        with open(lemon_path, 'r') as f:
            lemon_content = f.read()
        
        # Check for key LemonSqueezy methods
        required_methods = [
            "create_checkout",
            "verify_webhook_signature",
            "handle_webhook",
            "update_subscription",
            "cancel_subscription"
        ]
        
        for method in required_methods:
            if method in lemon_content:
                self.success(f"LemonSqueezy method {method} implemented")
            else:
                self.error(f"Missing LemonSqueezy method: {method}")
                return False
        
        # Check webhook event handling
        if "subscription_created" in lemon_content and "subscription_updated" in lemon_content:
            self.success("Webhook event handling implemented")
        else:
            self.warning("Webhook event handling may be incomplete")
        
        return True
    
    def validate_psychology_features(self) -> bool:
        """Validate gambling psychology and growth features"""
        print("\n🎲 Validating Psychology & Growth Features...")
        
        # Check gambling psychology implementation
        gambling_path = self.project_root / "src" / "ui" / "lib" / "gambling-psychology.tsx"
        if gambling_path.exists():
            with open(gambling_path, 'r') as f:
                gambling_content = f.read()
            
            psychology_features = [
                "DopamineEngine",
                "NearMissEffect",
                "ProgressiveReward",
                "StreakSystem",
                "SocialValidation"
            ]
            
            for feature in psychology_features:
                if feature in gambling_content:
                    self.success(f"Psychology feature {feature} implemented")
                else:
                    self.warning(f"Psychology feature {feature} missing")
        else:
            self.warning("Gambling psychology module missing")
        
        # Check viral growth implementation  
        viral_path = self.project_root / "src" / "ui" / "lib" / "viral-growth.tsx"
        if viral_path.exists():
            self.success("Viral growth module exists")
        else:
            self.warning("Viral growth module missing")
        
        return True
    
    def validate_configuration(self) -> bool:
        """Validate system configuration"""
        print("\n⚙️  Validating Configuration...")
        
        # Check if strategy document exists
        strategy_path = self.project_root / "PURPLE_TIER_STRATEGY.md"
        if strategy_path.exists():
            self.success("Purple Tier strategy document exists")
        else:
            self.warning("Purple Tier strategy document missing")
        
        # Check environment configuration hints
        config_path = self.project_root / "src" / "api" / "config.py"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            if "LEMONSQUEEZY" in config_content or "PAYMENT" in config_content:
                self.success("Payment configuration present")
            else:
                self.warning("Payment configuration may need setup")
        
        return True
    
    def run_validation(self) -> bool:
        """Run complete validation suite"""
        print("🎯 Purple Tier Integration Validation")
        print("=" * 50)
        
        validations = [
            ("Backend Integration", self.validate_backend_integration),
            ("Frontend Integration", self.validate_frontend_integration), 
            ("Database Schema", self.validate_database_schema),
            ("API Endpoints", self.validate_api_endpoints),
            ("Payment Integration", self.validate_payment_integration),
            ("Psychology Features", self.validate_psychology_features),
            ("Configuration", self.validate_configuration)
        ]
        
        all_passed = True
        
        for name, validator in validations:
            try:
                if not validator():
                    all_passed = False
            except Exception as e:
                self.error(f"Validation {name} crashed: {e}")
                all_passed = False
        
        # Print summary
        print("\n" + "=" * 50)
        print("🎯 Validation Summary")
        print("=" * 50)
        
        if self.errors:
            print("❌ ERRORS:")
            for error in self.errors:
                print(f"  {error}")
                
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        print(f"\nValidation Result: {len(self.errors)} errors, {len(self.warnings)} warnings")
        
        if all_passed and not self.errors:
            print("\n🎉 Purple Tier Integration VALIDATED!")
            print("💎 System ready for testing and deployment")
            return True
        else:
            print("\n❌ Purple Tier Integration has issues")
            print("🔧 Please resolve errors before proceeding")
            return False


def main():
    """Main validation execution"""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.getcwd()
    
    validator = PurpleTierValidator(project_root)
    success = validator.run_validation()
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()