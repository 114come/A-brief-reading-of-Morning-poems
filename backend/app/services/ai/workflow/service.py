import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.services.ai.knowledge_base.service import KnowledgeBaseService
from app.services.ai.service import AIService
from app.services.ai.workflow.executor import WorkflowExecutor
from app.services.ai.workflow.models import Workflow, WorkflowInstance
from app.services.ai.workflow.repository import (
    WorkflowInstanceRepository,
    WorkflowRepository,
)
from app.services.ai.workflow.schemas import WorkflowCreate, WorkflowUpdate

logger = logging.getLogger(__name__)


class WorkflowService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.wf_repo = WorkflowRepository(db)
        self.inst_repo = WorkflowInstanceRepository(db)
        self.ai_service = AIService(db)
        self.kb_service = KnowledgeBaseService(db)

    @property
    def _services(self) -> dict[str, Any]:
        return {
            "ai_service": self.ai_service,
            "kb_service": self.kb_service,
        }

    # ── Workflow CRUD ──────────────────────────────────────────

    def create_workflow(self, tenant_id: int, data: WorkflowCreate) -> Workflow:
        return self.wf_repo.create(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            definition=json.dumps(data.definition, ensure_ascii=False),
        )

    def get_workflow(
        self, tenant_id: int, workflow_id: int
    ) -> Workflow | None:
        wf = self.wf_repo.get_by_id(workflow_id)
        if wf and wf.tenant_id != tenant_id:
            return None
        return wf

    def list_workflows(self, tenant_id: int) -> list[Workflow]:
        return self.wf_repo.list_by_tenant(tenant_id)

    def update_workflow(
        self, tenant_id: int, workflow_id: int, data: WorkflowUpdate
    ) -> Workflow | None:
        wf = self.wf_repo.get_by_id(workflow_id)
        if not wf or wf.tenant_id != tenant_id:
            return None
        kwargs: dict[str, Any] = {}
        if data.name is not None:
            kwargs["name"] = data.name
        if data.description is not None:
            kwargs["description"] = data.description
        if data.definition is not None:
            kwargs["definition"] = json.dumps(data.definition, ensure_ascii=False)
        if data.is_active is not None:
            kwargs["is_active"] = data.is_active
        return self.wf_repo.update(workflow_id, **kwargs)

    def delete_workflow(self, tenant_id: int, workflow_id: int) -> bool:
        wf = self.wf_repo.get_by_id(workflow_id)
        if not wf or wf.tenant_id != tenant_id:
            return False
        return self.wf_repo.delete(workflow_id)

    # ── Workflow Execution ─────────────────────────────────────

    async def run_workflow(
        self,
        tenant_id: int,
        workflow_id: int,
        triggered_by: int,
        input_data: dict | None = None,
    ) -> WorkflowInstance:
        wf = self.wf_repo.get_by_id(workflow_id)
        if not wf or wf.tenant_id != tenant_id:
            raise ValueError("Workflow not found")

        instance = self.inst_repo.create(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            triggered_by=triggered_by,
            status="pending",
            context="{}",
        )

        executor = WorkflowExecutor(instance, self._services)
        await executor.execute(input_data)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    async def approve_instance(
        self,
        tenant_id: int,
        instance_id: int,
        approved: bool,
        comment: str | None = None,
    ) -> WorkflowInstance:
        instance = self.inst_repo.get_by_id(instance_id)
        if not instance or instance.tenant_id != tenant_id:
            raise ValueError("Instance not found")

        executor = WorkflowExecutor(instance, self._services)
        await executor.resume_after_review(approved, comment)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    # ── Instance Queries ───────────────────────────────────────

    def list_instances(self, workflow_id: int) -> list[WorkflowInstance]:
        return self.inst_repo.list_by_workflow(workflow_id)

    def get_instance(self, instance_id: int) -> WorkflowInstance | None:
        return self.inst_repo.get_by_id(instance_id)
