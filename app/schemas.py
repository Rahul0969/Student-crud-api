"""Pydantic models: request validation and response shapes."""
from datetime import date
from typing import Optional

from pydantic import (
    BaseModel, EmailStr, Field, field_validator, model_validator,
)

PHONE_PATTERN = r"^\+?[0-9][0-9\s\-]{6,18}$"


class StudentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Aarav Sharma"])
    date_of_birth: date = Field(..., examples=["2004-05-17"])
    email: Optional[EmailStr] = Field(None, examples=["aarav@example.com"])
    phone: Optional[str] = Field(None, pattern=PHONE_PATTERN, examples=["+91 98765 43210"])
    course: Optional[str] = Field(None, max_length=100, examples=["Computer Science"])
    address: Optional[str] = Field(None, max_length=255)
    enrollment_date: Optional[date] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def dob_not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return v


class StudentCreate(StudentBase):
    """Used for POST and PUT (full replacement)."""

    @model_validator(mode="after")
    def need_contact(self):
        if not self.email and not self.phone:
            raise ValueError("Provide at least an email or a phone number")
        return self


class StudentUpdate(BaseModel):
    """Used for PATCH: every field optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    date_of_birth: Optional[date] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=PHONE_PATTERN)
    course: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    enrollment_date: Optional[date] = None

    @field_validator("name", "date_of_birth")
    @classmethod
    def required_fields_not_null(cls, v):
        if v is None:
            raise ValueError("this field cannot be null")
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("name must not be blank")
        if isinstance(v, date) and v > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return v


class Student(StudentBase):
    id: int


class AIQuestion(BaseModel):
    question: str = Field(..., min_length=3, max_length=500,
                          examples=["How many students are there?"])


class AIAnswer(BaseModel):
    question: str
    answer: str
    records_used: int
    source: str  # "ollama" or "fallback"
    model: Optional[str] = None
