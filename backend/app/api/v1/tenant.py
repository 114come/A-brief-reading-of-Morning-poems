from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import DbDep, require_permission
from app.core.exceptions import UnauthorizedException, ValidationException
from app.core.response import UnifiedResponse
from app.core.security import create_access_token
from app.services.tenant.models import User
from app.services.tenant.schemas import (
    RoleCreate,
    TenantCreate,
    TenantResponse,
    TokenResponse,
    UserLogin,
)
from app.services.tenant.service import TenantService

router = APIRouter(prefix="/tenant", tags=["租户权限"])


@router.post("/tenants", response_model=UnifiedResponse[Any])
def create_tenant(data: TenantCreate, db: DbDep) -> UnifiedResponse[Any]:
    service = TenantService(db)
    if service.tenant_repo.get_by_code(data.code):
        raise ValidationException(f"租户编码 {data.code} 已存在")

    tenant, user = service.create_tenant(
        name=data.name,
        code=data.code,
        admin_username=data.admin_username,
        admin_password=data.admin_password,
        admin_email=data.admin_email,
    )
    return UnifiedResponse.success(
        data={
            "tenant": TenantResponse.model_validate(tenant).model_dump(),
            "admin_username": user.username,
        },
        message="租户创建成功",
    )


@router.post("/auth/login", response_model=UnifiedResponse[Any])
def login(data: UserLogin, db: DbDep) -> UnifiedResponse[Any]:
    # 先根据用户名查用户，获取 tenant_id
    # 简化：假设用户名全局唯一，或通过其他方式传入 tenant_id
    # 实际生产环境：登录时需要同时提供租户编码
    raise ValidationException("请使用 /auth/login_with_tenant 接口")


@router.post("/auth/login_with_tenant", response_model=UnifiedResponse[Any])
def login_with_tenant(
    tenant_code: str, data: UserLogin, db: DbDep
) -> UnifiedResponse[Any]:
    service = TenantService(db)
    tenant = service.tenant_repo.get_by_code(tenant_code)
    if not tenant:
        raise UnauthorizedException("租户不存在")

    user = service.authenticate_user(data.username, data.password, tenant.id)
    if not user:
        raise UnauthorizedException("用户名或密码错误")

    access_token = create_access_token(
        data={"sub": str(user.id), "tenant_id": str(tenant.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_access_token(
        data={"sub": str(user.id), "tenant_id": str(tenant.id), "type": "refresh"},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )

    return UnifiedResponse.success(
        data=TokenResponse(
            access_token=access_token, refresh_token=refresh_token
        ).model_dump(),
        message="登录成功",
    )


@router.post("/roles", response_model=UnifiedResponse[Any])
def create_role(
    data: RoleCreate,
    db: DbDep,
    _auth_user: Annotated[User, require_permission("role:create")],
) -> UnifiedResponse[Any]:
    from app.services.tenant.repository import RoleRepository

    repo = RoleRepository(db)
    role = repo.create(**data.model_dump())
    return UnifiedResponse.success(
        data={"id": role.id, "name": role.name}, message="角色创建成功"
    )
