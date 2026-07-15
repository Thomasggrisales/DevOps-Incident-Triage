from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager # NUEVO: Para el ciclo de vida
from app.db.weaviate_client import init_weaviate_schema # NUEVO: Tu función de Weaviate

from app.db.database import engine
from app.db import models
from app.api.incidents import router as incident_router
from app.api.auth import router as auth_router

# Crear las tablas en la BD relacional
models.Base.metadata.create_all(bind=engine)

# --- INICIO NUEVO: Manejador de ciclo de vida ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Evento de arranque
    try:
        print("Inicializando esquema de Weaviate...")
        init_weaviate_schema()
    except Exception as e:
        print(f"ADVERTENCIA: No se pudo conectar con Weaviate al arrancar: {e}")
    
    yield  # La aplicación se ejecuta normalmente aquí
    
    # Evento de apagado
    print("Apagando la aplicación...")
# --- FIN NUEVO ---

# NUEVO: Le pasamos el lifespan a la instancia de FastAPI
app = FastAPI(
    title="DevOps Incident Triage API",
    description="API para el sistema de gestión de incidentes",
    version="0.1.0",
    lifespan=lifespan 
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