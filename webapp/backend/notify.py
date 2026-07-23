"""Notification config + dispatch + API (v0.4.0).

A thin web-layer wrapper over the free notification adapters in
``dromx.services``:
  - system pop-up (``notify_adapter``)
  - Feishu webhook, text + card (``webhook_adapter``)

Config is stored as one JSON file at ``~/.dromx/notify.json`` (mirrors
``store.py``'s single-file, no-database approach). ``alert()`` is the single
dispatch entry the rest of the backend calls (e.g. the on-complete analysis
hook); it fans out to whichever channels are enabled/configured and never
raises — a notification failure must never break the caller.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from dromx.services import notify_adapter, webhook_adapter
from webapp.backend import auth

logger = logging.getLogger("dromx.web.notify")

_CONFIG_PATH = Path(os.path.expanduser("~")) / ".dromx" / "notify.json"

_DEFAULT_CONFIG = {
    "system": {"enabled": True},
    "feishu": {"webhook_url": "", "secret": ""},
}


# ---------------------------------------------------------------------------
# Config store
# ---------------------------------------------------------------------------


def load_config() -> dict:
    """Load notify config, merged over defaults. Never raises."""
    cfg = {k: dict(v) for k, v in _DEFAULT_CONFIG.items()}
    try:
        if _CONFIG_PATH.exists():
            stored = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            for key, val in (stored or {}).items():
                if isinstance(val, dict) and key in cfg:
                    cfg[key].update(val)
                else:
                    cfg[key] = val
    except Exception as e:  # noqa: BLE001
        logger.warning("notify config read failed: %s", e)
    return cfg


def save_config(update: dict) -> dict:
    """Merge ``update`` into the stored config (atomic write). Returns full config."""
    cfg = load_config()
    for key, val in (update or {}).items():
        if isinstance(val, dict) and isinstance(cfg.get(key), dict):
            cfg[key].update(val)
        else:
            cfg[key] = val
    try:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(_CONFIG_PATH.parent), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _CONFIG_PATH)
    except Exception as e:  # noqa: BLE001
        logger.warning("notify config write failed: %s", e)
    return cfg


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def channel_status() -> dict:
    """Report which channels are available/configured (no secrets leaked)."""
    cfg = load_config()
    feishu_url = cfg.get("feishu", {}).get("webhook_url", "")
    return {
        "system": {
            "enabled": bool(cfg.get("system", {}).get("enabled", True)),
            "available": notify_adapter.is_available(),
        },
        "feishu": {
            "configured": webhook_adapter.is_valid_feishu_url(feishu_url),
        },
    }


def alert(title: str, body: str, channels: list[str] | None = None,
          *, card_subtitle: str = "") -> dict:
    """Dispatch an alert to the requested (and enabled) channels.

    ``channels`` defaults to all configured channels. Returns a per-channel
    delivery map ``{channel: bool}``. Never raises.
    """
    cfg = load_config()
    want = set(channels) if channels else {"system", "feishu"}
    results: dict[str, bool] = {}

    if "system" in want and cfg.get("system", {}).get("enabled", True):
        try:
            results["system"] = notify_adapter.notify(title, body)
        except Exception as e:  # noqa: BLE001 — never let a channel break the caller
            logger.debug("system notify raised: %s", e)
            results["system"] = False

    if "feishu" in want:
        feishu = cfg.get("feishu", {})
        url = feishu.get("webhook_url", "")
        secret = feishu.get("secret", "")
        if webhook_adapter.is_valid_feishu_url(url):
            try:
                if card_subtitle:
                    ok = webhook_adapter.send_feishu_card(url, title, card_subtitle, body, secret)
                else:
                    ok = webhook_adapter.send_feishu(url, title, body, secret)
            except Exception as e:  # noqa: BLE001
                logger.debug("feishu notify raised: %s", e)
                ok = False
            results["feishu"] = ok

    return results


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/notify", tags=["notify"])


class TestRequest(BaseModel):
    channels: list[str] | None = None


class SettingsRequest(BaseModel):
    system: dict | None = None
    feishu: dict | None = None


@router.get("/channels")
def get_channels(_: None = Depends(auth.require_auth)) -> dict:
    """Configured/available notification channels (no secrets)."""
    return channel_status()


@router.post("/test")
def test_notify(req: TestRequest, _: None = Depends(auth.require_auth)) -> dict:
    """Send a test notification through the requested (or all) channels."""
    results = alert(
        "DromX 测试通知",
        "这是一条测试通知，说明该渠道已配置成功。",
        channels=req.channels,
    )
    return {"ok": any(results.values()), "results": results}


@router.put("/settings")
def update_settings(req: SettingsRequest, _: None = Depends(auth.require_auth)) -> dict:
    """Update notification config. Returns the merged config (secrets redacted)."""
    update: dict = {}
    if req.system is not None:
        update["system"] = req.system
    if req.feishu is not None:
        update["feishu"] = req.feishu
    cfg = save_config(update)
    # Redact the Feishu secret in the response.
    safe = {k: dict(v) if isinstance(v, dict) else v for k, v in cfg.items()}
    if "feishu" in safe and safe["feishu"].get("secret"):
        safe["feishu"]["secret"] = "***"
    return safe
