"""Monitor rules + alerts API (v0.4.0 Phase 2).

Thin HTTP glue over ``dromx.strategy.monitor_rules`` (rule CRUD) and
``webapp.backend.alert_store`` (alert history). PRD §2.4.2:

  GET    /api/monitor/rules        list rules
  POST   /api/monitor/rules        create a rule
  PUT    /api/monitor/rules/{id}   update a rule
  DELETE /api/monitor/rules/{id}   delete a rule
  GET    /api/monitor/alerts       alert history (newest first)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from dromx.strategy import monitor_rules
from webapp.backend import alert_store, auth

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


class RulePayload(BaseModel):
    id: str
    name: str
    type: str                      # price | signal | strategy
    scope: str = "symbols"         # symbols | all
    symbols: list[str] = []
    market: str = "hk"
    strategy_id: str | None = None
    direction: str = "entry"       # entry | exit | both (strategy type)
    conditions: list[dict] = []
    logic: str = "and"
    cooldown_seconds: int = 3600
    severity: str = "info"
    message: str = ""
    enabled: bool = True


def _validated(payload: dict) -> dict:
    rule = monitor_rules.normalize(payload)
    try:
        monitor_rules.validate(rule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return rule


@router.get("/rules")
def list_rules(_: None = Depends(auth.require_auth)) -> dict:
    return {"rules": monitor_rules.load_all()}


@router.post("/rules")
def create_rule(payload: RulePayload, _: None = Depends(auth.require_auth)) -> dict:
    if monitor_rules.load_one(payload.id) is not None:
        raise HTTPException(status_code=409, detail=f"规则 {payload.id} 已存在")
    rule = _validated(payload.model_dump())
    monitor_rules.save_one(rule)
    return rule


@router.put("/rules/{rule_id}")
def update_rule(rule_id: str, payload: RulePayload,
                _: None = Depends(auth.require_auth)) -> dict:
    if monitor_rules.load_one(rule_id) is None:
        raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
    data = payload.model_dump()
    data["id"] = rule_id  # path id wins
    rule = _validated(data)
    monitor_rules.save_one(rule)
    return rule


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str, _: None = Depends(auth.require_auth)) -> dict:
    if not monitor_rules.delete_one(rule_id):
        raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
    return {"ok": True, "id": rule_id}


@router.get("/alerts")
def list_alerts(limit: int = 200, source: str | None = None,
                _: None = Depends(auth.require_auth)) -> dict:
    return {"alerts": alert_store.query(limit=limit, source=source)}
