from datetime import datetime, timezone, timedelta
from typing import Any

from app.services.ai.agent_engine.tools.base import BaseTool


class GetTimeTool(BaseTool):
    """时间查询工具：获取当前北京时间"""

    name = "get_time"
    description = "获取当前北京时间（时区 UTC+8）"
    parameters: dict[str, Any] = {}

    async def execute(self, **kwargs: Any) -> str:
        """返回当前北京时间字符串，格式为「YYYY-MM-DD HH:mm:ss (星期X)」。"""
        bj_tz = timezone(timedelta(hours=8))
        now = datetime.now(bj_tz)

        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday_str = weekdays[now.weekday()]

        return f"{now:%Y-%m-%d %H:%M:%S} ({weekday_str})"
