from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, HttpUrl, field_validator

from critic.libs.assertions import Assertion
from critic.libs.ddb import CONSTANT_GSI_PK
from critic.libs.dt import to_utc


class MonitorState(str, Enum):
    new = 'new'
    up = 'up'
    down = 'down'
    paused = 'paused'


class ProjectModel(BaseModel):
    id: UUID
    name: str


class UptimeMonitorModel(BaseModel):
    project_id: UUID
    slug: str = Field(pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$', max_length=200)
    url: HttpUrl

    state: MonitorState = Field(default=MonitorState.new)
    frequency_mins: int = Field(ge=1, default=1)
    consecutive_fails: int = Field(ge=0, default=0)
    log_counter: int = Field(ge=0, default=0)
    next_due_at: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(second=0, microsecond=0)
    )
    timeout_secs: float = Field(ge=0, default=5)
    assertions: list[Assertion] = Field(default_factory=list)
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

    @property
    def id(self) -> str:
        return UptimeLogModel.monitor_id_from_parts(self.project_id, self.slug)


class UptimeLogModel(BaseModel):
    monitor_id: str = Field(
        # Project ID and monitor slug, separated by a slash
        # pattern = UUID / slug
        pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[a-z0-9]+(?:-[a-z0-9]+)*$'
    )
    timestamp: AwareDatetime
    status: MonitorState
    resp_code: int | None = None
    latency_secs: float | None = None
    error_message: list[str] | None = None

    @staticmethod
    def monitor_id_from_parts(project_id: UUID | str, slug: str) -> str:
        return f'{project_id}/{slug}'


class ProjectMonitorsModel(BaseModel):
    uptime: list[UptimeMonitorModel] = Field(default_factory=list)
