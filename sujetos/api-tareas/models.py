from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class Tarea(Base):
    __tablename__ = "tareas"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
    completada = Column(Boolean, default=False)
    prioridad = Column(Integer, default=1)  # 1=baja, 2=media, 3=alta
    creada_en = Column(DateTime(timezone=True), server_default=func.now())
