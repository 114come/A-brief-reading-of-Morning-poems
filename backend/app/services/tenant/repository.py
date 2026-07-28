from typing import Any

from sqlalchemy.orm import Session

from app.services.tenant.models import Permission, Role, Tenant, User


class TenantRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs: Any) -> Tenant:
        tenant = Tenant(**kwargs)
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def get_by_id(self, tenant_id: int) -> Tenant | None:
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_by_code(self, code: str) -> Tenant | None:
        return self.db.query(Tenant).filter(Tenant.code == code).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        return self.db.query(Tenant).offset(skip).limit(limit).all()


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs: Any) -> User:
        user = User(**kwargs)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str, tenant_id: int) -> User | None:
        return (
            self.db.query(User)
            .filter(User.username == username, User.tenant_id == tenant_id)
            .first()
        )

    def list_by_tenant(self, tenant_id: int, skip: int = 0, limit: int = 100) -> list[User]:
        return (
            self.db.query(User)
            .filter(User.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .all()
        )


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs: Any) -> Role:
        role = Role(**kwargs)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def get_by_code(self, code: str, tenant_id: int) -> Role | None:
        return (
            self.db.query(Role)
            .filter(Role.code == code, Role.tenant_id == tenant_id)
            .first()
        )
