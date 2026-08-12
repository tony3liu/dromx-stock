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

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage

from dromx.tools.registry import registry
from dromx.assistant.intents import classify_intent_llm, get_default_tools
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
        # 1. 意图识别（LLM 分类，失败回退关键词匹配）
        intent = classify_intent_llm(question, self.llm)
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

工具使用纪律（必须遵守）：
- 涉及你不确定的事实——某公司在哪个市场上市、股票代码、最新事件、当前价格——
  必须先调用 resolve_ticker 或 web_search 核实，禁止凭记忆断言。
  你的训练知识有截止日期，新公司上市/退市/改名你都不知道。
- 用户提到公司名而非代码时，先用 resolve_ticker 确认代码和交易所，再调数据工具。
- 信息确实无法通过工具获取时，诚实说明，不要编造看似合理的结果。
- 一次搜索解决一个疑问，搜索后用 web_read 读最相关的结果页面。

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
        final = ""
        for event in self._react_loop_events(messages, tools, intent):
            if event.get("type") == "delta":
                final += event.get("text", "")
            elif event.get("type") == "final":
                final = event.get("text", final)
        return final or "抱歉，我没有生成有效回答。"

    def _react_loop_events(
        self,
        messages: List[BaseMessage],
        tools: List[dict],
        intent: str,
        cancel_event=None,
    ):
        """ReAct 循环（生成器版）：逐步产出 delta / tool_start / final 事件

        - 每轮用 ``.stream()`` 调 LLM：content 增量直接产出（真流式）
        - 若本轮带 tool_calls：执行工具后继续循环
        - 若 LLM 不支持 .stream：回退 .invoke，一次性产出
        - cancel_event（threading.Event）置位时在协作点尽快中止
        """

        def _cancelled() -> bool:
            return bool(cancel_event is not None and cancel_event.is_set())

        llm_with_tools = self.llm.bind_tools(tools) if hasattr(self.llm, 'bind_tools') else self.llm
        can_stream = hasattr(llm_with_tools, "stream")

        for iteration in range(self.max_iterations):
            if _cancelled():
                yield {"type": "cancelled", "text": "已停止"}
                return
            logger.info("Assistant iteration %d/%d", iteration + 1, self.max_iterations)

            response = None
            if can_stream:
                try:
                    full = None
                    for chunk in llm_with_tools.stream(messages):
                        if _cancelled():
                            yield {"type": "cancelled", "text": "已停止"}
                            return
                        full = chunk if full is None else full + chunk
                        text = getattr(chunk, "content", "")
                        if isinstance(text, list):  # 兼容多模态 content block
                            text = "".join(
                                b.get("text", "") for b in text if isinstance(b, dict)
                            )
                        if text:
                            yield {"type": "delta", "text": text}
                    response = full
                except Exception as e:
                    logger.error("LLM stream failed: %s", e)
                    yield {"type": "error", "message": str(e)}
                    return
            else:
                try:
                    response = llm_with_tools.invoke(messages)
                except Exception as e:
                    logger.error("LLM invoke failed: %s", e)
                    yield {"type": "error", "message": str(e)}
                    return
                content = getattr(response, "content", "") or ""
                if content:
                    yield {"type": "delta", "text": content}

            if response is None:
                yield {"type": "error", "message": "LLM 未返回任何内容"}
                return

            # 检查是否有工具调用
            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                content = getattr(response, "content", "") or ""
                if isinstance(content, list):
                    content = "".join(
                        b.get("text", "") for b in content if isinstance(b, dict)
                    )
                yield {"type": "final", "text": content}
                return

            # 有工具调用：delta 流里 content 通常为空，执行工具后继续
            messages.append(response)
            for tool_call in tool_calls:
                if _cancelled():
                    yield {"type": "cancelled", "text": "已停止"}
                    return
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "")

                logger.info("Calling tool: %s with args: %s", tool_name, tool_args)
                yield {"type": "tool_start", "tool": tool_name, "args": tool_args}

                # dispatch 是阻塞调用；深研工具经 on_progress 回调上报 section 进度（P-C）。
                # 生成器不能从回调里 yield，故在工作线程跑 dispatch，回调把进度事件塞进队列，
                # 主线程边等结果边 drain 队列 yield（deep_start/deep_section）。cancel_event 照旧透传。
                import queue as _queue
                import threading as _threading

                _progress: "_queue.Queue" = _queue.Queue()
                _box: dict = {}

                def _on_progress(evt):
                    _progress.put(evt)

                def _worker():
                    try:
                        _box["result"] = registry.dispatch(
                            tool_name, tool_args, llm=self.llm,
                            cancel_event=cancel_event, on_progress=_on_progress,
                        )
                    except Exception as e:  # noqa: BLE001
                        _box["error"] = e
                    finally:
                        _progress.put(None)  # 结束哨兵

                _t = _threading.Thread(target=_worker, daemon=True)
                _t.start()
                while True:
                    evt = _progress.get()
                    if evt is None:
                        break
                    yield evt  # deep_start / deep_section 透传给上层 SSE
                _t.join()
                if "error" in _box:
                    raise _box["error"]
                result = _box.get("result", "")
                if _cancelled():
                    yield {"type": "cancelled", "text": "已停止"}
                    return
                yield {"type": "tool_end", "tool": tool_name}

                # 工具结果必须以 ToolMessage 回传（带 tool_call_id），
                # 否则 OpenAI 兼容接口会报 400: assistant message with
                # 'tool_calls' must be followed by tool messages
                messages.append(ToolMessage(
                    content=result,
                    tool_call_id=tool_id or tool_name,
                    name=tool_name,
                ))

        # 达到最大迭代次数
        logger.warning("Assistant reached max iterations: %d", self.max_iterations)
        yield {"type": "final", "text": "抱歉，我思考了太久，请简化你的问题再试一次。"}

    def answer_stream(
        self,
        question: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cancel_event=None,
    ):
        """流式回答：产出 status / delta / tool_start / tool_end / final / error 事件

        cancel_event（threading.Event）置位时在协作点尽快中止（前端断开连接）。"""
        # 1. 意图识别（LLM 分类，失败回退关键词匹配）
        yield {"type": "status", "text": "识别意图…"}
        intent = classify_intent_llm(question, self.llm)
        logger.info("Assistant intent: %s for question: %s", intent, question[:100])
        yield {"type": "status", "text": f"意图：{intent}"}

        # 2. 加载对话历史
        history: List[BaseMessage] = []
        if session_id:
            history = self.conversation.get_history(session_id)

        # 3. 获取工具
        tool_names = get_default_tools(intent)
        tools = registry.get_definitions(tool_names)

        # 4. 构建消息
        messages: List[BaseMessage] = [SystemMessage(content=self._build_system_prompt(intent, context))]
        messages.extend(history)
        messages.append(HumanMessage(content=question))

        # 5. ReAct 循环（流式）
        final_text = ""
        cancelled = False
        for event in self._react_loop_events(messages, tools, intent, cancel_event=cancel_event):
            if event.get("type") == "final":
                final_text = event.get("text", final_text)
            elif event.get("type") == "cancelled":
                cancelled = True
            yield event

        # 6. 保存对话历史（被取消的不写入，避免半截回答污染上下文）
        if session_id and final_text and not cancelled:
            self.conversation.add_message(session_id, "user", question)
            self.conversation.add_message(session_id, "assistant", final_text)

    def get_supported_intents(self) -> List[str]:
        """获取支持的意图列表"""
        from dromx.assistant.intents import INTENT_DEFAULT_TOOLS
        return list(INTENT_DEFAULT_TOOLS.keys())
