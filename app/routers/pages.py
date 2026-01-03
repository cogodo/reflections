from datetime import date, timedelta
from calendar import monthrange
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    get_current_user_optional,
    get_current_user,
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_user_by_email,
)
from app.config import get_settings
from app.database import get_db
from app.models import User, DayEntry

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


def get_score_color(score: int | None) -> str:
    """Get the CSS color class for a score (Chess.com style)."""
    if score is None:
        return "score-none"
    colors = {
        0: "score-0",
        1: "score-1", 2: "score-2",
        3: "score-3", 4: "score-4",
        5: "score-5",
        6: "score-6", 7: "score-7",
        8: "score-8", 9: "score-9",
        10: "score-10",
    }
    return colors.get(score, "score-none")


def get_calendar_data(year: int, month: int, entries: dict[date, DayEntry]) -> list[list[dict]]:
    """Generate calendar grid data for a given month."""
    first_day = date(year, month, 1)
    days_in_month = monthrange(year, month)[1]
    
    # Get the weekday of the first day (0=Monday, 6=Sunday)
    # We'll display Sunday-Saturday, so adjust
    start_weekday = (first_day.weekday() + 1) % 7  # Convert to Sunday=0
    
    weeks = []
    current_week = [None] * start_weekday  # Pad the first week
    
    for day in range(1, days_in_month + 1):
        current_date = date(year, month, day)
        entry = entries.get(current_date)
        
        day_data = {
            "date": current_date,
            "day": day,
            "entry": entry,
            "score_class": get_score_color(entry.score if entry else None),
            "is_today": current_date == date.today(),
            "is_future": current_date > date.today(),
        }
        current_week.append(day_data)
        
        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []
    
    # Pad the last week if needed
    if current_week:
        current_week.extend([None] * (7 - len(current_week)))
        weeks.append(current_week)
    
    return weeks


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    user: Annotated[User | None, Depends(get_current_user_optional)],
):
    """Home page - redirects to calendar if logged in, otherwise login."""
    if user:
        return RedirectResponse(url="/calendar", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    user: Annotated[User | None, Depends(get_current_user_optional)],
):
    """Login page."""
    if user:
        return RedirectResponse(url="/calendar", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    email: str = Form(...),
    password: str = Form(...),
):
    """Handle login form submission."""
    user = await authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    response = RedirectResponse(url="/calendar", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        samesite="lax",
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    user: Annotated[User | None, Depends(get_current_user_optional)],
):
    """Registration page."""
    if user:
        return RedirectResponse(url="/calendar", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    """Handle registration form submission."""
    # Validation
    if password != password_confirm:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Passwords do not match"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    if len(password) < 6:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Password must be at least 6 characters"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if email exists
    existing = await get_user_by_email(db, email)
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Email already registered"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Create user
    user = User(email=email, hashed_password=get_password_hash(password))
    db.add(user)
    await db.flush()
    
    # Log them in
    access_token = create_access_token(data={"sub": str(user.id)})
    response = RedirectResponse(url="/calendar", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    """Logout and redirect to login."""
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response


@router.get("/calendar", response_class=HTMLResponse)
async def calendar_page(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    year: int | None = None,
    month: int | None = None,
):
    """Main calendar view."""
    today = date.today()
    year = year or today.year
    month = month or today.month
    
    # Validate month/year
    if month < 1 or month > 12:
        month = today.month
    if year < 2000 or year > 2100:
        year = today.year
    
    # Get entries for this month
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    
    result = await db.execute(
        select(DayEntry).where(
            and_(
                DayEntry.user_id == user.id,
                DayEntry.date >= first_day,
                DayEntry.date <= last_day,
            )
        )
    )
    entries_list = result.scalars().all()
    entries = {e.date: e for e in entries_list}
    
    # Generate calendar data
    weeks = get_calendar_data(year, month, entries)
    
    # Navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    month_names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "user": user,
            "weeks": weeks,
            "year": year,
            "month": month,
            "month_name": month_names[month],
            "prev_month": prev_month,
            "prev_year": prev_year,
            "next_month": next_month,
            "next_year": next_year,
            "today": today,
        },
    )


@router.get("/calendar/day/{entry_date}", response_class=HTMLResponse)
async def get_day_modal(
    request: Request,
    entry_date: date,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get the day entry modal content (HTMX partial)."""
    result = await db.execute(
        select(DayEntry).where(
            and_(DayEntry.user_id == user.id, DayEntry.date == entry_date)
        )
    )
    entry = result.scalar_one_or_none()
    
    is_future = entry_date > date.today()
    
    return templates.TemplateResponse(
        "components/entry_form.html",
        {
            "request": request,
            "entry": entry,
            "entry_date": entry_date,
            "is_future": is_future,
        },
    )


@router.post("/calendar/day/{entry_date}", response_class=HTMLResponse)
async def save_day_entry(
    request: Request,
    entry_date: date,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    score: int = Form(...),
    summary: str = Form(...),
):
    """Save or update a day entry (HTMX)."""
    # Validate
    if score < 0 or score > 10:
        return templates.TemplateResponse(
            "components/entry_form.html",
            {
                "request": request,
                "entry": None,
                "entry_date": entry_date,
                "error": "Score must be between 0 and 10",
                "is_future": entry_date > date.today(),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    if len(summary.strip()) == 0 or len(summary) > 200:
        return templates.TemplateResponse(
            "components/entry_form.html",
            {
                "request": request,
                "entry": None,
                "entry_date": entry_date,
                "error": "Summary must be 1-200 characters",
                "is_future": entry_date > date.today(),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if entry exists
    result = await db.execute(
        select(DayEntry).where(
            and_(DayEntry.user_id == user.id, DayEntry.date == entry_date)
        )
    )
    entry = result.scalar_one_or_none()
    
    if entry:
        entry.score = score
        entry.summary = summary.strip()
    else:
        entry = DayEntry(
            user_id=user.id,
            date=entry_date,
            score=score,
            summary=summary.strip(),
        )
        db.add(entry)
    
    await db.flush()
    await db.refresh(entry)
    
    # Return updated day cell for the calendar
    return templates.TemplateResponse(
        "components/day_cell.html",
        {
            "request": request,
            "day": {
                "date": entry_date,
                "day": entry_date.day,
                "entry": entry,
                "score_class": get_score_color(entry.score),
                "is_today": entry_date == date.today(),
                "is_future": False,
            },
            "success": True,
        },
        headers={"HX-Trigger": "closeModal"},
    )


@router.delete("/calendar/day/{entry_date}", response_class=HTMLResponse)
async def delete_day_entry(
    request: Request,
    entry_date: date,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a day entry (HTMX)."""
    result = await db.execute(
        select(DayEntry).where(
            and_(DayEntry.user_id == user.id, DayEntry.date == entry_date)
        )
    )
    entry = result.scalar_one_or_none()
    
    if entry:
        await db.delete(entry)
    
    # Return empty day cell
    return templates.TemplateResponse(
        "components/day_cell.html",
        {
            "request": request,
            "day": {
                "date": entry_date,
                "day": entry_date.day,
                "entry": None,
                "score_class": "score-none",
                "is_today": entry_date == date.today(),
                "is_future": entry_date > date.today(),
            },
        },
        headers={"HX-Trigger": "closeModal"},
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    """Settings page."""
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "user": user},
    )


@router.post("/settings/delete-account")
async def delete_account_page(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete account from settings page."""
    await db.delete(user)
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response

