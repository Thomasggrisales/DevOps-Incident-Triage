from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# Esquema base con los campos requeridos
class IncidentBase(BaseModel):
    title: str = Field(..., description="Título del incidente", example="Alta latencia en Microservicio de Autenticación")
    description: str = Field(..., description="Detalle de los logs o métricas", example="Latencia por encima del umbral de 500ms durante 5 minutos")
    source: str = Field(..., description="Origen de la alerta (ej. Prometheus, Datadog)", example="Prometheus/Alertmanager")
    severity: str = Field(..., description="Severidad del incidente (P0, P1, P2)", example="P1")

# Esquema para cuando se crea un incidente (Input)
class IncidentCreate(IncidentBase):
    pass

# Esquema para cuando devolvemos el incidente (Output)
class IncidentResponse(IncidentBase):
    id: int
    status: str  # open, investigating, resolved
    created_at: datetime

    class Config:
        from_attributes = True