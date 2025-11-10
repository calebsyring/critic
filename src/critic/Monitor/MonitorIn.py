from enum import Enum

from pydantic import UUID4, AwareDatetime, BaseModel, Field, HttpUrl


class Assertions(BaseModel):
    status_code: int | None = None
    body_contains: str | None = None


class _State(str, Enum):
    new = 'new'
    up = 'up'
    down = 'down'
    paused = 'paused'


class MonitorIn(BaseModel):
    project_id: str  # Slugified project name
    id: UUID4

    state: _State = _State.new

    url: HttpUrl
    interval: int = Field(..., description='minutes', ge=1)
    next_due_at: AwareDatetime  # Should be rounded to nearest minute

    timeout: int = Field(..., description='seconds', ge=1)
    assertions: Assertions | None = None

    failures_before_alerting: int = Field(1, ge=0)
    alert_slack_channels: list[str] = Field(default_factory=list)
    alert_emails: list[str] = Field(default_factory=list)
    realert_interval: int = Field(..., description='seconds', ge=0)


class UptimeLog(BaseModel):
    monitor_id: UUID4 = Field(..., description='monitor')
    timestamp: int = Field(..., description='time', ge=0)
    status: _State = Field(..., description='status')
    resp_code: int = Field(..., description='code', ge=100, le=599)
    latency_secs: float = Field(..., description='latency', ge=0)


class Project(BaseModel):
    id: UUID4 = Field(..., description='partition_key')
    name: str = Field(..., description='project_name')
