from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class Assertions(BaseModel):
    status_code: int | None = None
    body_contains: str | None = None


class _State(str, Enum):
    new = 'new'
    up = 'up'
    down = 'down'
    paused = 'paused'


class MonitorIn(BaseModel):
    group_id: str | None = None
    alert_slack_channels: list[str] = Field(default_factory=list)
    alert_emails: list[str] = Field(default_factory=list)
    realert_interval: int = Field(..., description='seconds', ge=0)
    state: _State = _State.new
    failures_before_alerting: int = Field(1, ge=0)
    url: HttpUrl
    interval: int = Field(..., description='seconds', ge=1)
    timeout: int = Field(..., description='seconds', ge=1)
    assertions: Assertions | None = None
