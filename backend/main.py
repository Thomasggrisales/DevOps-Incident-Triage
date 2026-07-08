from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine
from app.db import models
from app.api.incidents import router as incident_router
from app.api.auth import router as auth_router

# Crear las tablas en la BD
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DevOps Incident Triage API",
    description="API para el sistema de gestión de incidentes",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluimos el router para auth.
app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

# Incluimos el router para incidents.
app.include_router(
    incident_router, 
    prefix="/incidents", 
    tags=["Incidents"]
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "¡La API está funcionando perfectamente!"}

