"""端到端集成测试 — 验证所有模块可以正常导入"""

def test_import_models() -> None:
    """验证所有数据模型可以正常导入"""
    from app.services.tenant.models import Tenant, User, Role, Permission
    from app.services.model.models import DataModel, DataField
    from app.services.ai.models import LLMProvider
    from app.services.ai.knowledge_base.models import KnowledgeBase, Document
    from app.services.ai.agent_engine.models import Agent, AgentConversation
    from app.services.ai.memory.models import AgentMemory
    from app.services.ai.workflow.models import Workflow, WorkflowInstance
    assert True  # All imports succeeded


def test_import_services() -> None:
    """验证所有服务层可以正常导入"""
    from app.services.tenant.service import TenantService
    from app.services.model.service import ModelService
    from app.services.ai.service import AIService
    from app.services.ai.knowledge_base.service import KnowledgeBaseService
    from app.services.ai.agent_engine.service import AgentService
    from app.services.ai.memory.service import MemoryService
    from app.services.ai.workflow.service import WorkflowService
    assert True


def test_import_routes() -> None:
    """验证所有 API 路由可以正常导入"""
    from app.api.v1.tenant import router as tenant_router
    from app.api.v1.model import router as model_router
    from app.api.v1.llm import router as llm_router
    from app.api.v1.knowledge_base import router as kb_router
    from app.api.v1.agent import router as agent_router
    from app.api.v1.workflow import router as workflow_router
    assert True


def test_render_template_known_cross_module() -> None:
    """模板渲染跨模块验证"""
    from app.services.ai.workflow.template import render_template
    context = {"outputs": {"llm_1": {"text": "hello", "score": 0.95}}}
    result = render_template("{{llm_1.output.text}}", context)
    assert result == "hello"

    # Nested field access
    result = render_template("score: {{llm_1.output.score}}", context)
    assert result == "score: 0.95"
