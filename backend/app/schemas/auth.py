from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel


class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)
    profile_name: str | None = Field(default=None, max_length=64)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, value: str) -> str:
        if value.isdigit() or value.isalpha():
            raise ValueError("Le mot de passe doit mélanger lettres et chiffres")
        return value


class LoginIn(BaseModel):
    email: str = Field(description="Email ou nom d'utilisateur")
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(ORMModel):
    id: str
    email: EmailStr
    username: str
    full_name: str | None = None
    role: str
    is_active: bool
    last_login_at: str | None = None
    created_at: datetime | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=3, max_length=64)


class UserAdminUpdate(BaseModel):
    role: str | None = Field(default=None, pattern="^(user|admin)$")
    is_active: bool | None = None


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    avatar: str | None = Field(default=None, max_length=32)
    is_kids: bool = False
    is_default: bool = False
    language: str = Field(default="fr", max_length=10)
    pin: str | None = Field(default=None, min_length=4, max_length=8)
    preferences: dict = Field(default_factory=dict)


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    avatar: str | None = Field(default=None, max_length=32)
    is_kids: bool | None = None
    is_default: bool | None = None
    language: str | None = Field(default=None, max_length=10)
    pin: str | None = Field(default=None, min_length=4, max_length=8)
    preferences: dict | None = None


class ProfileOut(ORMModel):
    id: str
    name: str
    avatar: str | None = None
    is_kids: bool
    is_default: bool
    language: str
    preferences: dict = Field(default_factory=dict)
    has_pin: bool = False
    created_at: datetime | None = None


TokenOut.model_rebuild()
