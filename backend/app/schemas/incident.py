from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# --- ESQUEMAS PARA HISTORIAL ---
class StatusHistoryResponse(BaseModel):
    id: int
    old_status: Optional[str] = None
    new_status: str
    changed_at: datetime
    changed_by: str

    class Config:
        from_attributes = True


# --- ESQUEMAS PARA INCIDENTES ---
class IncidentCreate(BaseModel):
    title: str
    description: str
    source: str
    severity: str

class IncidentUpdateStatus(BaseModel):
    status: str
    # Opcional: Podrías pedir el usuario que hace el cambio
    # changed_by: str = "System_AI" 

class IncidentResponse(IncidentCreate):
    id: int
    status: str
    created_at: datetime
    # Descomenta la siguiente línea si quieres que la API devuelva el historial de cambios de una vez
    # history: List[StatusHistoryResponse] = []

    class Config:
        from_attributes = True