import pytest
from sqlalchemy import inspect

from app.core.database import create_tenant_database, get_tenant_engine
from app.services.tenant.models import Tenant


# 注：此测试需要连接真实 MySQL，或使用 mock
# 在 CI 环境中可能需要跳过
@pytest.mark.skip(reason="Requires real MySQL instance")
def test_create_tenant_database() -> None:
    tenant = Tenant(
        db_name="test_tenant_001",
        db_host="localhost",
        db_port=3306,
        db_user="root",
        db_password_encrypted="root",
    )
    create_tenant_database(tenant)
    engine = get_tenant_engine(tenant)
    inspector = inspect(engine)
    # 新数据库应该可以连接
    assert inspector.default_schema_name is not None
