from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class TareaBase(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=1000)
    prioridad: int = Field(default=1, ge=1, le=3)

    @field_validator("titulo")
    @classmethod
    def titulo_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El titulo no puede estar vacio o solo espacios")
        return v.strip()


class TareaCrear(TareaBase):
    pass


class TareaActualizar(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str] = Field(None, max_length=1000)
    completada: Optional[bool] = None
    prioridad: Optional[int] = Field(None, ge=1, le=3)


class TareaRespuesta(TareaBase):
    id: int
    completada: bool
    creada_en: datetime

    class Config:
        from_attributes = True
