from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import TareaCrear, TareaActualizar, TareaRespuesta
import services

router = APIRouter(prefix="/tareas", tags=["tareas"])


@router.post("/", response_model=TareaRespuesta, status_code=status.HTTP_201_CREATED)
def crear_tarea_endpoint(datos: TareaCrear, db: Session = Depends(get_db)):
    return services.crear_tarea(db, datos)


@router.get("/", response_model=list[TareaRespuesta])
def listar_tareas_endpoint(
    completada: Optional[bool] = None,
    prioridad_minima: Optional[int] = None,
    ordenar_por_prioridad: bool = False,
    db: Session = Depends(get_db),
):
    return services.listar_tareas(
        db, completada, prioridad_minima, ordenar_por_prioridad
    )


@router.get("/resumen")
def resumen_endpoint(db: Session = Depends(get_db)):
    return services.calcular_resumen(db)


@router.get("/{tarea_id}", response_model=TareaRespuesta)
def obtener_tarea_endpoint(tarea_id: int, db: Session = Depends(get_db)):
    tarea = services.obtener_tarea(db, tarea_id)
    if tarea is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return tarea


@router.patch("/{tarea_id}", response_model=TareaRespuesta)
def actualizar_tarea_endpoint(
    tarea_id: int, datos: TareaActualizar, db: Session = Depends(get_db)
):
    tarea = services.actualizar_tarea(db, tarea_id, datos)
    if tarea is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return tarea


@router.patch("/{tarea_id}/completar", response_model=TareaRespuesta)
def completar_tarea_endpoint(tarea_id: int, db: Session = Depends(get_db)):
    tarea = services.marcar_completada(db, tarea_id)
    if tarea is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return tarea


@router.delete("/{tarea_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_tarea_endpoint(tarea_id: int, db: Session = Depends(get_db)):
    eliminado = services.eliminar_tarea(db, tarea_id)
    if not eliminado:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
