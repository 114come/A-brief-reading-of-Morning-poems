from app.services.ai.agent_engine.tools.base import BaseTool
from app.services.ai.agent_engine.tools.calculator import CalculatorTool
from app.services.ai.agent_engine.tools.get_time import GetTimeTool
from app.services.ai.agent_engine.tools.registry import ToolRegistry

# 注册无状态工具（全局单例，可在线程/请求间共享）
ToolRegistry.register(CalculatorTool())
ToolRegistry.register(GetTimeTool())

# LLMTool 和 KBTool 需要运行时依赖注入，不在模块加载时注册

__all__ = [
    "BaseTool",
    "CalculatorTool",
    "GetTimeTool",
    "ToolRegistry",
]
