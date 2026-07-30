import logging
from typing import Any

from fastapi import APIRouter

from app.core.dependencies import DbDep, UserDep
from app.core.exceptions import ValidationException
from app.core.response import UnifiedResponse
from app.services.ai.workflow.schemas import (
    ApproveRequest,
    WorkflowCreate,
    WorkflowInstanceResponse,
    WorkflowResponse,
    WorkflowRunRequest,
    WorkflowUpdate,
)
from app.services.ai.workflow.service import WorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["工作流"])


# ── Workflow CRUD ────────────────────────────────────────────


@router.post("/", response_model=UnifiedResponse[Any])
def create_workflow(
    data: WorkflowCreate,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = WorkflowService(db)
    wf = service.create_workflow(tenant_id=current_user.tenant_id, data=data)
    return UnifiedResponse.success(
        data=WorkflowResponse.model_validate(wf).model_dump()
    )


@router.get("/", response_model=UnifiedResponse[Any])
def list_workflows(
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = WorkflowService(db)
    workflows = service.list_workflows(tenant_id=current_user.tenant_id)
    return UnifiedResponse.success(
        data=[WorkflowResponse.model_validate(w).model_dump() for w in workflows]
    )


# ── Instance Routes (must be before /{wf_id} to avoid path conflicts) ──


@router.get("/instances/{inst_id}", response_model=UnifiedResponse[Any])
def get_instance(
    inst_id: int,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = WorkflowService(db)
    instance = service.get_instance(inst_id)
    if not instance or instance.tenant_id != current_user.tenant_id:
        raise ValidationException("工作流实例不存在")
    return UnifiedResponse.success(
        data=WorkflowInstanceResponse.model_validate(instance).model_dump()
    )


@router.post("/instances/{inst_id}/approve", response_model=UnifiedResponse[Any])
async def approve_instance(
    inst_id: int,
    req: ApproveRequest,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = WorkflowService(db)
    try:
        instance = await service.approve_instance(
            tenant_id=current_user.tenant_id,
            instance_id=inst_id,
            approved=req.approved,
            comment=req.comment,
        )
    except ValueError as e:
        raise ValidationException(str(e))
    return UnifiedResponse.success(
        data=WorkflowInstanceResponse.model_validate(instance).model_dump()
    )


# ── Workflow Detail Routes ───────────────────────────────────


@router.get("/{wf_id}", response_model=UnifiedResponse[Any])
def get_workflow(
    wf_id: int,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = WorkflowService(db)
    wf = service.get_workflow(tenant_id=current_user.tenant_id, workflow_id=wf_id)
    if not wf:
        raise ValidationException("工作流不存在")
    return UnifiedResponse.success(
        data=WorkflowResponse.model_validate(wf).model_dump()
    )


@router.put("/{wf_id}", response_model=UnifiedResponse[Any])
def update_workflow(
    wf_id: int,
    data: WorkflowUpdate,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = WorkflowService(db)
    wf = service.update_workflow(
        tenant_id=current_user.tenant_id, workflow_id=wf_id, data=data
    )
    if not wf:
        raise ValidationException("工作流不存在")
    return UnifiedResponse.success(
        data=WorkflowResponse.model_validate(wf).model_dump()
    )


@router.delete("/{wf_id}", response_model=UnifiedResponse[Any])
def delete_workflow(
    wf_id: int,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = WorkflowService(db)
    if not service.delete_workflow(tenant_id=current_user.tenant_id, workflow_id=wf_id):
        raise ValidationException("工作流不存在")
    return UnifiedResponse.success(message="工作流已删除")


@router.post("/{wf_id}/run", response_model=UnifiedResponse[Any])
async def run_workflow(
    wf_id: int,
    req: WorkflowRunRequest,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = WorkflowService(db)
    try:
        instance = await service.run_workflow(
            tenant_id=current_user.tenant_id,
            workflow_id=wf_id,
            triggered_by=current_user.id,
            input_data=req.input,
        )
    except ValueError as e:
        raise ValidationException(str(e))
    return UnifiedResponse.success(
        data=WorkflowInstanceResponse.model_validate(instance).model_dump()
    )


@router.get("/{wf_id}/instances", response_model=UnifiedResponse[Any])
def list_instances(
    wf_id: int,
    current_user: UserDep,
    db: DbDep,
) -> UnifiedResponse:
    service = WorkflowService(db)
    wf = service.get_workflow(tenant_id=current_user.tenant_id, workflow_id=wf_id)
    if not wf:
        raise ValidationException("工作流不存在")
    instances = service.list_instances(workflow_id=wf_id)
    return UnifiedResponse.success(
        data=[WorkflowInstanceResponse.model_validate(inst).model_dump() for inst in instances]
    )
