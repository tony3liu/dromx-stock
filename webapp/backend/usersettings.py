"""User settings — 页面配置层（优先级高于 .env）

toC 场景：用户不该手编 .env。设置页保存的配置写入
``~/.dromx/user_settings.json``，运行时生效；优先级：

    页面配置 (user_settings.json)  >  .env / 进程环境变量  >  代码默认值

生效机制（对现有代码零侵入）：
- 启动时（load_dotenv 之后、dromx 各模块 import 之前）：先快照 .env 原值，
  再把页面配置写入 ``os.environ`` —— default_config 的 ``_apply_env_overrides``
  在 import 时自然读到覆盖后的值。
- 运行时保存：同步更新 ``os.environ``（数据源 key 立即生效）；
  LLM 相关 key 额外通过 ``set_config`` 更新已初始化的配置，
  并由调用方重置 assistant planner 单例。

安全：GET 接口对 secret 类 key 只回掩码（后 4 位），不回原文。
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_PATH = Path(os.path.expanduser("~")) / ".dromx" / "user_settings.json"

_lock = threading.Lock()

# .env 原值快照（apply_on_startup 时记录，用于"清除页面配置"时回落）
_originals: dict[str, str | None] = {}

# 可在页面配置的 key 注册表：key / 显示名 / 分组 / 是否密钥
REGISTRY: list[dict] = [
    # ---- LLM 配置（非密钥） ----
    {"key": "DROMX_LLM_PROVIDER", "label": "模型提供商", "group": "模型", "secret": False,
     "placeholder": "openai / deepseek / anthropic / google / kimi ..."},
    {"key": "DROMX_DEEP_THINK_LLM", "label": "深度思考模型", "group": "模型", "secret": False,
     "placeholder": "如 deepseek-reasoner / gpt-5"},
    {"key": "DROMX_QUICK_THINK_LLM", "label": "快速模型", "group": "模型", "secret": False,
     "placeholder": "如 deepseek-chat / gpt-5-mini"},
    {"key": "DROMX_LLM_BACKEND_URL", "label": "自定义 API 地址", "group": "模型", "secret": False,
     "placeholder": "OpenAI 兼容端点，可留空"},
    {"key": "DROMX_OUTPUT_LANGUAGE", "label": "输出语言", "group": "模型", "secret": False,
     "placeholder": "中文 / English"},
    {"key": "DROMX_TEMPERATURE", "label": "采样温度", "group": "模型", "secret": False,
     "placeholder": "0.0 - 1.0，留空用模型默认"},
    # ---- LLM 密钥 ----
    {"key": "OPENAI_API_KEY", "label": "OpenAI", "group": "模型密钥", "secret": True},
    {"key": "DEEPSEEK_API_KEY", "label": "DeepSeek", "group": "模型密钥", "secret": True},
    {"key": "ANTHROPIC_API_KEY", "label": "Anthropic", "group": "模型密钥", "secret": True},
    {"key": "GOOGLE_API_KEY", "label": "Google (Gemini)", "group": "模型密钥", "secret": True},
    {"key": "MOONSHOT_API_KEY", "label": "Kimi (Moonshot)", "group": "模型密钥", "secret": True},
    {"key": "DASHSCOPE_API_KEY", "label": "通义千问 (DashScope)", "group": "模型密钥", "secret": True},
    {"key": "ZHIPU_API_KEY", "label": "智谱 GLM", "group": "模型密钥", "secret": True},
    {"key": "OPENROUTER_API_KEY", "label": "OpenRouter", "group": "模型密钥", "secret": True},
    {"key": "XAI_API_KEY", "label": "xAI (Grok)", "group": "模型密钥", "secret": True},
    # ---- 数据源密钥 ----
    {"key": "SERPER_API_KEY", "label": "Serper（联网搜索）", "group": "数据源", "secret": True,
     "hint": "serper.dev 免费额度，用于 web_search 核实事实"},
    {"key": "FRED_API_KEY", "label": "FRED（宏观数据）", "group": "数据源", "secret": True,
     "hint": "fred.stlouisfed.org 免费申请，用于宏观指标"},
    {"key": "jin10_token", "label": "金十数据（快讯/日历/行情）", "group": "数据源", "secret": True,
     "hint": "mcp.jin10.com/app/ 申请"},
    {"key": "ALPHA_VANTAGE_API_KEY", "label": "Alpha Vantage（美股）", "group": "数据源", "secret": True},
]

_VALID_KEYS = {e["key"] for e in REGISTRY}


def _read_store() -> dict:
    if not _PATH.exists():
        return {}
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        return {k: str(v) for k, v in data.items() if k in _VALID_KEYS and isinstance(v, str)}
    except Exception as e:  # noqa: BLE001
        logger.warning("user_settings read failed: %s", e)
        return {}


def _write_store(data: dict) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, _PATH)


def _apply_config_mapping(key: str) -> None:
    """LLM 类 key：同步到已初始化的 dromx 配置（运行时保存路径）"""
    try:
        from dromx.default_config import _ENV_OVERRIDES, _coerce
        from dromx.dataflows.config import get_config, set_config

        target = _ENV_OVERRIDES.get(key)
        if not target:
            return
        raw = os.environ.get(key)
        if raw is None or raw == "":
            # 页面配置被清除且 .env 无此 key → 回落到 import 时构建的默认配置
            import dromx.default_config as dc

            set_config({target: dc.DEFAULT_CONFIG.get(target)})
            return
        current = get_config().get(target)
        set_config({target: _coerce(raw, current)})
    except Exception as e:  # noqa: BLE001 — 配置同步失败不阻塞保存
        logger.warning("config mapping for %s failed: %s", key, e)


def apply_on_startup() -> None:
    """启动时应用页面配置（在 load_dotenv 之后、dromx import 之前调用）。

    只写 os.environ：default_config 在 import 时读取的就是覆盖后的值，
    无需触碰配置模块。
    """
    with _lock:
        store = _read_store()
        if not store:
            # 仍要快照原值，运行时保存/清除才能正确回落
            for k in _VALID_KEYS:
                _originals[k] = os.environ.get(k)
            return
        for k in _VALID_KEYS:
            _originals[k] = os.environ.get(k)
        for k, v in store.items():
            os.environ[k] = v
        logger.info("user settings applied: %d page-configured keys", len(store))


def get_settings() -> list[dict]:
    """GET 接口数据：每个 key 的配置状态（secret 只回掩码）"""
    with _lock:
        store = _read_store()
        out = []
        for entry in REGISTRY:
            k = entry["key"]
            page_val = store.get(k)
            env_val = _originals.get(k) if k in _originals else os.environ.get(k)
            if page_val:
                source, effective = "page", page_val
            elif env_val:
                source, effective = "env", env_val
            else:
                source, effective = None, None
            item = {
                "key": k,
                "label": entry["label"],
                "group": entry["group"],
                "secret": entry["secret"],
                "hint": entry.get("hint", ""),
                "placeholder": entry.get("placeholder", ""),
                "source": source,
                "configured": effective is not None,
            }
            if entry["secret"]:
                item["preview"] = f"••••{effective[-4:]}" if effective else ""
            else:
                item["value"] = effective or ""
            out.append(item)
        return out


def update_settings(updates: dict) -> dict:
    """保存页面配置。value 为空字符串 = 清除页面配置（回落 .env）。

    返回 {"updated": [...], "llm_changed": bool}
    """
    llm_keys = {e["key"] for e in REGISTRY if e["group"] in ("模型", "模型密钥")}
    updated, llm_changed = [], False
    with _lock:
        store = _read_store()
        for key, value in updates.items():
            if key not in _VALID_KEYS:
                raise ValueError(f"不支持的配置项: {key}")
            value = (value or "").strip()
            if value:
                store[key] = value
                os.environ[key] = value
            else:
                store.pop(key, None)
                # 回落 .env 原值
                original = _originals.get(key)
                if original:
                    os.environ[key] = original
                else:
                    os.environ.pop(key, None)
            _apply_config_mapping(key)
            updated.append(key)
            if key in llm_keys:
                llm_changed = True
        _write_store(store)
    return {"updated": updated, "llm_changed": llm_changed}
