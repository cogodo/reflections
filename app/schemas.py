from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============ Auth Schemas ============

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None


# ============ Entry Schemas ============

class DayEntryCreate(BaseModel):
    date: date
    score: int = Field(..., ge=0, le=10, description="Score from 0 (blunder) to 10 (brilliant)")
    summary: str = Field(..., min_length=1, max_length=200)
    
    @field_validator("summary")
    @classmethod
    def strip_summary(cls, v: str) -> str:
        return v.strip()


class DayEntryUpdate(BaseModel):
    score: int | None = Field(None, ge=0, le=10)
    summary: str | None = Field(None, min_length=1, max_length=200)
    
    @field_validator("summary")
    @classmethod
    def strip_summary(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class DayEntryResponse(BaseModel):
    id: int
    date: date
    score: int
    summary: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DayEntryListResponse(BaseModel):
    entries: list[DayEntryResponse]
    total: int

