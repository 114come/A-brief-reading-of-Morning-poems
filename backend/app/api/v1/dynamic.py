import logging

from fastapi import APIRouter, FastAPI
from sqlalchemy.orm import Session

from app.core.database import master_engine
from app.services.model.generator import (
    generate_crud_router,
    generate_pydantic_schemas,
    generate_sqlalchemy_model,
)
from app.services.model.models import DataModel

router = APIRouter(prefix="/dynamic", tags=["动态数据"])
logger = logging.getLogger(__name__)


def register_dynamic_routers(app: FastAPI) -> None:
    """注册所有已发布 DataModel 的动态 CRUD 路由"""
    db = Session(bind=master_engine)
    try:
        models = db.query(DataModel).filter(DataModel.status == "published").all()
        for model_def in models:
            try:
                DynamicModel = generate_sqlalchemy_model(model_def)
                CreateSchema, ResponseSchema = generate_pydantic_schemas(model_def)
                router = generate_crud_router(
                    model_def, DynamicModel, CreateSchema, ResponseSchema
                )
                app.include_router(router, prefix="/api/v1")
            except Exception:
                # 单个模型注册失败不应阻止其他模型
                logger.exception(
                    "Failed to register dynamic router for %s", model_def.table_name
                )
    finally:
        db.close()
