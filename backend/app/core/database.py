from collections.abc import Generator
from typing import TYPE_CHECKING

import re

from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.engine import Engine

from app.core.config import settings

if TYPE_CHECKING:
    from app.services.tenant.models import Tenant


# MySQL identifier rules: start with letter, then letters/digits/underscores, max 64 chars
_MYSQL_IDENTIFIER_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")


def _validate_db_name(db_name: str) -> None:
    if not _MYSQL_IDENTIFIER_RE.match(db_name):
        raise ValueError(f"Invalid database name: {db_name!r}")


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


_tenant_engine_cache: dict[int, Engine] = {}


def get_cached_tenant_engine(tenant: "Tenant") -> Engine:
    """获取租户数据库引擎（带缓存，避免每请求创建新连接池）"""
    if tenant.id not in _tenant_engine_cache:
        _tenant_engine_cache[tenant.id] = get_tenant_engine(tenant)
    return _tenant_engine_cache[tenant.id]


def get_tenant_engine(tenant: "Tenant") -> Engine:
    """获取租户数据库的 SQLAlchemy 引擎"""
    # TODO: decrypt password
    password = tenant.db_password_encrypted or settings.MASTER_DB_PASSWORD
    url = URL.create(
        drivername="mysql+pymysql",
        username=tenant.db_user,
        password=password,
        host=tenant.db_host,
        port=tenant.db_port,
        database=tenant.db_name,
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


def create_tenant_database(tenant: "Tenant") -> None:
    """在 MySQL 中创建租户独立数据库"""
    _validate_db_name(tenant.db_name)
    password = tenant.db_password_encrypted or settings.MASTER_DB_PASSWORD
    # 连接 mysql 系统库来执行 CREATE DATABASE
    admin_url = URL.create(
        drivername="mysql+pymysql",
        username=tenant.db_user,
        password=password,
        host=tenant.db_host,
        port=tenant.db_port,
        database="mysql",
    )
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS {tenant.db_name} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
    admin_engine.dispose()
