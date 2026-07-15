from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class StatusHistoryResponse(BaseModel):
    id: int
    old_status: Optional[str] = None
    new_status: str
    changed_at: datetime
    changed_by: str

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True