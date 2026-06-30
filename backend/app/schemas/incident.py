from pydantic import BaseModel
from datetime import datetime

# Estructura de datos requerida para crear un incidente
class IncidentCreate(BaseModel):
    title: str
    description: str
    source: str
    severity: str

# Estructura de datos devuelta por la API (con datos de auditoría)
class IncidentResponse(IncidentCreate):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True