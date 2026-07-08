from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.db import models
from app.core import security
# Asumiendo que en app.db.database tienes una función para obtener la sesión
from app.db.database import Base 

router = APIRouter()

# Dependencia para obtener la sesión de la base de datos
# Cambia esta importación si tu función para la sesión se llama diferente
def get_db():
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- SCHEMAS DE PYDANTIC (Para validar la entrada y salida de datos) ---
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "devops"

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

# --- ENDPOINTS ---

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Endpoint temporal para crear usuarios desde /docs"""
    # Verificar si el email ya existe
    user_exists = db.query(models.User).filter(models.User.email == user_in.email).first()
    if user_exists:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    # Crear el nuevo usuario con la contraseña encriptada
    new_user = models.User(
        email=user_in.email,
        name=user_in.name,
        role=user_in.role,
        hashed_password=security.get_password_hash(user_in.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": f"Usuario {new_user.name} creado con éxito"}


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """Endpoint real de inicio de sesión"""
    # 1. Buscar al usuario por correo
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos"
        )
    
    # 2. Verificar la contraseña
    if not security.verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_41_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos"
        )
    
    # 3. Generar el Token JWT utilizando el ID del usuario como 'sub'
    access_token = security.create_access_token(subject=user.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }