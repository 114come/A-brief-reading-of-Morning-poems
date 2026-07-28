from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenantBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50, pattern=r"^[a-z0-9_]+$")


class TenantCreate(TenantBase):
    admin_username: str = Field(..., max_length=50)
    admin_password: str = Field(..., min_length=6, max_length=50)
    admin_email: str = Field(..., max_length=100)


class TenantResponse(TenantBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    db_name: str
    created_at: datetime


class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    email: str = Field(..., max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=50)
    tenant_id: int
    is_superuser: bool = False


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    is_superuser: bool
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RoleCreate(BaseModel):
    name: str = Field(..., max_length=50)
    code: str = Field(..., max_length=50)
    description: str | None = None
    tenant_id: int


class PermissionCreate(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=100)
    resource: str = Field(..., max_length=100)
    action: str = Field(..., max_length=50)
