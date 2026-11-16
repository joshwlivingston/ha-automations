"""Base model for settings read from apps.yaml."""
from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    """Read-only settings model. Unknown keys are an error."""

    model_config = ConfigDict(extra="forbid", frozen=True)
