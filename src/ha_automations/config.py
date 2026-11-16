"""Base model for settings read from apps.yaml."""
from appdaemon.models.config.app import AppConfig
from pydantic import BaseModel, ConfigDict

# Keys AppDaemon itself puts in app args.
APPDAEMON_KEYS = frozenset(f.alias or name for name, f in AppConfig.model_fields.items())


class Config(BaseModel):
    """Read-only settings model. Unknown keys are an error."""

    model_config = ConfigDict(extra="forbid", frozen=True)
