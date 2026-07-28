from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


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
