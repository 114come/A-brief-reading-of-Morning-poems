from collections.abc import Generator
from typing import Annotated, Any

from fastapi import Depends, Header
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import (
    MasterSessionLocal,
    get_cached_tenant_engine,
    get_master_db,
)
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.services.tenant.models import User
from app.services.tenant.repository import UserRepository

DbDep = Annotated[Session, Depends(get_master_db)]


async def get_current_user(
    db: DbDep,
    authorization: str | None = Header(default=None),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException("无效的认证头")
    token = authorization[7:]
    try:
        payload = decode_token(token)
    except Exception:
        raise UnauthorizedException("无效的令牌")

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if not user_id or not tenant_id:
        raise UnauthorizedException("令牌信息不完整")

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(int(user_id))
    if not user or user.tenant_id != int(tenant_id):
        raise UnauthorizedException("用户不存在或租户不匹配")
    if not user.is_active:
        raise UnauthorizedException("用户已被禁用")
    return user


UserDep = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    db: DbDep,
    authorization: str | None = Header(default=None),
) -> User | None:
    """可选登录依赖：未携带/无效令牌时返回 None，供公开内容接口使用"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    try:
        payload = decode_token(token)
    except Exception:
        return None
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if not user_id or not tenant_id:
        return None
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(int(user_id))
    if not user or user.tenant_id != int(tenant_id) or not user.is_active:
        return None
    return user


OptionalUserDep = Annotated[User | None, Depends(get_optional_user)]


def get_tenant_db(
    authorization: str | None = Header(default=None),
) -> Generator[Session, None, None]:
    """FastAPI Dependency: 从 JWT 提取 tenant_id，返回租户数据库 session"""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException("无效的认证头")
    token = authorization[7:]
    try:
        payload = decode_token(token)
    except Exception:
        raise UnauthorizedException("无效的令牌")

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise UnauthorizedException("令牌缺少 tenant_id")

    from app.services.tenant.models import Tenant

    master_db = MasterSessionLocal()
    try:
        tenant = master_db.query(Tenant).filter_by(id=int(tenant_id)).first()
        if not tenant:
            raise UnauthorizedException("租户不存在")
        if tenant.status != "active":
            raise UnauthorizedException("租户已停用")
    finally:
        master_db.close()

    engine = get_cached_tenant_engine(tenant)
    TenantSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TenantSessionLocal()
    try:
        yield db
    finally:
        db.close()


TenantDbDep = Annotated[Session, Depends(get_tenant_db)]


def require_permission(permission_code: str) -> Any:
    def checker(user: UserDep) -> User:
        if user.is_superuser:
            return user
        user_permissions = {
            p.code for role in user.roles for p in role.permissions
        }
        if permission_code not in user_permissions:
            raise ForbiddenException(f"缺少权限: {permission_code}")
        return user
    return Depends(checker)
