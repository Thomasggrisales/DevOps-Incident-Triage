from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.schemas.incident import IncidentCreate, IncidentResponse
from app.services import incident as incident_service
from app.db.database import get_db

router = APIRouter(prefix="/incidents", tags=["Incidents"])

@router.post("/", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(incident_in: IncidentCreate, db: Session = Depends(get_db)):
    """
    Crea un nuevo incidente en el sistema y registra su estado inicial en el historial.
    """
    return incident_service.create_new_incident(db=db, incident_in=incident_in)

@router.get("/", response_model=List[IncidentResponse])
def list_incidents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lista todos los incidentes registrados en el sistema de forma paginada.
    """
    return incident_service.get_incidents(db=db, skip=skip, limit=limit)

@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    """
    Obtiene los detalles completos de un incidente específico a partir de su ID.
    """
    db_incident = incident_service.get_incident_by_id(db=db, incident_id=incident_id)
    if not db_incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"El incidente con ID {incident_id} no existe."
        )
    return db_incident