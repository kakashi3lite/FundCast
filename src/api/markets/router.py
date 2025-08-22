"""Prediction markets routes with order book and AMM support."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
import uuid
import math

import structlog
from fastapi import APIRouter, Depends, Request, Query, Path, HTTPException
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, text
from sqlalchemy.orm import selectinload

from ..database import get_database, User, Market, MarketPosition
from ..exceptions import (
    ResourceNotFoundError, 
    AuthorizationError, 
    ValidationError, 
    MarketError,
    InferenceError
)
from ..users.dependencies import get_current_user, require_permissions
from ..config import settings

logger = structlog.get_logger(__name__)
router = APIRouter()


# Request/Response Models
class MarketCreate(BaseModel):
    """Create prediction market request."""
    title: str = Field(..., min_length=10, max_length=255)
    description: str = Field(..., min_length=50, max_length=2000)
    category: str = Field(..., regex="^(business|finance|crypto|sports|politics|technology)$")
    market_type: str = Field(default="binary", regex="^(binary|categorical|scalar)$")
    engine_type: str = Field(default="orderbook", regex="^(orderbook|amm)$")
    resolution_source: Optional[str] = Field(None, max_length=500)
    resolution_date: Optional[datetime] = None
    outcomes: List[str] = Field(default=["Yes", "No"])
    initial_liquidity: Optional[int] = Field(None, ge=100000)  # cents, min $1000
    
    @validator('resolution_date')
    def validate_resolution_date(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('Resolution date must be in the future')
        if v and v > datetime.utcnow() + timedelta(days=365):
            raise ValueError('Resolution date cannot be more than 1 year in the future')
        return v
    
    @validator('outcomes')
    def validate_outcomes(cls, v, values):
        market_type = values.get('market_type', 'binary')
        if market_type == 'binary' and len(v) != 2:
            raise ValueError('Binary markets must have exactly 2 outcomes')
        if market_type == 'categorical' and (len(v) < 2 or len(v) > 10):
            raise ValueError('Categorical markets must have 2-10 outcomes')
        return v


class MarketUpdate(BaseModel):
    """Update market request."""
    description: Optional[str] = Field(None, min_length=50, max_length=2000)
    resolution_source: Optional[str] = Field(None, max_length=500)
    resolution_date: Optional[datetime] = None
    status: Optional[str] = Field(None, regex="^(active|paused|resolved|cancelled)$")


class MarketOrder(BaseModel):
    """Place market order request."""
    outcome: str = Field(..., min_length=1, max_length=100)
    side: str = Field(..., regex="^(buy|sell)$")
    order_type: str = Field(default="market", regex="^(market|limit)$")
    quantity: int = Field(..., gt=0, le=1000000)  # Max 1M shares
    price: Optional[float] = Field(None, ge=0.01, le=0.99)  # Probability between 1% and 99%
    
    @validator('price')
    def validate_price(cls, v, values):
        order_type = values.get('order_type')
        if order_type == 'limit' and v is None:
            raise ValueError('Limit orders require a price')
        return v


class MarketTrade(BaseModel):
    """Market trade response."""
    id: str
    market_id: str
    user_id: str
    outcome: str
    side: str
    quantity: int
    price: float
    timestamp: str
    fees: int  # cents


class MarketPosition(BaseModel):
    """User market position response."""
    market_id: str
    outcome: str
    shares: float
    avg_price: float
    current_value: int  # cents
    unrealized_pnl: int  # cents
    percentage_return: float


class MarketStats(BaseModel):
    """Market statistics response."""
    market_id: str
    total_volume: int  # cents
    total_shares: int
    unique_traders: int
    price_change_24h: float
    volatility: float
    liquidity_depth: Dict[str, int]  # outcome -> liquidity in cents


class MarketResponse(BaseModel):
    """Market details response."""
    id: str
    title: str
    description: str
    category: str
    market_type: str
    engine_type: str
    status: str
    resolution_source: Optional[str]
    resolution_date: Optional[str]
    resolved_at: Optional[str]
    resolution_value: Optional[str]
    outcomes: List[str]
    current_prices: Dict[str, float]  # outcome -> probability
    total_volume: int
    created_at: str
    updated_at: str


class MarketList(BaseModel):
    """Market list response."""
    markets: List[MarketResponse]
    total: int
    page: int
    per_page: int


# Utility functions
def calculate_probability_from_shares(yes_shares: int, no_shares: int) -> float:
    """Calculate implied probability from shares outstanding."""
    if yes_shares + no_shares == 0:
        return 0.5
    return yes_shares / (yes_shares + no_shares)


def calculate_amm_price(k: float, yes_liquidity: int, no_liquidity: int, trade_size: int, side: str) -> float:
    """Calculate AMM price using constant product formula."""
    if side == "buy":
        # Calculate price for buying YES shares
        new_yes_liquidity = yes_liquidity + trade_size
        new_no_liquidity = k / new_yes_liquidity
        price_impact = (no_liquidity - new_no_liquidity) / trade_size
    else:
        # Calculate price for selling YES shares  
        new_yes_liquidity = yes_liquidity - trade_size
        new_no_liquidity = k / new_yes_liquidity
        price_impact = (new_no_liquidity - no_liquidity) / trade_size
    
    return max(0.01, min(0.99, price_impact))


def validate_market_access(user: User, market_type: str) -> bool:
    """Validate user has access to market type."""
    # Some markets may require accredited investor status
    if market_type in ["high_stakes", "institutional"]:
        return user.accredited_status == "verified"
    return True


# Market CRUD Routes
@router.post("/", response_model=MarketResponse)
async def create_market(
    market_data: MarketCreate,
    current_user: User = Depends(require_permissions(["market:create", "admin"])),
    db: AsyncSession = Depends(get_database),
):
    """Create a new prediction market (admin only)."""
    
    logger.info(
        "Creating market",
        user_id=str(current_user.id),
        title=market_data.title,
        market_type=market_data.market_type,
    )
    
    try:
        # Create market record
        market = Market(
            title=market_data.title,
            description=market_data.description,
            category=market_data.category,
            market_type=market_data.market_type,
            engine_type=market_data.engine_type,
            resolution_source=market_data.resolution_source,
            resolution_date=market_data.resolution_date,
            status="active",
            metadata={
                "outcomes": market_data.outcomes,
                "creator_id": str(current_user.id),
                "initial_liquidity": market_data.initial_liquidity,
            },
        )
        
        db.add(market)
        await db.commit()
        await db.refresh(market)
        
        # Initialize AMM liquidity if specified
        if market_data.engine_type == "amm" and market_data.initial_liquidity:
            # Create initial liquidity positions
            for outcome in market_data.outcomes:
                position = MarketPosition(
                    user_id=current_user.id,
                    market_id=market.id,
                    outcome=outcome,
                    shares=market_data.initial_liquidity // len(market_data.outcomes),
                    avg_price=0.5,  # Start at 50% probability
                    current_value=market_data.initial_liquidity // len(market_data.outcomes),
                )
                db.add(position)
        
        await db.commit()
        
        logger.info("Market created successfully", market_id=str(market.id))
        
        return MarketResponse(
            id=str(market.id),
            title=market.title,
            description=market.description,
            category=market.category,
            market_type=market.market_type,
            engine_type=market.engine_type,
            status=market.status,
            resolution_source=market.resolution_source,
            resolution_date=market.resolution_date.isoformat() if market.resolution_date else None,
            resolved_at=None,
            resolution_value=None,
            outcomes=market_data.outcomes,
            current_prices={outcome: 0.5 for outcome in market_data.outcomes},
            total_volume=0,
            created_at=market.created_at.isoformat(),
            updated_at=market.updated_at.isoformat(),
        )
        
    except Exception as e:
        logger.error("Market creation failed", error=str(e))
        raise MarketError("Failed to create market")


@router.get("/", response_model=MarketList)
async def list_markets(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query("active", description="Filter by status"),
    search: Optional[str] = Query(None, max_length=255, description="Search query"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    """List prediction markets with pagination and filtering."""
    
    logger.info(
        "Listing markets",
        user_id=str(current_user.id),
        page=page,
        category=category,
        status=status,
    )
    
    # Build query
    query = select(Market)
    
    if category:
        query = query.where(Market.category == category)
    
    if status:
        query = query.where(Market.status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Market.title.ilike(search_term),
                Market.description.ilike(search_term),
            )
        )
    
    # Get total count
    count_result = await db.execute(
        select(func.count(Market.id)).select_from(
            query.subquery()
        )
    )
    total = count_result.scalar()
    
    # Get paginated results
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(Market.created_at.desc())
    
    result = await db.execute(query)
    markets = result.scalars().all()
    
    # Convert to response format
    market_responses = []
    for market in markets:
        outcomes = market.metadata.get("outcomes", ["Yes", "No"])
        
        # Calculate current prices (simplified - would use actual market data)
        current_prices = {outcome: 0.5 for outcome in outcomes}
        
        market_responses.append(MarketResponse(
            id=str(market.id),
            title=market.title,
            description=market.description,
            category=market.category,
            market_type=market.market_type,
            engine_type=market.engine_type,
            status=market.status,
            resolution_source=market.resolution_source,
            resolution_date=market.resolution_date.isoformat() if market.resolution_date else None,
            resolved_at=market.resolved_at.isoformat() if market.resolved_at else None,
            resolution_value=market.resolution_value,
            outcomes=outcomes,
            current_prices=current_prices,
            total_volume=0,  # Would calculate from trades
            created_at=market.created_at.isoformat(),
            updated_at=market.updated_at.isoformat(),
        ))
    
    return MarketList(
        markets=market_responses,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{market_id}", response_model=MarketResponse)
async def get_market(
    market_id: uuid.UUID = Path(..., description="Market ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    """Get market details by ID."""
    
    result = await db.execute(select(Market).where(Market.id == market_id))
    market = result.scalar_one_or_none()
    
    if not market:
        raise ResourceNotFoundError("Market", str(market_id))
    
    # Check market access
    if not validate_market_access(current_user, market.market_type):
        raise AuthorizationError("Insufficient verification for this market type")
    
    outcomes = market.metadata.get("outcomes", ["Yes", "No"])
    current_prices = {outcome: 0.5 for outcome in outcomes}
    
    return MarketResponse(
        id=str(market.id),
        title=market.title,
        description=market.description,
        category=market.category,
        market_type=market.market_type,
        engine_type=market.engine_type,
        status=market.status,
        resolution_source=market.resolution_source,
        resolution_date=market.resolution_date.isoformat() if market.resolution_date else None,
        resolved_at=market.resolved_at.isoformat() if market.resolved_at else None,
        resolution_value=market.resolution_value,
        outcomes=outcomes,
        current_prices=current_prices,
        total_volume=0,
        created_at=market.created_at.isoformat(),
        updated_at=market.updated_at.isoformat(),
    )


# Trading Routes
@router.post("/{market_id}/orders", response_model=Dict[str, Any])
async def place_order(
    market_id: uuid.UUID,
    order: MarketOrder,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    """Place a market order."""
    
    logger.info(
        "Placing market order",
        user_id=str(current_user.id),
        market_id=str(market_id),
        outcome=order.outcome,
        side=order.side,
        quantity=order.quantity,
    )
    
    # Get market
    result = await db.execute(select(Market).where(Market.id == market_id))
    market = result.scalar_one_or_none()
    
    if not market:
        raise ResourceNotFoundError("Market", str(market_id))
    
    if market.status != "active":
        raise MarketError("Market is not active for trading", str(market_id))
    
    # Validate outcome
    outcomes = market.metadata.get("outcomes", ["Yes", "No"])
    if order.outcome not in outcomes:
        raise ValidationError(f"Invalid outcome: {order.outcome}")
    
    # Check market access
    if not validate_market_access(current_user, market.market_type):
        raise AuthorizationError("Insufficient verification for this market type")
    
    # Validate user has sufficient balance (simplified check)
    max_cost = order.quantity * (order.price or 0.99) * 100  # Convert to cents
    if max_cost > 100000:  # $1000 limit for demo
        raise ValidationError("Insufficient balance for this order")
    
    try:
        # Execute order based on engine type
        if market.engine_type == "orderbook":
            # Order book matching logic would go here
            execution_price = order.price or 0.5
        else:  # AMM
            # AMM price calculation
            execution_price = calculate_amm_price(10000, 5000, 5000, order.quantity, order.side)
        
        # Update or create user position
        position_result = await db.execute(
            select(MarketPosition).where(
                and_(
                    MarketPosition.user_id == current_user.id,
                    MarketPosition.market_id == market_id,
                    MarketPosition.outcome == order.outcome,
                )
            )
        )
        position = position_result.scalar_one_or_none()
        
        if position:
            # Update existing position
            if order.side == "buy":
                new_shares = position.shares + order.quantity
                new_avg_price = (
                    (position.shares * position.avg_price + order.quantity * execution_price) / new_shares
                )
            else:  # sell
                new_shares = max(0, position.shares - order.quantity)
                new_avg_price = position.avg_price  # Keep same avg price when selling
            
            await db.execute(
                update(MarketPosition)
                .where(MarketPosition.id == position.id)
                .values(
                    shares=new_shares,
                    avg_price=new_avg_price,
                    current_value=int(new_shares * execution_price * 100),
                    unrealized_pnl=int((execution_price - new_avg_price) * new_shares * 100),
                )
            )
        else:
            # Create new position
            if order.side == "buy":
                new_position = MarketPosition(
                    user_id=current_user.id,
                    market_id=market_id,
                    outcome=order.outcome,
                    shares=order.quantity,
                    avg_price=execution_price,
                    current_value=int(order.quantity * execution_price * 100),
                    unrealized_pnl=0,
                )
                db.add(new_position)
        
        await db.commit()
        
        logger.info(
            "Order executed",
            user_id=str(current_user.id),
            market_id=str(market_id),
            execution_price=execution_price,
        )
        
        return {
            "order_id": str(uuid.uuid4()),
            "status": "filled",
            "execution_price": execution_price,
            "quantity_filled": order.quantity,
            "fees": int(order.quantity * execution_price * 0.01 * 100),  # 1% fee in cents
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error("Order execution failed", error=str(e))
        raise MarketError("Failed to execute order", str(market_id))


@router.get("/{market_id}/positions", response_model=List[MarketPosition])
async def get_user_positions(
    market_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    """Get user's positions in a market."""
    
    result = await db.execute(
        select(MarketPosition).where(
            and_(
                MarketPosition.user_id == current_user.id,
                MarketPosition.market_id == market_id,
                MarketPosition.shares > 0,
            )
        )
    )
    positions = result.scalars().all()
    
    return [
        MarketPosition(
            market_id=str(position.market_id),
            outcome=position.outcome,
            shares=float(position.shares),
            avg_price=float(position.avg_price),
            current_value=position.current_value,
            unrealized_pnl=position.unrealized_pnl,
            percentage_return=((position.current_value / (position.shares * position.avg_price * 100)) - 1) * 100
            if position.shares > 0 else 0,
        )
        for position in positions
    ]


