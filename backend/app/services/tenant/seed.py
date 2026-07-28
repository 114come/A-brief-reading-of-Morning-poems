from sqlalchemy.orm import Session

from app.services.tenant.models import Permission


DEFAULT_PERMISSIONS = [
    {"code": "tenant:create", "name": "创建租户", "resource": "tenant", "action": "create"},
    {"code": "tenant:read", "name": "查看租户", "resource": "tenant", "action": "read"},
    {"code": "user:create", "name": "创建用户", "resource": "user", "action": "create"},
    {"code": "user:read", "name": "查看用户", "resource": "user", "action": "read"},
    {"code": "role:create", "name": "创建角色", "resource": "role", "action": "create"},
    {"code": "role:read", "name": "查看角色", "resource": "role", "action": "read"},
]


def seed_permissions(db: Session) -> None:
    for perm_data in DEFAULT_PERMISSIONS:
        existing = db.query(Permission).filter_by(code=perm_data["code"]).first()
        if not existing:
            perm = Permission(**perm_data)
            db.add(perm)
    db.commit()
