from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from models import Sala, Reserva
from schemas import SalaCrear, ReservaCrear


class SalaNoEncontradaError(Exception):
    pass


class SalaInactivaError(Exception):
    pass


class ConflictoHorarioError(Exception):
    pass


def crear_sala(db: Session, datos: SalaCrear) -> Sala:
    sala = Sala(nombre=datos.nombre, capacidad=datos.capacidad, activa=True)
    db.add(sala)
    db.commit()
    db.refresh(sala)
    return sala


def obtener_sala(db: Session, sala_id: int) -> Optional[Sala]:
    return db.query(Sala).filter(Sala.id == sala_id).first()


def desactivar_sala(db: Session, sala_id: int) -> Optional[Sala]:
    sala = obtener_sala(db, sala_id)
    if sala is None:
        return None
    sala.activa = False
    db.commit()
    db.refresh(sala)
    return sala


def existe_solapamiento(
    db: Session, sala_id: int, inicio: datetime, fin: datetime, excluir_reserva_id: Optional[int] = None
) -> bool:
    """
    Dos reservas se solapan si una empieza antes de que la otra termine
    y termina despues de que la otra empiece. Ignora reservas canceladas.
    """
    query = db.query(Reserva).filter(
        Reserva.sala_id == sala_id,
        Reserva.cancelada == False,  # noqa: E712
        Reserva.inicio < fin,
        Reserva.fin > inicio,
    )

    if excluir_reserva_id is not None:
        query = query.filter(Reserva.id != excluir_reserva_id)

    return query.first() is not None


def crear_reserva(db: Session, datos: ReservaCrear) -> Reserva:
    sala = obtener_sala(db, datos.sala_id)
    if sala is None:
        raise SalaNoEncontradaError(f"Sala {datos.sala_id} no existe")

    if not sala.activa:
        raise SalaInactivaError(f"Sala {datos.sala_id} esta inactiva")

    if existe_solapamiento(db, datos.sala_id, datos.inicio, datos.fin):
        raise ConflictoHorarioError("Ya existe una reserva en ese horario para esta sala")

    reserva = Reserva(
        sala_id=datos.sala_id,
        titulo=datos.titulo,
        inicio=datos.inicio,
        fin=datos.fin,
        cancelada=False,
    )
    db.add(reserva)
    db.commit()
    db.refresh(reserva)
    return reserva


def cancelar_reserva(db: Session, reserva_id: int) -> Optional[Reserva]:
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if reserva is None:
        return None
    reserva.cancelada = True
    db.commit()
    db.refresh(reserva)
    return reserva


def listar_reservas_de_sala(
    db: Session, sala_id: int, incluir_canceladas: bool = False
) -> list[Reserva]:
    query = db.query(Reserva).filter(Reserva.sala_id == sala_id)
    if not incluir_canceladas:
        query = query.filter(Reserva.cancelada == False)  # noqa: E712
    return query.order_by(Reserva.inicio.asc()).all()


def calcular_ocupacion_horas(db: Session, sala_id: int) -> float:
    """Suma las horas totales reservadas (no canceladas) para una sala."""
    reservas = listar_reservas_de_sala(db, sala_id, incluir_canceladas=False)
    total_segundos = sum(
        (r.fin - r.inicio).total_seconds() for r in reservas
    )
    return round(total_segundos / 3600, 2)
