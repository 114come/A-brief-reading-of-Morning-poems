from collections.abc import Generator
from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

if TYPE_CHECKING:
    from app.services.tenant.models import Tenant


class Base(DeclarativeBase):
    pass


# 主库引擎（租户元数据）
master_engine = create_engine(
    settings.MASTER_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.APP_ENV == "development",
)

MasterSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=master_engine,
)


def get_master_db() -> Generator[Session, None, None]:
    """FastAPI Dependency: 获取主库 session"""
    db = MasterSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_tenant_engine(tenant: "Tenant") -> Any:
    """获取租户数据库的 SQLAlchemy 引擎"""
    # TODO: decrypt password
    password = tenant.db_password_encrypted or settings.MASTER_DB_PASSWORD
    url = (
        f"mysql+pymysql://{tenant.db_user}:{password}"
        f"@{tenant.db_host}:{tenant.db_port}/{tenant.db_name}"
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def create_tenant_database(tenant: "Tenant") -> None:
    """在 MySQL 中创建租户独立数据库"""
    password = tenant.db_password_encrypted or settings.MASTER_DB_PASSWORD
    # 连接 mysql 系统库来执行 CREATE DATABASE
    admin_url = (
        f"mysql+pymysql://{tenant.db_user}:{password}"
        f"@{tenant.db_host}:{tenant.db_port}/mysql"
    )
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {tenant.db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
    admin_engine.dispose()
