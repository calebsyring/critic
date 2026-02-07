from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, HttpUrl, field_validator

from critic.libs.ddb import CONSTANT_GSI_PK
from critic.libs.dt import to_utc


class MonitorState(str, Enum):
    new = 'new'
    up = 'up'
    down = 'down'
    paused = 'paused'


class Project(BaseModel):
    id: UUID
    name: str


class UptimeMonitorModel(BaseModel):
    project_id: UUID
    slug: str = Field(pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$', max_length=200)
    url: HttpUrl

    state: MonitorState = Field(default=MonitorState.new)
    frequency_mins: int = Field(ge=1, default=1)
    consecutive_fails: int = Field(ge=0, default=0)
    next_due_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(second=0, microsecond=0)
    )
    timeout_secs: float = Field(ge=0, default=5)
    assertions: dict[str, Any] = Field(default_factory=dict)
    failures_before_alerting: int = Field(ge=1, default=1)
    alert_slack_channels: list[str] = Field(default_factory=list)
    alert_emails: list[str] = Field(default_factory=list)
    realert_interval_mins: int = Field(ge=15, default=60)
    GSI_PK: str = Field(default=CONSTANT_GSI_PK)

    @field_validator('next_due_at')
    @classmethod
    def validate_next_due_at(cls, v: datetime) -> datetime:
        """Normalize to UTC"""
        if v.second or v.microsecond:
            raise ValueError('next_due_at must be no more precise than minutes')
        return to_utc(v)


class UptimeLog(BaseModel):
    monitor_id: str = Field(
        # Project ID and monitor slug, separated by a slash
        # pattern = UUID / slug
        pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[a-z0-9]+(?:-[a-z0-9]+)*$'
    )
    timestamp: AwareDatetime
    status: MonitorState
    resp_code: int | None
    latency_secs: float | None


class ProjectMonitors(BaseModel):
    uptime: list[UptimeMonitorModel] = Field(default_factory=list)
