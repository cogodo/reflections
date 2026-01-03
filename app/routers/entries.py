from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User, DayEntry
from app.schemas import (
    DayEntryCreate,
    DayEntryUpdate,
    DayEntryResponse,
    DayEntryListResponse,
)

router = APIRouter(prefix="/api/entries", tags=["entries"])


@router.get("", response_model=DayEntryListResponse)
async def list_entries(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    start_date: date | None = Query(None, description="Filter entries from this date"),
    end_date: date | None = Query(None, description="Filter entries until this date"),
    min_score: int | None = Query(None, ge=0, le=10, description="Minimum score filter"),
    max_score: int | None = Query(None, ge=0, le=10, description="Maximum score filter"),
):
    """List all day entries for the current user with optional filters."""
    query = select(DayEntry).where(DayEntry.user_id == current_user.id)
    
    # Apply filters
    if start_date:
        query = query.where(DayEntry.date >= start_date)
    if end_date:
        query = query.where(DayEntry.date <= end_date)
    if min_score is not None:
        query = query.where(DayEntry.score >= min_score)
    if max_score is not None:
        query = query.where(DayEntry.score <= max_score)
    
    query = query.order_by(DayEntry.date.desc())
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    return DayEntryListResponse(entries=entries, total=len(entries))


@router.get("/{entry_date}", response_model=DayEntryResponse)
async def get_entry(
    entry_date: date,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a specific day entry by date."""
    result = await db.execute(
        select(DayEntry).where(
            and_(DayEntry.user_id == current_user.id, DayEntry.date == entry_date)
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No entry found for {entry_date}",
        )
    
    return entry


@router.post("", response_model=DayEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    entry_data: DayEntryCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new day entry."""
    # Check if entry already exists for this date
    existing = await db.execute(
        select(DayEntry).where(
            and_(DayEntry.user_id == current_user.id, DayEntry.date == entry_data.date)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Entry already exists for {entry_data.date}. Use PUT to update.",
        )
    
    entry = DayEntry(
        user_id=current_user.id,
        date=entry_data.date,
        score=entry_data.score,
        summary=entry_data.summary,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    
    return entry


@router.put("/{entry_date}", response_model=DayEntryResponse)
async def update_entry(
    entry_date: date,
    entry_data: DayEntryUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an existing day entry."""
    result = await db.execute(
        select(DayEntry).where(
            and_(DayEntry.user_id == current_user.id, DayEntry.date == entry_date)
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No entry found for {entry_date}",
        )
    
    # Update fields if provided
    if entry_data.score is not None:
        entry.score = entry_data.score
    if entry_data.summary is not None:
        entry.summary = entry_data.summary
    
    await db.flush()
    await db.refresh(entry)
    
    return entry


@router.delete("/{entry_date}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_date: date,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a day entry."""
    result = await db.execute(
        select(DayEntry).where(
            and_(DayEntry.user_id == current_user.id, DayEntry.date == entry_date)
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No entry found for {entry_date}",
        )
    
    await db.delete(entry)
    return None

