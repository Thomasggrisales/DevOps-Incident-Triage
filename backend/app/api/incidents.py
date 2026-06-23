from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime
from app.schemas.incident import IncidentCreate, IncidentResponse

router = APIRouter(prefix="/incidents", tags=["Incidents"])

# Base de datos simulada en memoria (Temporal hasta hacer el Ticket #5)
INCIDENTS_DB = []
id_counter = 1

@router.post("/", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(incident_in: IncidentCreate):
    """
    Crea un nuevo incidente en el sistema.
    """
    global id_counter
    new_incident = {
        "id": id_counter,
        **incident_in.model_dump(),  # Convertimos el esquema Pydantic a diccionario
        "status": "open",
        "created_at": datetime.now()
    }
    INCIDENTS_DB.append(new_incident)
    id_counter += 1
    return new_incident

@router.get("/{id}", response_model=IncidentResponse)
def get_incident(id: int):
    """
    Obtiene los detalles de un incidente específico por su ID.
    """
    for incident in INCIDENTS_DB:
        if incident["id"] == id:
            return incident
    raise HTTPException(status_code=404, detail=f"El incidente con ID {id} no existe.")

@router.get("/", response_model=List[IncidentResponse])
def list_incidents():
    """
    Lista todos los incidentes registrados.
    """
    return INCIDENTS_DB