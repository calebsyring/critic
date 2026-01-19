from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class MonitorState(str, Enum):
    new = 'new'
    up = 'up'
    down = 'down'
    paused = 'paused'


class UptimeMonitorModel(BaseModel):
    project_id: str
    slug: str
    state: MonitorState = MonitorState.new
    url: HttpUrl
    frequency_mins: int = Field(ge=1)
    consecutive_fails: int = Field(ge=0)
    next_due_at: str
    timeout_secs: float = Field(ge=0)
    # TODO: assertions should probably become its own model
    assertions: dict[str, Any] | None = None
    failures_before_alerting: int
    alert_slack_channels: list[str] = Field(default_factory=list)
    alert_emails: list[str] = Field(default_factory=list)
    realert_interval_mins: int = Field(ge=0)
    GSI_PK: str = Field(default='MONITOR')


class UptimeLog(BaseModel):
    monitor_id: str  # for now we just combine the monitor and slug
    timestamp: str
    status: MonitorState
    resp_code: int | None
    latency_secs: float | None


class ProjectMonitors(BaseModel):
    uptime: list[UptimeMonitorModel] = Field(default_factory=list)
