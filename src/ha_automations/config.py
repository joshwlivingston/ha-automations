"""Base model for settings read from apps.yaml."""
from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    """Read-only settings model. Unknown keys are an error.

    Each field's docstring is its description.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, use_attribute_docstrings=True)
