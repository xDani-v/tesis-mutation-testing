from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class SalaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    capacidad: int = Field(..., ge=1, le=500)


class SalaCrear(SalaBase):
    pass


class SalaRespuesta(SalaBase):
    id: int
    activa: bool

    class Config:
        from_attributes = True


class ReservaBase(BaseModel):
    sala_id: int
    titulo: str = Field(..., min_length=1, max_length=200)
    inicio: datetime
    fin: datetime

    @model_validator(mode="after")
    def validar_rango_fechas(self):
        if self.fin <= self.inicio:
            raise ValueError("La fecha de fin debe ser posterior a la fecha de inicio")

        duracion_horas = (self.fin - self.inicio).total_seconds() / 3600
        if duracion_horas > 8:
            raise ValueError("Una reserva no puede durar mas de 8 horas")

        return self


class ReservaCrear(ReservaBase):
    pass


class ReservaRespuesta(ReservaBase):
    id: int
    cancelada: bool
    creada_en: datetime

    class Config:
        from_attributes = True
