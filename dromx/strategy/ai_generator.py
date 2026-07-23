"""AI strategy generator — LLM-authored screening strategy code, safety-checked.

Adapted from TickFlow's ``ai_generator.py``. The AST safety check and literal
META extraction are ported verbatim (they are the security boundary and must
stay strict). The only substantive change is the LLM call: instead of TickFlow's
async ``ai_provider``, we take a synchronous LangChain-style LLM (the engine's
``quick_thinking_llm``), matching how the rest of DromX invokes models.

Flow: user prompt → guide + system prompt → llm.invoke → strip code fence →
AST safety check → literal META extraction → {code, meta, valid, error}.
"""
from __future__ import annotations

import ast
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

GUIDE_PATH = Path(__file__).resolve().parent / "ai_generator_prompt.md"

_SYSTEM_PREFIX = """你是量化选股策略设计专家。根据用户描述的需求，参考下方的《策略开发指南》生成一个完整的策略 Python 文件。

文件与范围铁律（不可违反）:
1. 只创建这一个策略文件：只生成一个 .py 文件，绝不创建多文件、不拆分模块、不跨文件引用。
2. 绝不触碰项目源码：不要写任何会修改现有文件的代码；不要 import os/sys/pathlib 等模块。
3. AI 生成的策略 META["id"] 必须以 ai_ 前缀开头。
4. 只 import polars as pl，不 import 其他模块。

要求:
1. 用户可能调整的策略阈值通过 META["params"] 暴露；公式常数、固定窗口、布尔开关不必强行参数化。
2. 遵循指南的文件结构，但优先贴合用户规则，不要为了套模板歪曲策略含义。
3. ENTRY_SIGNALS/EXIT_SIGNALS 根据策略逻辑选择匹配的信号列，不要照搬示例。
4. scoring 权重根据策略核心逻辑定制，总和 = 1.0，键必须是指南列出的可用列。
5. markets 只写策略真正适用的市场。比率类字段是小数（0.05 = 5%）。
6. 直接输出 Python 代码，不要输出其他内容。

--- 策略开发指南 ---

"""

# The AST security boundary — ported verbatim from TickFlow (do not loosen).
_FORBIDDEN_MODULES = {"os", "sys", "subprocess", "socket", "shutil",
                      "pathlib", "http", "urllib", "requests", "httpx"}
_FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "__import__",
                    "globals", "locals", "vars", "dir", "getattr",
                    "setattr", "delattr", "input"}


class AIStrategyGenerator:
    """Generate + validate strategy code from a natural-language prompt.

    Args:
        llm: a LangChain-style model with ``.invoke(prompt) -> message`` whose
             ``.content`` is the text. Pass the engine's ``quick_thinking_llm``.
    """

    def __init__(self, llm):
        self._llm = llm
        self._guide_cache: str | None = None

    def _get_guide(self) -> str:
        if self._guide_cache is None:
            self._guide_cache = (
                GUIDE_PATH.read_text(encoding="utf-8") if GUIDE_PATH.exists() else ""
            )
            if not self._guide_cache:
                logger.warning("strategy guide not found at %s", GUIDE_PATH)
        return self._guide_cache

    def generate(self, user_prompt: str) -> dict:
        """Return ``{code, meta, valid, error}``. Never raises on bad output."""
        guide = self._get_guide()
        try:
            code = self._call_llm(user_prompt, guide)
        except Exception as e:  # noqa: BLE001 — surface LLM errors as a result
            return {"code": "", "meta": {}, "valid": False, "error": f"LLM 调用失败: {e}"}

        try:
            self._validate_safety(code)
        except (ValueError, SyntaxError) as e:
            return {"code": code, "meta": {}, "valid": False, "error": str(e)}

        try:
            meta = self._extract_meta(code)
        except Exception as e:  # noqa: BLE001
            return {"code": code, "meta": {}, "valid": False, "error": f"解析 META 失败: {e}"}
        if not meta.get("id"):
            return {"code": code, "meta": meta, "valid": False,
                    "error": "META 缺少 id 字段"}

        return {"code": code, "meta": meta, "valid": True, "error": None}

    def _call_llm(self, user_prompt: str, guide: str) -> str:
        messages = [
            {"role": "system", "content": _SYSTEM_PREFIX + guide},
            {"role": "user", "content": user_prompt},
        ]
        response = self._llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        # Extract fenced code if the model wrapped the answer in Markdown.
        if "```python" in content:
            content = content.split("```python", 1)[1].split("```", 1)[0].strip()
        elif "```" in content:
            content = content.split("```", 1)[1].split("```", 1)[0].strip()
        return content.strip()

    @staticmethod
    def _validate_safety(code: str) -> None:
        """AST-level safety check (ported from TickFlow). Raises on violation."""
        if not code.strip():
            raise ValueError("生成的代码为空")
        tree = ast.parse(code)  # SyntaxError propagates as invalid
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root != "polars" and root in _FORBIDDEN_MODULES:
                        raise ValueError(f"禁止 import {alias.name}")
                    if root not in ("polars",):
                        raise ValueError(f"只允许 import polars, 检测到 import {alias.name}")
            if isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root != "polars":
                    raise ValueError(f"只允许 from polars import, 检测到 from {node.module} import")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in _FORBIDDEN_CALLS:
                    raise ValueError(f"禁止调用 {node.func.id}()")

    @staticmethod
    def _extract_meta(code: str) -> dict:
        """Extract the literal META dict without executing the module."""
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "META":
                        code_obj = compile(
                            ast.Expression(node.value), "<meta>", "eval"
                        )
                        return eval(code_obj, {"__builtins__": {}})  # noqa: S307
        return {}
