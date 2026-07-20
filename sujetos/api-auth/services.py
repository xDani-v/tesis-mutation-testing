import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from sqlalchemy.orm import Session

from models import Usuario
from schemas import UsuarioRegistro

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "clave-secreta-de-desarrollo-cambiar-en-produccion")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

PBKDF2_ITERACIONES = 100_000


class EmailYaRegistradoError(Exception):
    pass


class UsuarioNoEncontradoError(Exception):
    pass


def hash_password(password: str) -> str:
    """
    Genera un hash seguro de la contrasena usando PBKDF2-HMAC-SHA256
    con una sal aleatoria. Formato de salida: "salt_hex$hash_hex"
    """
    sal = secrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), sal.encode("utf-8"), PBKDF2_ITERACIONES
    )
    return f"{sal}${hash_bytes.hex()}"


def verificar_password(password: str, password_hash: str) -> bool:
    """
    Verifica una contrasena contra su hash almacenado.
    Usa comparacion de tiempo constante para evitar timing attacks.
    """
    try:
        sal, hash_guardado = password_hash.split("$")
    except ValueError:
        return False

    hash_calculado = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), sal.encode("utf-8"), PBKDF2_ITERACIONES
    ).hex()

    return hmac.compare_digest(hash_calculado, hash_guardado)


def obtener_usuario_por_email(db: Session, email: str) -> Optional[Usuario]:
    return db.query(Usuario).filter(Usuario.email == email).first()


def obtener_usuario_por_id(db: Session, usuario_id: int) -> Optional[Usuario]:
    return db.query(Usuario).filter(Usuario.id == usuario_id).first()


def registrar_usuario(db: Session, datos: UsuarioRegistro) -> Usuario:
    existente = obtener_usuario_por_email(db, datos.email)
    if existente is not None:
        raise EmailYaRegistradoError(f"El email {datos.email} ya esta registrado")

    usuario = Usuario(
        email=datos.email,
        password_hash=hash_password(datos.password),
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def autenticar_usuario(db: Session, email: str, password: str) -> Optional[Usuario]:
    """
    Retorna el usuario si las credenciales son correctas y esta activo.
    Retorna None en cualquier otro caso (usuario no existe, inactivo,
    o contrasena incorrecta) sin revelar cual fue la causa especifica.
    """
    usuario = obtener_usuario_por_email(db, email)
    if usuario is None:
        return None

    if not usuario.activo:
        return None

    if not verificar_password(password, usuario.password_hash):
        return None

    return usuario


def desactivar_usuario(db: Session, usuario_id: int) -> Optional[Usuario]:
    usuario = obtener_usuario_por_id(db, usuario_id)
    if usuario is None:
        return None
    usuario.activo = False
    db.commit()
    db.refresh(usuario)
    return usuario


def crear_token_acceso(usuario_id: int, expira_minutos: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "iat": ahora,
        "exp": ahora + timedelta(minutes=expira_minutos),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> Optional[dict]:
    """
    Decodifica y valida un token JWT. Retorna el payload si es valido,
    o None si esta expirado, mal formado, o tiene firma invalida.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def obtener_usuario_desde_token(db: Session, token: str) -> Optional[Usuario]:
    payload = decodificar_token(token)
    if payload is None:
        return None

    usuario_id_str = payload.get("sub")
    if usuario_id_str is None:
        return None

    try:
        usuario_id = int(usuario_id_str)
    except ValueError:
        return None

    usuario = obtener_usuario_por_id(db, usuario_id)
    if usuario is None or not usuario.activo:
        return None

    return usuario
