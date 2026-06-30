from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base

# Función auxiliar para la fecha actual en UTC
def get_utc_now():
    return datetime.now(timezone.utc)

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=False)
    source = Column(String, nullable=False)  
    severity = Column(String, nullable=False)  
    status = Column(String, default="open")  
    created_at = Column(DateTime, default=get_utc_now)

    history = relationship("StatusHistory", back_populates="incident", cascade="all, delete-orphan")


class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)
    changed_at = Column(DateTime, default=get_utc_now)
    changed_by = Column(String, default="System_AI")  

    incident = relationship("Incident", back_populates="history")