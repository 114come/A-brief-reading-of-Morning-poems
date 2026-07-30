from typing import Any

from sqlalchemy.orm import Session

from app.services.ai.workflow.models import Workflow, WorkflowInstance


class WorkflowRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs: Any) -> Workflow:
        workflow = Workflow(**kwargs)
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def get_by_id(self, workflow_id: int) -> Workflow | None:
        return self.db.query(Workflow).filter(Workflow.id == workflow_id).first()

    def list_by_tenant(self, tenant_id: int) -> list[Workflow]:
        return (
            self.db.query(Workflow)
            .filter(Workflow.tenant_id == tenant_id)
            .order_by(Workflow.created_at.desc())
            .all()
        )

    def update(self, workflow_id: int, **kwargs: Any) -> Workflow | None:
        workflow = self.get_by_id(workflow_id)
        if not workflow:
            return None
        for key, value in kwargs.items():
            if hasattr(workflow, key):
                setattr(workflow, key, value)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def delete(self, workflow_id: int) -> bool:
        workflow = self.get_by_id(workflow_id)
        if not workflow:
            return False
        self.db.delete(workflow)
        self.db.commit()
        return True


class WorkflowInstanceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs: Any) -> WorkflowInstance:
        instance = WorkflowInstance(**kwargs)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def get_by_id(self, instance_id: int) -> WorkflowInstance | None:
        return self.db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()

    def list_by_workflow(self, workflow_id: int) -> list[WorkflowInstance]:
        return (
            self.db.query(WorkflowInstance)
            .filter(WorkflowInstance.workflow_id == workflow_id)
            .order_by(WorkflowInstance.created_at.desc())
            .all()
        )

    def update_status(self, instance_id: int, status: str) -> WorkflowInstance | None:
        instance = self.get_by_id(instance_id)
        if not instance:
            return None
        instance.status = status
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def update_context(
        self, instance_id: int, context: dict[str, Any]
    ) -> WorkflowInstance | None:
        instance = self.get_by_id(instance_id)
        if not instance:
            return None
        import json
        instance.context = json.dumps(context, ensure_ascii=False)
        self.db.commit()
        self.db.refresh(instance)
        return instance
