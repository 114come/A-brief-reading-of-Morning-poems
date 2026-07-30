from app.services.ai.workflow.nodes.base import BaseNode
from app.services.ai.workflow.nodes.condition_node import ConditionNode
from app.services.ai.workflow.nodes.human_node import HumanReviewNode
from app.services.ai.workflow.nodes.kb_node import KBNode
from app.services.ai.workflow.nodes.llm_node import LLMNode
from app.services.ai.workflow.nodes.start_end import EndNode, StartNode

NODE_REGISTRY: dict[str, BaseNode] = {
    "start": StartNode(),
    "end": EndNode(),
    "llm": LLMNode(),
    "kb": KBNode(),
    "condition": ConditionNode(),
    "human": HumanReviewNode(),
}

__all__ = [
    "BaseNode",
    "StartNode",
    "EndNode",
    "LLMNode",
    "KBNode",
    "ConditionNode",
    "HumanReviewNode",
    "NODE_REGISTRY",
]
