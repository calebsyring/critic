from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class MonitorState(str, Enum):
    new = 'new'
    up = 'up'
    down = 'down'
    paused = 'paused'


class UptimeMonitorModel(BaseModel):
    project_id: UUID
    slug: str
    state: MonitorState = MonitorState.new
    url: HttpUrl
    frequency_mins: int = Field(ge=1)
    next_due_at: datetime
    timeout_secs: float = Field(ge=0)
    # TODO: assertions should probably become its own model
    assertions: dict[str, Any] | None = None
    failures_before_alerting: int
    alert_slack_channels: list[str] = Field(default_factory=list)
    alert_emails: list[str] = Field(default_factory=list)
    realert_interval_mins: int = Field(ge=0)
    GSI_PK: str = Field(default='all monitors')


class ProjectMonitors(BaseModel):
    uptime: list[UptimeMonitorModel] = Field(default_factory=list)
