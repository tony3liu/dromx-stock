"""Monitor tools — 监控工具（预留）

自注册工具：监控规则、告警等。
"""

from __future__ import annotations

import logging

from dromx.tools.registry import registry, tool_error, tool_result

logger = logging.getLogger(__name__)


def _create_monitor_rule(args: dict, llm=None, config=None) -> str:
    """创建监控规则"""
    # TODO: 实现监控规则创建
    return tool_error("Monitor rule creation not implemented yet")


def _get_alerts(args: dict, llm=None, config=None) -> str:
    """获取告警"""
    # TODO: 实现告警查询
    return tool_error("Alerts query not implemented yet")


# 注册工具（预留）
# registry.register(
#     name="create_monitor_rule",
#     toolset="monitor",
#     schema={
#         "description": "创建监控规则。当用户需要"监控这只股票"或"设置提醒"时调用。",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "ticker": {"type": "string", "description": "股票代码"},
#                 "condition": {"type": "string", "description": "监控条件"},
#             },
#             "required": ["ticker", "condition"],
#         },
#     },
#     handler=_create_monitor_rule,
#     description="创建监控规则",
# )

# registry.register(
#     name="get_alerts",
#     toolset="monitor",
#     schema={
#         "description": "获取告警。当用户问"有什么提醒"或"最近有什么告警"时调用。",
#         "parameters": {"type": "object", "properties": {}},
#     },
#     handler=_get_alerts,
#     description="获取告警",
# )
