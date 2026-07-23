"""Feishu (Lark) webhook adapter (ported from TickFlow).

Pushes alerts to a Feishu custom-bot webhook — free, no paid API. Supports a
plain text message and an interactive markdown card. Optional HMAC-SHA256
signing (when the bot has "signature verification" enabled).

Feishu custom bot setup:
  1. Group settings → Bots → add "Custom Bot"
  2. Copy the webhook URL (https://open.feishu.cn/open-apis/bot/v2/hook/xxx)
  3. (optional) enable "signature verification", record the secret

Design: failures degrade silently and never raise. Uses the repo-standard
``requests`` client (not httpx) for consistency with the other dataflows.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time

import requests

logger = logging.getLogger(__name__)

_MAX_LEN = 500          # plain-text truncation
_CARD_MAX_LEN = 28000   # card body truncation (Feishu card limit is ~30KB)
_TIMEOUT = 5.0

FEISHU_HOOK_PREFIX = "https://open.feishu.cn/open-apis/bot/v2/hook/"


def is_valid_feishu_url(url: str) -> bool:
    return bool(url) and url.startswith(FEISHU_HOOK_PREFIX)


def _truncate(text: str, limit: int = _MAX_LEN) -> str:
    text = (text or "").strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def _gen_sign(timestamp: str, secret: str) -> str:
    """Feishu custom-bot signature: HMAC-SHA256 over '<ts>\\n<secret>', base64."""
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _post_feishu(webhook_url: str, payload: dict, secret: str) -> bool:
    try:
        if secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = _gen_sign(timestamp, secret)

        resp = requests.post(webhook_url, json=payload, timeout=_TIMEOUT)
        if resp.status_code == 200:
            try:
                data = resp.json()
                if isinstance(data, dict):
                    code = data.get("code", data.get("StatusCode", 0))
                    if code == 0:
                        return True
                    logger.debug("feishu business error: %s", data)
                    return False
            except ValueError:
                return True  # non-JSON 200 → treat as success
        logger.debug("feishu HTTP %s: %s", resp.status_code, resp.text[:200])
        return False
    except Exception as e:  # noqa: BLE001 — auxiliary channel, never raise
        logger.debug("feishu webhook failed: %s", e)
        return False


def send_feishu(webhook_url: str, title: str, body: str, secret: str = "") -> bool:
    """Send a plain-text message. False (silent) on failure or bad URL."""
    if not is_valid_feishu_url(webhook_url):
        return False
    text = _truncate(f"{title}\n{body}".strip())
    if not text:
        return False
    return _post_feishu(webhook_url, {"msg_type": "text", "content": {"text": text}}, secret)


def send_feishu_card(webhook_url: str, title: str, subtitle: str,
                     body_md: str, secret: str = "") -> bool:
    """Send an interactive markdown card (renders a full report). Silent on fail."""
    if not is_valid_feishu_url(webhook_url):
        return False
    body = _truncate(body_md, _CARD_MAX_LEN)
    elements: list[dict] = []
    if subtitle.strip():
        elements.append({"tag": "div", "text": {"tag": "lark_md",
                                                 "content": f"**{subtitle.strip()}**"}})
        elements.append({"tag": "hr"})
    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": body}})

    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": title}, "template": "blue"},
            "elements": elements,
        },
    }
    return _post_feishu(webhook_url, payload, secret)
