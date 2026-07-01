"""Compliance routes for SEC regulations and KYC/AML."""

import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import Company, Offering, User, get_database
from ..exceptions import (
    AuthorizationError,
    ComplianceError,
    ExternalServiceError,
    ResourceNotFoundError,
    ValidationError,
)
from ..users.dependencies import get_current_user, require_permissions

logger = structlog.get_logger(__name__)
router = APIRouter()


# Request/Response Models
class KYCRequest(BaseModel):
    """KYC verification request."""

    provider: str = Field(..., regex="^(stripe|persona|jumio)$")
    redirect_url: Optional[str] = Field(None, max_length=500)

    @validator("redirect_url")
    def validate_redirect_url(cls, v):
        if v and not re.match(r"^https?://", v):
            raise ValueError("Redirect URL must use HTTP or HTTPS")
        return v


class KYCStatus(BaseModel):
    """KYC status response."""

    status: str
    provider: Optional[str]
    reference_id: Optional[str]
    verified_at: Optional[str]
    documents_required: List[str] = []
    next_action: Optional[str]


class AccreditationRequest(BaseModel):
    """Accredited investor verification request."""

    verification_method: str = Field(..., regex="^(income|net_worth|professional)$")
    annual_income: Optional[int] = Field(None, ge=200000)  # cents
    net_worth: Optional[int] = Field(None, ge=100000000)  # cents (1M)
    professional_certifications: List[str] = []
    supporting_documents: List[str] = []

    @validator("professional_certifications")
    def validate_certifications(cls, v):
        allowed_certs = {"CPA", "CFP", "CFA", "Series7", "Series82", "PEF"}
        for cert in v:
            if cert not in allowed_certs:
                raise ValueError(f"Invalid certification: {cert}")
        return v


class AccreditationStatus(BaseModel):
    """Accreditation status response."""

    status: str
    verification_method: Optional[str]
    verified_at: Optional[str]
    expires_at: Optional[str]
    annual_review_due: Optional[str]


class CompanyKYBRequest(BaseModel):
    """Company KYB verification request."""

    legal_name: str = Field(..., min_length=1, max_length=255)
    tax_id: str = Field(..., regex=r"^\d{2}-\d{7}$")  # EIN format
    incorporation_state: str = Field(..., min_length=2, max_length=2)
    incorporation_country: str = Field(default="US", regex="^[A-Z]{2}$")
    entity_type: str = Field(..., regex="^(corporation|llc|partnership|lp)$")
    business_address: Dict[str, str]
    authorized_officers: List[Dict[str, str]]

    @validator("business_address")
    def validate_address(cls, v):
        required_fields = {"street", "city", "state", "zip_code", "country"}
        if not all(field in v for field in required_fields):
            raise ValueError(
                "Address must include street, city, state, zip_code, country"
            )
        return v


class OfferingComplianceRequest(BaseModel):
    """Securities offering compliance request."""

    offering_type: str = Field(..., regex="^(reg_cf|reg_a|rule_506b|rule_506c)$")
    target_amount: int = Field(..., gt=0, le=500000000)  # cents, max $5M for Reg CF
    minimum_investment: int = Field(..., gt=0)
    use_of_proceeds: str = Field(..., min_length=100, max_length=2000)
    risk_factors: List[str] = Field(..., min_items=1)
    financial_statements: Dict[str, Any]

    @validator("target_amount")
    def validate_target_amount(cls, v, values):
        offering_type = values.get("offering_type")
        if offering_type == "reg_cf" and v > 500000000:  # $5M limit
            raise ValueError("Reg CF offerings limited to $5M")
        return v


class ComplianceAudit(BaseModel):
    """Compliance audit response."""

    user_id: str
    kyc_status: str
    accreditation_status: str
    compliance_score: float
    risk_level: str
    last_audit: str
    issues: List[Dict[str, str]]
    required_actions: List[str]


# Security validation functions
def validate_ssn(ssn: str) -> bool:
    """Validate SSN format (for accreditation)."""
    pattern = r"^\d{3}-\d{2}-\d{4}$"
    return bool(re.match(pattern, ssn))


def validate_ein(ein: str) -> bool:
    """Validate EIN format."""
    pattern = r"^\d{2}-\d{7}$"
    return bool(re.match(pattern, ein))


