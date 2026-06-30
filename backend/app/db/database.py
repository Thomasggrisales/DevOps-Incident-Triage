import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Carga el archivo .env por si ejecutas el script localmente fuera de Docker
load_dotenv()

# Lee la URL desde el entorno; si no existe, usa una por defecto (local)
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres_user:postgres_password123@localhost:5432/devops_incident_db"
)

# Creamos el motor de SQLAlchemy para PostgreSQL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()