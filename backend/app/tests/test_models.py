from app.services.tenant.models import Permission, Role, Tenant, User


def test_models_importable() -> None:
    assert Tenant.__tablename__ == "tenants"
    assert User.__tablename__ == "users"
    assert Role.__tablename__ == "roles"
    assert Permission.__tablename__ == "permissions"