def sanitize_pii(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize PII from compliance data for logging."""
    sensitive_fields = {"ssn", "tax_id", "account_number", "routing_number"}
    sanitized = {}

    for key, value in data.items():
        if key.lower() in sensitive_fields:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_pii(value)
        else:
            sanitized[key] = value

    return sanitized


# KYC Routes
@router.post("/kyc/initiate", response_model=Dict[str, str])
async def initiate_kyc(
    kyc_request: KYCRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    """Initiate KYC verification process."""

    logger.info(
        "Initiating KYC verification",
        user_id=str(current_user.id),
        provider=kyc_request.provider,
    )

    # Check if KYC already completed
    if current_user.kyc_status == "verified":
        raise ComplianceError("KYC already verified", regulation="KYC")

    # Rate limiting check (max 3 KYC attempts per day)
    if current_user.kyc_status == "rejected":
        # Check last attempt time
        pass  # Implementation would check attempt history

    try:
        # Generate verification session with provider
        reference_id = f"kyc_{uuid.uuid4().hex[:12]}"

        # Update user KYC status
        await db.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(
                kyc_status="pending",
                kyc_provider=kyc_request.provider,
                kyc_reference_id=reference_id,
            )
        )

        await db.commit()

        # In production, integrate with actual KYC provider
        verification_url = (
            f"https://verify.{kyc_request.provider}.com/session/{reference_id}"
        )

        logger.info(
            "KYC verification initiated",
            user_id=str(current_user.id),
            reference_id=reference_id,
        )

        return {
            "verification_url": verification_url,
            "reference_id": reference_id,
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }

    except Exception as e:
        logger.error(
            "KYC initiation failed", user_id=str(current_user.id), error=str(e)
        )
        raise ExternalServiceError("KYC Provider", "Failed to initiate verification")


@router.get("/kyc/status", response_model=KYCStatus)
async def get_kyc_status(
    current_user: User = Depends(get_current_user),
):
    """Get current user's KYC status."""

    next_action = None
    documents_required = []

    if current_user.kyc_status == "pending":
        next_action = "complete_verification"
        documents_required = ["government_id", "proof_of_address"]
    elif current_user.kyc_status == "rejected":
        next_action = "resubmit_documents"
        documents_required = ["government_id", "proof_of_address"]

    return KYCStatus(
        status=current_user.kyc_status,
        provider=current_user.kyc_provider,
        reference_id=current_user.kyc_reference_id,
        verified_at=(
            current_user.kyc_verified_at.isoformat()
            if current_user.kyc_verified_at
            else None
        ),
        documents_required=documents_required,
        next_action=next_action,
    )


# Accreditation Routes
@router.post("/accreditation/verify", response_model=Dict[str, str])
async def verify_accreditation(
    accreditation_request: AccreditationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    """Verify accredited investor status (Rule 506(c) requirement)."""

    logger.info(
        "Verifying accredited investor status",
        user_id=str(current_user.id),
        method=accreditation_request.verification_method,
    )

    # Must have verified KYC first
    if current_user.kyc_status != "verified":
        raise ComplianceError(
            "KYC verification required before accreditation", regulation="Rule 506(c)"
        )

    # Validate accreditation criteria
    is_accredited = False

    if accreditation_request.verification_method == "income":
        # $200k individual or $300k joint income for 2+ years
        if (
            accreditation_request.annual_income
            and accreditation_request.annual_income >= 20000000
        ):  # $200k in cents
            is_accredited = True

    elif accreditation_request.verification_method == "net_worth":
        # $1M net worth excluding primary residence
        if (
            accreditation_request.net_worth
            and accreditation_request.net_worth >= 100000000
        ):  # $1M in cents
            is_accredited = True

    elif accreditation_request.verification_method == "professional":
        # Series 7, 82, or 65 license holders
        valid_certs = {"Series7", "Series82", "Series65", "CFA", "CFP"}
        if any(
            cert in valid_certs
            for cert in accreditation_request.professional_certifications
        ):
            is_accredited = True

    status = "verified" if is_accredited else "rejected"

    # Update user accreditation status
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(
            accredited_status=status,
            accredited_verified_at=datetime.utcnow() if is_accredited else None,
            accredited_expires_at=(
                (datetime.utcnow() + timedelta(days=365)) if is_accredited else None
            ),
        )
    )

    await db.commit()

    logger.info(
        "Accreditation verification completed",
        user_id=str(current_user.id),
        status=status,
    )

    return {
        "status": status,
        "expires_at": (
            (datetime.utcnow() + timedelta(days=365)).isoformat()
            if is_accredited
            else None
        ),
        "annual_review_required": "true" if is_accredited else "false",
    }


@router.get("/accreditation/status", response_model=AccreditationStatus)
async def get_accreditation_status(
    current_user: User = Depends(get_current_user),
):
    """Get current user's accreditation status."""

    return AccreditationStatus(
        status=current_user.accredited_status,
        verified_at=(
            current_user.accredited_verified_at.isoformat()
            if current_user.accredited_verified_at
            else None
        ),
        expires_at=(
            current_user.accredited_expires_at.isoformat()
            if current_user.accredited_expires_at
            else None
        ),
        annual_review_due=(
            (current_user.accredited_verified_at + timedelta(days=365)).isoformat()
            if current_user.accredited_verified_at
            else None
        ),
    )


# Company KYB Routes
@router.post("/kyb/company/{company_id}", response_model=Dict[str, str])
async def initiate_company_kyb(
    company_id: uuid.UUID,
    kyb_request: CompanyKYBRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    """Initiate company KYB verification."""

    logger.info(
        "Initiating company KYB",
        user_id=str(current_user.id),
        company_id=str(company_id),
    )

    # Get company and verify ownership
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()

    if not company:
        raise ResourceNotFoundError("Company", str(company_id))

    if company.owner_id != current_user.id:
        raise AuthorizationError("Not authorized to modify this company")

    # Validate EIN format
    if not validate_ein(kyb_request.tax_id):
        raise ValidationError("Invalid EIN format", "tax_id")

    try:
        reference_id = f"kyb_{uuid.uuid4().hex[:12]}"

        # Update company KYB status
        await db.execute(
            update(Company)
            .where(Company.id == company_id)
            .values(
                kyb_status="pending",
                kyb_provider="jumio_business",
                kyb_reference_id=reference_id,
                legal_name=kyb_request.legal_name,
                tax_id=kyb_request.tax_id,
                incorporation_state=kyb_request.incorporation_state,
                entity_type=kyb_request.entity_type,
            )
        )

        await db.commit()

        logger.info(
            "Company KYB initiated",
            company_id=str(company_id),
            reference_id=reference_id,
        )

        return {
            "reference_id": reference_id,
            "status": "pending",
            "next_steps": "Awaiting document verification",
        }

    except Exception as e:
        logger.error(
            "Company KYB initiation failed", company_id=str(company_id), error=str(e)
        )
        raise ExternalServiceError(
            "KYB Provider", "Failed to initiate business verification"
        )


# Offering Compliance Routes
@router.post("/offerings/{offering_id}/compliance-check", response_model=Dict[str, Any])
async def check_offering_compliance(
    offering_id: uuid.UUID,
    compliance_request: OfferingComplianceRequest,
    current_user: User = Depends(require_permissions(["compliance:create", "admin"])),
    db: AsyncSession = Depends(get_database),
):
    """Check securities offering compliance requirements."""

    logger.info(
        "Checking offering compliance",
        user_id=str(current_user.id),
        offering_id=str(offering_id),
        offering_type=compliance_request.offering_type,
    )

    # Get offering
    result = await db.execute(
        select(Offering)
        .options(selectinload(Offering.company))
        .where(Offering.id == offering_id)
    )
    offering = result.scalar_one_or_none()

    if not offering:
        raise ResourceNotFoundError("Offering", str(offering_id))

    compliance_issues = []

    # Reg CF compliance checks
    if compliance_request.offering_type == "reg_cf":
        # $5M annual limit
        if compliance_request.target_amount > 500000000:
            compliance_issues.append("Target amount exceeds Reg CF $5M limit")

        # Company must be US entity
        if offering.company.incorporation_country != "US":
            compliance_issues.append("Company must be US entity for Reg CF")

        # Financial disclosure requirements
        if not compliance_request.financial_statements:
            compliance_issues.append("Financial statements required for Reg CF")

    # Rule 506(c) compliance checks
    elif compliance_request.offering_type == "rule_506c":
        # Must verify all investors are accredited
        # This would be checked during investment acceptance
        pass

    # General compliance checks
    if len(compliance_request.risk_factors) < 3:
        compliance_issues.append("At least 3 risk factors required")

    if len(compliance_request.use_of_proceeds) < 100:
        compliance_issues.append("Use of proceeds description too brief")

    compliance_score = max(0, 100 - (len(compliance_issues) * 10))

    return {
        "compliance_score": compliance_score,
        "status": "compliant" if compliance_score >= 80 else "non_compliant",
        "issues": compliance_issues,
        "recommendations": [
            "Review SEC guidelines for chosen offering type",
            "Consult with securities attorney",
            "Ensure all required disclosures are complete",
        ],
        "next_steps": [
            "File Form D if applicable",
            "Update offering documents",
            "Submit for final review",
        ],
    }


# Compliance Audit Routes
@router.get("/audit/user/{user_id}", response_model=ComplianceAudit)
async def audit_user_compliance(
    user_id: uuid.UUID,
    current_user: User = Depends(require_permissions(["compliance:read", "admin"])),
    db: AsyncSession = Depends(get_database),
):
    """Audit user's compliance status (admin only)."""

    logger.info(
        "Auditing user compliance",
        admin_user_id=str(current_user.id),
        target_user_id=str(user_id),
    )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise ResourceNotFoundError("User", str(user_id))

    # Calculate compliance score
    compliance_score = 0
    issues = []
    required_actions = []

    # KYC status (40 points)
    if user.kyc_status == "verified":
        compliance_score += 40
    elif user.kyc_status == "pending":
        compliance_score += 20
        issues.append({"type": "kyc", "message": "KYC verification pending"})
        required_actions.append("Complete KYC verification")
    else:
        issues.append({"type": "kyc", "message": "KYC not verified"})
        required_actions.append("Initiate KYC verification")

    # Email verification (20 points)
    if user.email_verified:
        compliance_score += 20
    else:
        issues.append({"type": "email", "message": "Email not verified"})
        required_actions.append("Verify email address")

    # Profile completeness (20 points)
    if user.full_name and user.username:
        compliance_score += 20
    else:
        issues.append({"type": "profile", "message": "Incomplete profile"})
        required_actions.append("Complete user profile")

    # Accreditation if applicable (20 points)
    if user.accredited_status == "verified":
        compliance_score += 20
    elif user.accredited_status == "unknown":
        compliance_score += 10

    # Risk level assessment
    if compliance_score >= 90:
        risk_level = "low"
    elif compliance_score >= 70:
        risk_level = "medium"
    else:
        risk_level = "high"

    return ComplianceAudit(
        user_id=str(user_id),
        kyc_status=user.kyc_status,
        accreditation_status=user.accredited_status,
        compliance_score=compliance_score,
        risk_level=risk_level,
        last_audit=datetime.utcnow().isoformat(),
        issues=issues,
        required_actions=required_actions,
    )


@router.get("/regulations/info", response_model=Dict[str, Any])
async def get_regulatory_information():
    """Get regulatory information and requirements."""

    return {
        "reg_cf": {
            "max_raise": 5000000,  # $5M
            "investor_limits": {
                "accredited": "no_limit",
                "non_accredited_income_net_worth_100k_plus": "10_percent_annual_income_or_net_worth",
                "non_accredited_income_net_worth_under_100k": "lesser_of_2200_or_5_percent_annual_income",
            },
            "requirements": [
                "Form C filing",
                "Annual reports",
                "Financial statements",
                "Intermediary platform",
            ],
        },
        "rule_506c": {
            "max_raise": "unlimited",
            "investor_requirements": "accredited_only",
            "verification_required": True,
            "requirements": [
                "Form D filing",
                "Accredited investor verification",
                "General solicitation allowed",
            ],
        },
        "accredited_investor_criteria": {
            "income": "200k_individual_300k_joint_for_2_years",
            "net_worth": "1m_excluding_primary_residence",
            "professional": [
                "Series 7 license holder",
                "Series 82 license holder",
                "Series 65 license holder",
                "Knowledgeable employee of fund",
            ],
        },
    }


# Export router
compliance_router = router
