"""AI strategy generator isolation tests (mocked LLM, no network).

Covers the security boundary (AST safety), literal META extraction, code-fence
stripping, and graceful failure — the parts that must hold regardless of what
the model returns.
"""

from unittest import mock

import pytest

from dromx.strategy.ai_generator import AIStrategyGenerator

_GOOD_STRATEGY = '''
"""RSI 超卖反弹"""
import polars as pl

META = {
    "id": "ai_rsi_oversold",
    "name": "RSI超卖反弹",
    "description": "RSI < 30 且收阳",
    "markets": ["HK"],
    "params": [
        {"id": "rsi_max", "label": "RSI上限", "type": "float", "default": 30.0},
    ],
    "scoring": {"change_pct": 0.5, "vol_ratio_5d": 0.5},
    "limit": 50,
}

def filter(df: pl.DataFrame, params: dict) -> pl.Expr:
    return (pl.col("rsi_14") < params.get("rsi_max", 30.0)) & (pl.col("close") > pl.col("open"))
'''


def _llm(content: str):
    llm = mock.MagicMock()
    llm.invoke.return_value = mock.MagicMock(content=content)
    return llm


@pytest.mark.unit
class TestAIStrategyGenerator:
    def test_valid_strategy_parsed(self):
        gen = AIStrategyGenerator(_llm(_GOOD_STRATEGY))
        result = gen.generate("找 RSI 超卖反弹的港股")
        assert result["valid"] is True
        assert result["error"] is None
        assert result["meta"]["id"] == "ai_rsi_oversold"
        assert result["meta"]["markets"] == ["HK"]

    def test_code_fence_is_stripped(self):
        gen = AIStrategyGenerator(_llm("```python\n" + _GOOD_STRATEGY + "\n```"))
        result = gen.generate("x")
        assert result["valid"] is True
        assert "```" not in result["code"]

    def test_forbidden_import_rejected(self):
        bad = 'import os\nMETA = {"id": "ai_x"}\ndef filter(df, p):\n    return None\n'
        result = AIStrategyGenerator(_llm(bad)).generate("x")
        assert result["valid"] is False
        assert "os" in result["error"]

    def test_forbidden_call_rejected(self):
        bad = ('import polars as pl\nMETA = {"id": "ai_x"}\n'
               'def filter(df, p):\n    eval("1+1")\n    return None\n')
        result = AIStrategyGenerator(_llm(bad)).generate("x")
        assert result["valid"] is False
        assert "eval" in result["error"]

    def test_non_polars_import_rejected(self):
        bad = ('import numpy as np\nMETA = {"id": "ai_x"}\n'
               'def filter(df, p):\n    return None\n')
        result = AIStrategyGenerator(_llm(bad)).generate("x")
        assert result["valid"] is False

    def test_syntax_error_is_invalid_not_raised(self):
        result = AIStrategyGenerator(_llm("def filter( : bad syntax")).generate("x")
        assert result["valid"] is False

    def test_missing_meta_id_is_invalid(self):
        code = ('import polars as pl\nMETA = {"name": "no id"}\n'
                'def filter(df, p):\n    return pl.col("close") > 0\n')
        result = AIStrategyGenerator(_llm(code)).generate("x")
        assert result["valid"] is False
        assert "id" in result["error"]

    def test_llm_failure_surfaced_as_result(self):
        llm = mock.MagicMock()
        llm.invoke.side_effect = RuntimeError("provider down")
        result = AIStrategyGenerator(llm).generate("x")
        assert result["valid"] is False
        assert "provider down" in result["error"]
