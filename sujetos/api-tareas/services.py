from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from models import Tarea
from schemas import TareaCrear, TareaActualizar


def crear_tarea(db: Session, datos: TareaCrear) -> Tarea:
    tarea = Tarea(
        titulo=datos.titulo,
        descripcion=datos.descripcion,
        prioridad=datos.prioridad,
        completada=False,
    )
    db.add(tarea)
    db.commit()
    db.refresh(tarea)
    return tarea


def obtener_tarea(db: Session, tarea_id: int) -> Optional[Tarea]:
    return db.query(Tarea).filter(Tarea.id == tarea_id).first()


def listar_tareas(
    db: Session,
    completada: Optional[bool] = None,
    prioridad_minima: Optional[int] = None,
    ordenar_por_prioridad: bool = False,
) -> list[Tarea]:
    query = db.query(Tarea)

    if completada is not None:
        query = query.filter(Tarea.completada == completada)

    if prioridad_minima is not None:
        query = query.filter(Tarea.prioridad >= prioridad_minima)

    if ordenar_por_prioridad:
        query = query.order_by(desc(Tarea.prioridad))
    else:
        query = query.order_by(asc(Tarea.id))

    return query.all()


def actualizar_tarea(
    db: Session, tarea_id: int, datos: TareaActualizar
) -> Optional[Tarea]:
    tarea = obtener_tarea(db, tarea_id)
    if tarea is None:
        return None

    datos_dict = datos.model_dump(exclude_unset=True)
    for campo, valor in datos_dict.items():
        setattr(tarea, campo, valor)

    db.commit()
    db.refresh(tarea)
    return tarea


def eliminar_tarea(db: Session, tarea_id: int) -> bool:
    tarea = obtener_tarea(db, tarea_id)
    if tarea is None:
        return False

    db.delete(tarea)
    db.commit()
    return True


def marcar_completada(db: Session, tarea_id: int) -> Optional[Tarea]:
    tarea = obtener_tarea(db, tarea_id)
    if tarea is None:
        return None

    tarea.completada = True
    db.commit()
    db.refresh(tarea)
    return tarea


def calcular_resumen(db: Session) -> dict:
    """Calcula estadisticas de las tareas - buena fuente de mutantes logicos."""
    todas = db.query(Tarea).all()
    total = len(todas)
    completadas = sum(1 for t in todas if t.completada)
    pendientes = total - completadas

    if total == 0:
        porcentaje_completado = 0.0
    else:
        porcentaje_completado = round((completadas / total) * 100, 2)

    alta_prioridad_pendientes = sum(
        1 for t in todas if not t.completada and t.prioridad == 3
    )

    return {
        "total": total,
        "completadas": completadas,
        "pendientes": pendientes,
        "porcentaje_completado": porcentaje_completado,
        "alta_prioridad_pendientes": alta_prioridad_pendientes,
    }
