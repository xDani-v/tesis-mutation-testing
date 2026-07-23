from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import SalaCrear, SalaRespuesta, ReservaCrear, ReservaRespuesta
import services

router = APIRouter(tags=["reservas"])


@router.post("/salas", response_model=SalaRespuesta, status_code=status.HTTP_201_CREATED)
def crear_sala_endpoint(datos: SalaCrear, db: Session = Depends(get_db)):
    return services.crear_sala(db, datos)


@router.get("/salas/{sala_id}", response_model=SalaRespuesta)
def obtener_sala_endpoint(sala_id: int, db: Session = Depends(get_db)):
    sala = services.obtener_sala(db, sala_id)
    if sala is None:
        raise HTTPException(status_code=404, detail="Sala no encontrada")
    return sala


@router.patch("/salas/{sala_id}/desactivar", response_model=SalaRespuesta)
def desactivar_sala_endpoint(sala_id: int, db: Session = Depends(get_db)):
    sala = services.desactivar_sala(db, sala_id)
    if sala is None:
        raise HTTPException(status_code=404, detail="Sala no encontrada")
    return sala


@router.post("/reservas", response_model=ReservaRespuesta, status_code=status.HTTP_201_CREATED)
def crear_reserva_endpoint(datos: ReservaCrear, db: Session = Depends(get_db)):
    try:
        return services.crear_reserva(db, datos)
    except services.SalaNoEncontradaError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except services.SalaInactivaError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except services.ConflictoHorarioError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/reservas/{reserva_id}/cancelar", response_model=ReservaRespuesta)
def cancelar_reserva_endpoint(reserva_id: int, db: Session = Depends(get_db)):
    reserva = services.cancelar_reserva(db, reserva_id)
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return reserva


@router.get("/salas/{sala_id}/reservas", response_model=list[ReservaRespuesta])
def listar_reservas_endpoint(
    sala_id: int, incluir_canceladas: bool = False, db: Session = Depends(get_db)
):
    return services.listar_reservas_de_sala(db, sala_id, incluir_canceladas)


@router.get("/salas/{sala_id}/ocupacion")
def ocupacion_endpoint(sala_id: int, db: Session = Depends(get_db)):
    horas = services.calcular_ocupacion_horas(db, sala_id)
    return {"sala_id": sala_id, "horas_ocupadas": horas}
