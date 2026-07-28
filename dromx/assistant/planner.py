"""Assistant Planner — 投研助手核心

意图识别 → 工具规划 → ReAct 循环 → 回答

参考 Hermes Agent 的 conversation loop 设计：
- model call → tool dispatch → observe → repeat
- iteration budget 控制循环次数
- 错误统一处理
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from dromx.tools.registry import registry
from dromx.assistant.intents import classify_intent, get_default_tools
from dromx.assistant.conversation import ConversationManager

logger = logging.getLogger(__name__)


class AssistantPlanner:
    """投研助手：理解意图 → 规划工具 → 执行 → 回答"""

    def __init__(
        self,
        llm: Any,
        max_iterations: int = 10,
        conversation_manager: Optional[ConversationManager] = None,
    ):
        self.llm = llm
        self.max_iterations = max_iterations
        self.conversation = conversation_manager or ConversationManager()

    def answer(
        self,
        question: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """回答用户问题

        Args:
            question: 用户问题
            session_id: 会话 ID（用于多轮对话）
            context: 额外上下文（如 ticker, holdings 等）

        Returns:
            回答文本
        """
        # 1. 意图识别
        intent = classify_intent(question)
        logger.info("Assistant intent: %s for question: %s", intent, question[:100])

        # 2. 加载对话历史
        history: List[BaseMessage] = []
        if session_id:
            history = self.conversation.get_history(session_id)

        # 3. 获取工具
        tool_names = get_default_tools(intent)
        tools = registry.get_definitions(tool_names)
        logger.info("Assistant tools for intent %s: %s", intent, tool_names)

        # 4. 构建 system prompt
        system_prompt = self._build_system_prompt(intent, context)

        # 5. 构建消息
        messages: List[BaseMessage] = [SystemMessage(content=system_prompt)]
        messages.extend(history)
        messages.append(HumanMessage(content=question))

        # 6. ReAct 循环
        answer = self._react_loop(messages, tools, intent)

        # 7. 保存对话历史
        if session_id:
            self.conversation.add_message(session_id, "user", question)
            self.conversation.add_message(session_id, "assistant", answer)

        return answer

    def _build_system_prompt(self, intent: str, context: Optional[Dict[str, Any]] = None) -> str:
        """构建 system prompt"""
        prompt = """你是 DromX 投研助手，一个专业的股票投资研究助手。

你的职责：
1. 理解用户的投研问题（板块分析、资金流向、个股诊断、操作复盘等）
2. 调用合适的工具获取数据
3. 基于数据给出专业、客观、有依据的回答

回答原则：
- 用数据说话，不编造数字
- 明确标注数据来源和时间
- 给出明确的判断和依据
- 如果数据不足，明确告诉用户
- 用中文回答

"""
        # 添加意图特定指导
        intent_guides = {
            "deep_analysis": "用户需要深度分析一只股票。调用 run_deep_analysis 工具获取完整分析报告。",
            "sector_question": "用户关心板块/行业趋势。调用板块相关工具获取数据，分析板块是否见底/见顶。",
            "capital_rotation": "用户关心资金流向。调用资金流工具，分析资金会轮动到哪些板块。",
            "my_operation": "用户想复盘自己的操作。调用用户工具获取持仓信息，分析操作是否正确。",
            "backtest": "用户想回测历史表现。调用 run_backtest 工具。",
            "screener": "用户想筛选股票。调用 run_screener 工具。",
            "hedge": "用户想对冲风险。调用 run_hedge_analysis 工具。",
            "general_qa": "通用问题。基于你的知识回答，或调用 web_search 搜索最新信息。",
        }
        guide = intent_guides.get(intent, intent_guides["general_qa"])
        prompt += f"\n当前意图：{intent}\n{guide}\n"

        # 添加可用工具列表
        prompt += "\n可用工具：\n"
        prompt += registry.get_definitions_description() if hasattr(registry, 'get_definitions_description') else ""

        # 添加上下文
        if context:
            prompt += f"\n\n用户上下文：\n{json.dumps(context, ensure_ascii=False, indent=2)}"

        return prompt

    def _react_loop(
        self,
        messages: List[BaseMessage],
        tools: List[dict],
        intent: str,
    ) -> str:
        """ReAct 循环：model call → tool dispatch → observe → repeat"""

        # 绑定工具
        llm_with_tools = self.llm.bind_tools(tools) if hasattr(self.llm, 'bind_tools') else self.llm

        for iteration in range(self.max_iterations):
            logger.info("Assistant iteration %d/%d", iteration + 1, self.max_iterations)

            # 调用 LLM
            try:
                response = llm_with_tools.invoke(messages)
            except Exception as e:
                logger.error("LLM invoke failed: %s", e)
                return f"抱歉，我遇到了技术问题：{e}"

            # 检查是否有工具调用
            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                # 没有工具调用，直接返回回答
                content = getattr(response, "content", "")
                if content:
                    return content
                return "抱歉，我没有生成有效回答。"

            # 有工具调用，执行工具
            messages.append(response)

            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "")

                logger.info("Calling tool: %s with args: %s", tool_name, tool_args)

                # 执行工具
                result = registry.dispatch(tool_name, tool_args, llm=self.llm)

                # 添加工具结果到消息
                messages.append(AIMessage(
                    content=f"Tool {tool_name} result: {result}",
                    tool_calls=[{"id": tool_id, "name": tool_name, "args": tool_args}],
                ))

            # 继续循环，让 LLM 基于工具结果生成回答

        # 达到最大迭代次数，返回最后一次 LLM 的回答
        logger.warning("Assistant reached max iterations: %d", self.max_iterations)
        last_response = messages[-1] if messages else None
        content = getattr(last_response, "content", "") if last_response else ""
        return content or "抱歉，我思考了太久，请简化你的问题再试一次。"

    def get_supported_intents(self) -> List[str]:
        """获取支持的意图列表"""
        return list(get_default_tools.keys())
