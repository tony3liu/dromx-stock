"""Pydantic request/response models for the web API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateRunRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol, e.g. NVDA / 07709.HK / 600519.SS")
    trade_date: str = Field(..., description="Analysis date YYYY-MM-DD")
    analysts: list[str] = Field(
        default_factory=lambda: ["market", "social", "news", "fundamentals", "industry"],
        description="Analyst keys to include",
    )
    depth: int = Field(default=1, ge=1, le=5, description="Research depth: 1 shallow / 3 medium / 5 deep")
    shares: float | None = Field(
        default=None, description="User's existing position size in this name (negative = short); None/0 = flat",
    )
    cost_basis: float | None = Field(
        default=None, description="Per-share cost basis in the instrument's quote currency (optional)",
    )
    holdings: list[str] = Field(
        default_factory=list,
        description="Other current holdings for the pre-trade portfolio-context factor, "
                    "e.g. ['MU', '07709.HK:20']. Empty → portfolio context is skipped.",
    )
    strategy_id: str | None = Field(
        default=None,
        description="Source screening strategy this run originated from (attribution only).",
    )
    on_complete_notify: bool = Field(
        default=False,
        description="Send a notification (Feishu card + system pop-up) when the analysis finishes.",
    )


class CreateRunResponse(BaseModel):
    id: str
    status: str


class RunSummary(BaseModel):
    id: str
    ticker: str | None = None
    trade_date: str | None = None
    status: str | None = None
    rating: str | None = None
    created_at: str | None = None
    finished_at: str | None = None


class QARequest(BaseModel):
    question: str
    history: list[tuple[str, str]] = Field(default_factory=list)


class BacktestRequest(BaseModel):
    ticker: str = Field(..., description="Ticker to backtest")
    start_date: str = Field(..., description="Backtest window start YYYY-MM-DD")
    end_date: str = Field(..., description="Backtest window end YYYY-MM-DD")
    analysts: list[str] = Field(
        default_factory=lambda: ["market", "social", "news", "fundamentals", "industry"],
    )
    depth: int = Field(default=1, ge=1, le=5)
    holding_days: int = Field(default=5, ge=1, le=60, description="Return window per call")


class QAResponse(BaseModel):
    answer: str
