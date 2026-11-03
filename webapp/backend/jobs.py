"""Scheduled jobs API (v0.4.0 Phase 2).

Thin HTTP glue over ``webapp.backend.scheduler`` job CRUD + manual trigger.
PRD §2.3.2:

  GET    /api/jobs            list jobs
  POST   /api/jobs            create a job
  PUT    /api/jobs/{id}       update a job
  DELETE /api/jobs/{id}       delete a job
  POST   /api/jobs/{id}/run   run a job now (manual trigger)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from webapp.backend import auth, scheduler

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobPayload(BaseModel):
    id: str
    kind: str                      # analysis | screen | warmup
    cron: str                      # 5-field cron: min hour dom month dow
    params: dict = {}
    enabled: bool = True


@router.get("")
def list_jobs(_: None = Depends(auth.require_auth)) -> dict:
    return {"jobs": scheduler.load_jobs(), "running": scheduler._scheduler is not None}


@router.post("")
def create_job(payload: JobPayload, _: None = Depends(auth.require_auth)) -> dict:
    if scheduler.get_job(payload.id) is not None:
        raise HTTPException(status_code=409, detail=f"任务 {payload.id} 已存在")
    try:
        return scheduler.upsert_job(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/{job_id}")
def update_job(job_id: str, payload: JobPayload,
               _: None = Depends(auth.require_auth)) -> dict:
    if scheduler.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail=f"任务 {job_id} 不存在")
    data = payload.model_dump()
    data["id"] = job_id
    try:
        return scheduler.upsert_job(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{job_id}")
def delete_job(job_id: str, _: None = Depends(auth.require_auth)) -> dict:
    if not scheduler.delete_job(job_id):
        raise HTTPException(status_code=404, detail=f"任务 {job_id} 不存在")
    return {"ok": True, "id": job_id}


@router.post("/{job_id}/run")
def run_job(job_id: str, _: None = Depends(auth.require_auth)) -> dict:
    try:
        return scheduler.run_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
