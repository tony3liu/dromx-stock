"""Intent definitions — 意图分类定义

定义投研助手支持的意图类型和关键词。
"""

from __future__ import annotations

# 意图分类：关键词 → 意图
INTENT_KEYWORDS: dict[str, list[str]] = {
    "deep_analysis": ["分析", "研究", "看看", "评估", "调研", "深度"],
    "sector_question": ["板块", "行业", "领域", "赛道", "见底", "见顶", "趋势"],
    "capital_rotation": ["轮动", "资金流向", "切换", "调仓", "换仓", "资金"],
    "my_operation": ["我的", "操作", "买", "卖", "持仓", "成本", "补救", "对不对"],
    "backtest": ["回测", "历史", "复盘", "表现"],
    "screener": ["筛选", "选股", "找股票", "筛选器"],
    "hedge": ["对冲", "风险", "保护", "避险"],
    "general_qa": [],  # 默认意图
}

# 意图 → 默认工具（兜底）
INTENT_DEFAULT_TOOLS: dict[str, list[str]] = {
    "deep_analysis": ["run_deep_analysis"],
    "sector_question": ["get_sector_quote", "get_capital_flow", "get_sector_news"],
    "capital_rotation": ["get_capital_flow", "get_sector_quote", "get_macro_data"],
    "my_operation": ["get_my_position", "get_stock_data", "analyze_my_operation"],
    "backtest": ["run_backtest"],
    "screener": ["run_screener"],
    "hedge": ["run_hedge_analysis"],
    "general_qa": ["web_search"],
}


def classify_intent(question: str) -> str:
    """意图识别：根据关键词判断问题类型

    简单的关键词匹配，后续可以升级为 LLM 分类。
    """
    q = question.lower()

    # 按优先级匹配（my_operation 优先于 general_qa）
    priority = [
        "my_operation",
        "deep_analysis",
        "sector_question",
        "capital_rotation",
        "backtest",
        "screener",
        "hedge",
    ]

    for intent in priority:
        keywords = INTENT_KEYWORDS.get(intent, [])
        if any(kw in q for kw in keywords):
            return intent

    return "general_qa"


def get_default_tools(intent: str) -> list[str]:
    """获取意图的默认工具"""
    return INTENT_DEFAULT_TOOLS.get(intent, INTENT_DEFAULT_TOOLS["general_qa"])
