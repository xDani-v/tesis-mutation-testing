from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from schemas import UsuarioRegistro, UsuarioLogin, UsuarioRespuesta, TokenRespuesta
import services

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


@router.post("/registro", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
def registro_endpoint(datos: UsuarioRegistro, db: Session = Depends(get_db)):
    try:
        return services.registrar_usuario(db, datos)
    except services.EmailYaRegistradoError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/login", response_model=TokenRespuesta)
def login_endpoint(datos: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = services.autenticar_usuario(db, datos.email, datos.password)
    if usuario is None:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")

    token = services.crear_token_acceso(usuario.id)
    return TokenRespuesta(access_token=token)


def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    usuario = services.obtener_usuario_desde_token(db, credenciales.credentials)
    if usuario is None:
        raise HTTPException(status_code=401, detail="Token invalido o expirado")
    return usuario


@router.get("/me", response_model=UsuarioRespuesta)
def perfil_endpoint(usuario=Depends(obtener_usuario_actual)):
    return usuario


@router.patch("/usuarios/{usuario_id}/desactivar", response_model=UsuarioRespuesta)
def desactivar_usuario_endpoint(usuario_id: int, db: Session = Depends(get_db)):
    usuario = services.desactivar_usuario(db, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario
