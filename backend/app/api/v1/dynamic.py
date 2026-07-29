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


def register_dynamic_routers(app: FastAPI) -> None:
    """在 FastAPI 应用启动后，注册所有已发布模型的 CRUD 路由"""
    db = Session(bind=master_engine)
    try:
        published_models = db.query(DataModel).filter_by(status="published").all()
        for model_def in published_models:
            DynamicModel = generate_sqlalchemy_model(model_def)
            CreateSchema, ResponseSchema = generate_pydantic_schemas(model_def)
            crud_router = generate_crud_router(
                model_def, DynamicModel, CreateSchema, ResponseSchema
            )
            app.include_router(crud_router, prefix="/api/v1")
    finally:
        db.close()
