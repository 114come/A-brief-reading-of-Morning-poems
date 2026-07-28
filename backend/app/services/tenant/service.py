from sqlalchemy.orm import Session

from app.core.database import create_tenant_database
from app.core.security import get_password_hash, verify_password
from app.services.tenant.models import Tenant, User
from app.services.tenant.repository import TenantRepository, UserRepository


class TenantService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.tenant_repo = TenantRepository(db)
        self.user_repo = UserRepository(db)

    def create_tenant(
        self,
        name: str,
        code: str,
        admin_username: str,
        admin_password: str,
        admin_email: str,
    ) -> tuple[Tenant, User]:
        db_name = f"tenant_{code}"
        tenant = self.tenant_repo.create(
            name=name,
            code=code,
            db_name=db_name,
            db_host="localhost",
            db_port=3306,
            db_user="root",
            db_password_encrypted="",  # TODO: encrypt real password
        )
        # 创建物理数据库
        create_tenant_database(tenant)
        # TODO: 在租户库中创建基础表（users, roles, permissions）
        admin = self.user_repo.create(
            tenant_id=tenant.id,
            username=admin_username,
            email=admin_email,
            password_hash=get_password_hash(admin_password),
            is_superuser=True,
        )
        return tenant, admin

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        tenant_id: int,
        is_superuser: bool = False,
    ) -> User:
        return self.user_repo.create(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            tenant_id=tenant_id,
            is_superuser=is_superuser,
        )

    def authenticate_user(
        self, username: str, password: str, tenant_id: int
    ) -> User | None:
        user = self.user_repo.get_by_username(username, tenant_id)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
