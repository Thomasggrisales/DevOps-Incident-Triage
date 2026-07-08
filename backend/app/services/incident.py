from sqlalchemy.orm import Session
from app.db.models import Incident, StatusHistory
from app.schemas.incident import IncidentCreate
from app.db.weaviate_client import get_weaviate_client

def get_incidents(db: Session, skip: int = 0, limit: int = 100) -> list[Incident]:
    return db.query(Incident).offset(skip).limit(limit).all()

def get_incident_by_id(db: Session, incident_id: int) -> Incident | None:
    return db.query(Incident).filter(Incident.id == incident_id).first()

def create_new_incident(db: Session, incident_in: IncidentCreate) -> Incident:
    # 1. Preparar el incidente principal
    db_incident = Incident(
        title=incident_in.title,
        description=incident_in.description,
        source=incident_in.source,
        severity=incident_in.severity
    )
    db.add(db_incident)
    
    # Usamos flush() para que Postgres asigne el ID a db_incident, 
    # pero sin cerrar la transacción todavía.
    db.flush() 

    # 2. Preparar el registro del estado inicial
    db_history = StatusHistory(
        incident_id=db_incident.id, # Aquí ya tenemos el ID gracias al flush
        old_status=None,
        new_status=db_incident.status,
        changed_by="System_Init"
    )
    db.add(db_history)
    
    # 3. Guardar todo definitivamente en una sola transacción
    db.commit()
    db.refresh(db_incident)

    return db_incident

def update_incident_status(db: Session, incident_id: int, new_status: str) -> Incident | None:
    db_incident = get_incident_by_id(db, incident_id)
    if not db_incident:
        return None
    
    old_status = db_incident.status
    db_incident.status = new_status
    
    # Agregar registro al historial del cambio
    db_history = StatusHistory(
        incident_id=incident_id,
        old_status=old_status,
        new_status=new_status,
        changed_by="Operator"
    )
    db.add(db_history)
    
    # Como solo hay un commit aquí, la transacción ya es atómica
    db.commit()
    db.refresh(db_incident)
    
    return db_incident

def create_new_incident(db: Session, incident_in: IncidentCreate):
    # 1. Guardar en Postgres
    db_incident = models.Incident(
        title=incident_in.title,
        description=incident_in.description,
        source=incident_in.source,
        severity=incident_in.severity
    )
    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)
    
    # 2. Indexar en Weaviate
    try:
        client = get_weaviate_client()
        incidents = client.collections.get("Incident")
        
        # Ojo: asegúrate de que los campos coincidan con tu esquema de Weaviate
        incidents.insert({
            "incident_id": db_incident.id, 
            "title": db_incident.title,
            "description": db_incident.description,
            "status": str(db_incident.status) # Aseguramos que sea string
        })
    except Exception as e:
        # Es vital capturar esto para que no se caiga todo el proceso
        # si Weaviate está temporalmente caído
        print(f"Error indexando en Weaviate: {e}")
        
    return db_incident