"""Intent definitions — 意图分类定义

定义投研助手支持的意图类型和关键词。
"""

from __future__ import annotations

# 意图分类：关键词 → 意图
INTENT_KEYWORDS: dict[str, list[str]] = {
    "deep_analysis": ["分析", "研究", "看看", "评估", "调研", "深度"],
    "sector_question": ["板块", "行业", "领域", "赛道", "见底", "见顶", "趋势"],
    "capital_rotation": ["轮动", "资金流向", "切换", "调仓", "换仓", "资金", "宏观", "经济", "周期", "利率", "通胀", "滞胀", "衰退", "过热", "复苏", "加息", "降息"],
    "my_operation": ["我的", "操作", "买", "卖", "持仓", "成本", "补救", "对不对"],
    "backtest": ["回测", "历史", "复盘", "表现"],
    "screener": ["筛选", "选股", "找股票", "筛选器"],
    "hedge": ["对冲", "风险", "保护", "避险"],
    "general_qa": [],  # 默认意图
}

# 意图 → 默认工具（兜底）
INTENT_DEFAULT_TOOLS: dict[str, list[str]] = {
    "deep_analysis": ["run_deep_analysis"],
    "sector_question": ["list_sectors", "get_sector_quote", "get_capital_flow", "get_sector_news"],
    "capital_rotation": ["list_sectors", "get_capital_flow", "get_sector_quote", "get_macro_data", "get_macro_cycle"],
    "my_operation": ["get_my_position", "get_stock_data", "analyze_my_operation"],
    "backtest": ["run_backtest"],
    "screener": ["run_screener"],
    "hedge": ["run_hedge_analysis"],
    "general_qa": ["web_search"],
}


def classify_intent(question: str) -> str:
    """意图识别：根据关键词判断问题类型

    简单的关键词匹配，作为 LLM 分类失败时的兜底。
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


# 意图说明（用于 LLM 分类 prompt）
INTENT_DESCRIPTIONS: dict[str, str] = {
    "deep_analysis": "深度分析某一只股票（基本面/技术面/新闻/情绪综合研究）",
    "sector_question": "板块/行业/赛道问题（如某板块是否见底、见顶、趋势如何）",
    "capital_rotation": "资金流向与板块轮动（如资金会轮动到哪些板块、如何调仓）；宏观经济周期判断（如现在处于什么经济周期、宏观环境如何）",
    "my_operation": "用户自己的持仓或操作复盘（如我的操作对不对、怎么补救、成本价）",
    "backtest": "策略回测或历史表现复盘",
    "screener": "条件选股/筛选股票",
    "hedge": "风险对冲/避险方案",
    "general_qa": "以上都不匹配的通用问题",
}


def classify_intent_llm(question: str, llm) -> str:
    """LLM 意图分类：优先用大模型判断，失败时回退关键词匹配"""
    try:
        options = "\n".join(
            f"- {name}: {desc}" for name, desc in INTENT_DESCRIPTIONS.items()
        )
        prompt = (
            "你是意图分类器。把用户问题归入下列唯一一个意图，只输出意图名称，不要输出任何其他内容。\n"
            f"{options}\n\n用户问题：{question}\n意图："
        )
        resp = llm.invoke(prompt)
        text = getattr(resp, "content", None) or str(resp)
        text = text.strip().lower()
        # 精确或包含匹配（容忍模型输出前后缀）
        for name in INTENT_DESCRIPTIONS:
            if name in text:
                return name
    except Exception:
        pass
    return classify_intent(question)


# 全意图常驻工具（Hermes 思路：核实/查询类工具始终可用，由 LLM 自主决定何时调用）
UNIVERSAL_TOOLS: list[str] = [
    "resolve_ticker", "web_search", "web_read",
    "get_commodity_quote", "get_commodity_kline", "get_economic_calendar",
]


def get_default_tools(intent: str) -> list[str]:
    """获取意图的默认工具：意图专属工具 + 全意图常驻核实工具"""
    specific = INTENT_DEFAULT_TOOLS.get(intent, INTENT_DEFAULT_TOOLS["general_qa"])
    return list(dict.fromkeys([*specific, *UNIVERSAL_TOOLS]))
