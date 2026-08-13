from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import timedelta
import logging
from app.db import models
from app.core import security
from app.db.database import get_db

logger = logging.getLogger(__name__)

# Validez del token de recuperación de contraseña (30 minutos).
RESET_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()

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

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = None
    expires_in_minutes: int = RESET_TOKEN_EXPIRE_MINUTES

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

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
            status_code=status.HTTP_401_UNAUTHORIZED,
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


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(user_in: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Genera un token de recuperación de contraseña para el correo indicado.

    Por seguridad no se revela si el correo existe (evita enumeración de usuarios):
    siempre se devuelve el mismo mensaje. Mientras no haya infraestructura de
    correo, el token se devuelve en la respuesta para poder completar el flujo.
    """
    user = db.query(models.User).filter(models.User.email == user_in.email).first()

    if not user or not user.is_active:
        logger.info("Solicitud de recuperación para correo no registrado o inactivo.")
        return ForgotPasswordResponse(
            message="Si el correo está registrado, hemos enviado las instrucciones."
        )

    reset_token = security.create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
        token_type="password_reset",
    )
    logger.info("Token de recuperación generado para el usuario %s.", user.email)
    return ForgotPasswordResponse(
        message="Si el correo está registrado, hemos enviado las instrucciones.",
        reset_token=reset_token,
    )


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Cambia la contraseña usando el token de recuperación (válido 30 min)."""
    payload = security.decode_token(request.token)
    if not payload or payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de recuperación inválido o expirado.",
        )

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de recuperación inválido o expirado.",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de recuperación inválido o expirado.",
        )

    user.hashed_password = security.get_password_hash(request.new_password)
    db.commit()
    logger.info("Contraseña restablecida para el usuario %s.", user.email)
    return {"message": "Contraseña actualizada correctamente."}