from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base


class Sala(Base):
    __tablename__ = "salas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, unique=True)
    capacidad = Column(Integer, nullable=False)
    activa = Column(Boolean, default=True)


class Reserva(Base):
    __tablename__ = "reservas"

    id = Column(Integer, primary_key=True, index=True)
    sala_id = Column(Integer, nullable=False)
    titulo = Column(String, nullable=False)
    inicio = Column(DateTime, nullable=False)
    fin = Column(DateTime, nullable=False)
    cancelada = Column(Boolean, default=False)
    creada_en = Column(DateTime(timezone=True), server_default=func.now())
