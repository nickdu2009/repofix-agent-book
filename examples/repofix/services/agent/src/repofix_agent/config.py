"""Validated configuration for the HTTP service shell."""

from pydantic import BaseModel, ConfigDict, Field


class ServiceConfig(BaseModel):
    """Small, explicit limits owned by the Python process."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    service_name: str = "repofix-agent"
    max_run_seconds: float = Field(default=300.0, gt=0, le=3_600)
    max_total_tokens: int = Field(default=100_000, ge=1, le=10_000_000)