@router.get("/{market_id}/stats", response_model=MarketStats)
async def get_market_stats(
    market_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_database),
):
    """Get market statistics."""
    
    # Get market
    result = await db.execute(select(Market).where(Market.id == market_id))
    market = result.scalar_one_or_none()
    
    if not market:
        raise ResourceNotFoundError("Market", str(market_id))
    
    # Get position statistics
    stats_result = await db.execute(
        select(
            func.count(MarketPosition.user_id.distinct()).label("unique_traders"),
            func.sum(MarketPosition.shares).label("total_shares"),
            func.sum(MarketPosition.current_value).label("total_value"),
        ).where(MarketPosition.market_id == market_id)
    )
    
    stats = stats_result.first()
    
    return MarketStats(
        market_id=str(market_id),
        total_volume=stats.total_value or 0,
        total_shares=int(stats.total_shares or 0),
        unique_traders=stats.unique_traders or 0,
        price_change_24h=0.0,  # Would calculate from historical data
        volatility=0.1,  # Would calculate from price history
        liquidity_depth={"Yes": 10000, "No": 10000},  # Simplified
    )


# Market Resolution Routes
@router.post("/{market_id}/resolve", response_model=Dict[str, str])
async def resolve_market(
    market_id: uuid.UUID,
    resolution_data: Dict[str, Any],
    current_user: User = Depends(require_permissions(["market:resolve", "admin"])),
    db: AsyncSession = Depends(get_database),
):
    """Resolve a prediction market (admin only)."""
    
    logger.info(
        "Resolving market",
        admin_user_id=str(current_user.id),
        market_id=str(market_id),
    )
    
    result = await db.execute(select(Market).where(Market.id == market_id))
    market = result.scalar_one_or_none()
    
    if not market:
        raise ResourceNotFoundError("Market", str(market_id))
    
    if market.status == "resolved":
        raise MarketError("Market is already resolved", str(market_id))
    
    resolution_value = resolution_data.get("outcome")
    outcomes = market.metadata.get("outcomes", ["Yes", "No"])
    
    if resolution_value not in outcomes:
        raise ValidationError(f"Invalid resolution outcome: {resolution_value}")
    
    # Update market status
    await db.execute(
        update(Market)
        .where(Market.id == market_id)
        .values(
            status="resolved",
            resolved_at=datetime.utcnow(),
            resolution_value=resolution_value,
        )
    )
    
    await db.commit()
    
    logger.info(
        "Market resolved",
        market_id=str(market_id),
        resolution_value=resolution_value,
    )
    
    return {
        "status": "resolved",
        "resolution_value": resolution_value,
        "resolved_at": datetime.utcnow().isoformat(),
    }


# Export router
markets_router = router