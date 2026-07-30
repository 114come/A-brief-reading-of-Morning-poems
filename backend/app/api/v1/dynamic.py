import logging

from fastapi import APIRouter, FastAPI
from sqlalchemy.orm import Session

from app.core.database import master_engine
from app.core.dependencies import DbDep, UserDep
from app.core.response import UnifiedResponse
from app.services.model.generator import (
    generate_crud_router,
    generate_pydantic_schemas,
    generate_sqlalchemy_model,
)
from app.services.model.models import DataModel
from app.services.model.repository import DataModelRepository

router = APIRouter(prefix="/dynamic", tags=["动态数据"])
logger = logging.getLogger(__name__)


@router.get("/models")
def list_dynamic_models(
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    """列出当前租户下所有可用的动态模型定义（用于 ToolCall 配置 UI）"""
    repo = DataModelRepository(db)
    models = repo.list_by_tenant(current_user.tenant_id)
    return UnifiedResponse.success(
        data=[
            {
                "id": m.id,
                "name": m.name,
                "table_name": m.table_name,
                "fields": [
                    {"name": f.name, "field_type": f.field_type} for f in m.fields
                ],
            }
            for m in models
        ]
    )


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
