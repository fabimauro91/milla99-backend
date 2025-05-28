from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class ProjectSettingsBase(SQLModel):
    driver_dist: str
    referral_1: str
    referral_2: str
    referral_3: str
    referral_4: str
    referral_5: str
    driver_saving: str
    company: str
    bonus: str

class ProjectSettings(ProjectSettingsBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ProjectSettingsCreate(ProjectSettingsBase):
    pass