from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class StatusHistoryResponse(BaseModel):
    id: int
    old_status: Optional[str] = None
    new_status: str
    changed_at: datetime
    changed_by: str

    model_config = ConfigDict(from_attributes=True)


class IncidentCreate(BaseModel):
    title: str
    description: str
    source: str
    severity: str

class IncidentUpdateStatus(BaseModel):
    status: str
    # changed_by: str = "System_AI" 

class IncidentResponse(IncidentCreate):
    id: int
    status: str
    created_at: datetime
    # history: List[StatusHistoryResponse] = []

    model_config = ConfigDict(from_attributes=True)