"""Inputs for a new Vendomat workspace registry."""

from pydantic import BaseModel, Field


class WorkspaceRegistry(BaseModel):
    forge_url: str = Field(description="URL of the owner's source collection")
    vendomat_tag: str = Field(description="Vendomat release tag, without refs/tags/")
    devenv_tag: str | None = Field(default=None, description="Patched devenv tag, without refs/tags/")
