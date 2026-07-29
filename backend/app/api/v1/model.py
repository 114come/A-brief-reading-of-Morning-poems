from typing import Any

from fastapi import APIRouter, Request

from app.core.dependencies import DbDep, UserDep
from app.core.exceptions import ForbiddenException, ValidationException
from app.core.response import UnifiedResponse
from app.services.model.schemas import DataModelCreate
from app.services.model.service import ModelService

router = APIRouter(prefix="/models", tags=["数据模型"])


@router.post("/", response_model=UnifiedResponse[Any])
def create_model(
    data: DataModelCreate,
    db: DbDep,
    current_user: UserDep,
) -> UnifiedResponse[Any]:
    service = ModelService(db)
    model = service.create_model(tenant_id=current_user.tenant_id, data=data)
    return UnifiedResponse.success(
        data={"id": model.id, "name": model.name, "table_name": model.table_name}
    )


@router.get("/", response_model=UnifiedResponse[Any])
def list_models(
    db: DbDep,
    current_user: UserDep,
    skip: int = 0,
    limit: int = 100,
) -> UnifiedResponse[Any]:
    service = ModelService(db)
    models = service.model_repo.list_by_tenant(current_user.tenant_id, skip, limit)
    return UnifiedResponse.success(
        data=[
            {"id": m.id, "name": m.name, "table_name": m.table_name, "status": m.status}
            for m in models
        ]
    )


@router.post("/{model_id}/publish", response_model=UnifiedResponse[Any])
def publish_model(
    model_id: int,
    request: Request,
    db: DbDep,
    current_user: UserDep,
) -> UnifiedResponse[Any]:
    from app.api.v1.dynamic import register_dynamic_routers
    from app.services.tenant.service import TenantService

    service = ModelService(db)
    tenant_service = TenantService(db)
    tenant = tenant_service.tenant_repo.get_by_id(current_user.tenant_id)
    if not tenant:
        raise ValidationException("租户不存在")

    model = service.model_repo.get_by_id(model_id)
    if not model:
        raise ValidationException("模型不存在")
    if model.tenant_id != tenant.id:
        raise ForbiddenException("无权操作此模型")

    model = service.publish_model(model_id, tenant)

    # Re-register dynamic routers so the new table is immediately accessible
    register_dynamic_routers(request.app)

    return UnifiedResponse.success(
        data={"id": model.id, "status": model.status, "table_name": model.table_name}
    )
