"""Cross-cutting services (v0.4.0): notification adapters.

These are best-effort, side-channel utilities (system notifications, webhooks).
They never raise on failure — a notification that fails to send must not break
the analysis / screening pipeline that triggered it.
"""
