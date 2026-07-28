from typing import Annotated, Any

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_master_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.services.tenant.models import User
from app.services.tenant.repository import UserRepository

DbDep = Annotated[Session, Depends(get_master_db)]


async def get_current_user(
    db: DbDep,
    authorization: str = Header(...),
) -> User:
    if not authorization.startswith("Bearer "):
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
