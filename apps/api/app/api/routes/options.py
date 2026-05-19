"""HTTP routes for options chain and strategies."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter(prefix="/options", tags=["options"])


class OptionLegSchema(BaseModel):
    """Schema for single options leg."""

    conid: int
    right: str  # CALL or PUT
    strike: str  # Decimal as string
    expiration: str  # YYYYMMDD
    quantity: float
    side: str  # BUY or SELL
    limit_price: str | None = None


class OptionStrategySchema(BaseModel):
    """Schema for multi-leg options strategy."""

    name: str
    legs: list[OptionLegSchema]
    description: str = ""


class CallSpreadRequestSchema(BaseModel):
    """Request schema for call spread."""

    conid: int
    expiration: str  # YYYYMMDD
    long_strike: str  # Decimal as string
    short_strike: str
    quantity: float = 100.0


class PutSpreadRequestSchema(BaseModel):
    """Request schema for put spread."""

    conid: int
    expiration: str
    long_strike: str
    short_strike: str
    quantity: float = 100.0


class CollarRequestSchema(BaseModel):
    """Request schema for collar strategy."""

    conid: int
    expiration: str
    call_strike: str
    put_strike: str
    shares: float


@router.get("/expirations/{conid}")
async def get_option_expirations(
    conid: int,
) -> dict:
    """Get available option expirations.
    
    Args:
        conid: Underlying contract ID
    
    Returns:
        List of expirations in YYYYMMDD format
    """
    try:
        # For now, return disabled sentinel
        return {
            "status": "disabled_in_mvp",
            "message": "Options chain queries disabled until Phase 16",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strikes/{conid}")
async def get_option_strikes(
    conid: int,
    expiration: str = Query(..., description="Expiration in YYYYMMDD format"),
) -> dict:
    """Get available strikes for an expiration.
    
    Args:
        conid: Underlying contract ID
        expiration: Expiration in YYYYMMDD format
    
    Returns:
        List of strike prices
    """
    try:
        return {
            "status": "disabled_in_mvp",
            "message": "Options chain queries disabled until Phase 16",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contracts/{conid}")
async def get_option_contracts(
    conid: int,
    expiration: str = Query(..., description="Expiration in YYYYMMDD format"),
    right: str = Query("CALL", description="CALL or PUT"),
) -> dict:
    """Get option contracts for a strike/expiration.
    
    Args:
        conid: Underlying contract ID
        expiration: Expiration in YYYYMMDD format
        right: CALL or PUT
    
    Returns:
        List of option contract dicts
    """
    try:
        return {
            "status": "disabled_in_mvp",
            "message": "Options chain queries disabled until Phase 16",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies/call-spread")
async def build_call_spread(request: CallSpreadRequestSchema) -> dict:
    """Build a call spread strategy.
    
    Args:
        request: Call spread configuration
    
    Returns:
        Option strategy with 2 legs
    """
    try:
        return {
            "status": "disabled_in_mvp",
            "message": "Strategy building disabled until Phase 16",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies/put-spread")
async def build_put_spread(request: PutSpreadRequestSchema) -> dict:
    """Build a put spread strategy.
    
    Args:
        request: Put spread configuration
    
    Returns:
        Option strategy with 2 legs
    """
    try:
        return {
            "status": "disabled_in_mvp",
            "message": "Strategy building disabled until Phase 16",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies/collar")
async def build_collar(request: CollarRequestSchema) -> dict:
    """Build a protective collar strategy.
    
    Args:
        request: Collar configuration
    
    Returns:
        Option strategy with 2 legs (long put, short call)
    """
    try:
        return {
            "status": "disabled_in_mvp",
            "message": "Strategy building disabled until Phase 16",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
