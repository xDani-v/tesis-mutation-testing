from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


class UsuarioRegistro(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_debe_tener_numero(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("La contrasena debe contener al menos un numero")
        return v


class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str


class UsuarioRespuesta(BaseModel):
    id: int
    email: str
    activo: bool
    creado_en: datetime

    class Config:
        from_attributes = True


class TokenRespuesta(BaseModel):
    access_token: str
    token_type: str = "bearer"
