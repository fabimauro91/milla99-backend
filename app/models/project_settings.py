from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class ProjectSettingsBase(SQLModel):
    value: str
    description: str

class ProjectSettings(ProjectSettingsBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ProjectSettingsCreate(ProjectSettingsBase):
    pass