from datetime import timedelta

import jwt as pyjwt

from schemas import UsuarioRegistro
import services


def _registrar(db, email="user@test.com", password="clave1234"):
    return services.registrar_usuario(db, UsuarioRegistro(email=email, password=password))


# --- hash_password / verificar_password ---


def test_hash_password_no_devuelve_texto_plano():
    resultado = services.hash_password("miClave123")
    assert "miClave123" not in resultado
    assert "$" in resultado


def test_hash_password_genera_sales_distintas():
    hash1 = services.hash_password("mismaClave1")
    hash2 = services.hash_password("mismaClave1")
    # Aunque la contrasena sea igual, el hash completo debe diferir (sal aleatoria)
    assert hash1 != hash2


def test_verificar_password_correcta(db_session):
    hash_guardado = services.hash_password("claveSegura1")
    assert services.verificar_password("claveSegura1", hash_guardado) is True


def test_verificar_password_incorrecta():
    hash_guardado = services.hash_password("claveSegura1")
    assert services.verificar_password("claveIncorrecta1", hash_guardado) is False


def test_verificar_password_formato_invalido():
    assert services.verificar_password("cualquier", "hash-sin-separador") is False


# --- registrar_usuario ---


def test_registrar_usuario_exito(db_session):
    usuario = _registrar(db_session)
    assert usuario.id is not None
    assert usuario.email == "user@test.com"
    assert usuario.activo is True
    assert usuario.password_hash != "clave1234"


def test_registrar_usuario_email_duplicado(db_session):
    _registrar(db_session, email="dup@test.com")
    try:
        _registrar(db_session, email="dup@test.com")
        assert False, "Debio lanzar EmailYaRegistradoError"
    except services.EmailYaRegistradoError:
        pass


# --- obtener_usuario_por_email / por_id ---


def test_obtener_usuario_por_email_existente(db_session):
    creado = _registrar(db_session)
    encontrado = services.obtener_usuario_por_email(db_session, "user@test.com")
    assert encontrado is not None
    assert encontrado.id == creado.id


def test_obtener_usuario_por_email_no_existente(db_session):
    assert services.obtener_usuario_por_email(db_session, "nadie@test.com") is None


def test_obtener_usuario_por_id_no_existente(db_session):
    assert services.obtener_usuario_por_id(db_session, 999) is None


# --- autenticar_usuario ---


def test_autenticar_usuario_exito(db_session):
    _registrar(db_session, email="auth@test.com", password="claveBuena1")
    usuario = services.autenticar_usuario(db_session, "auth@test.com", "claveBuena1")
    assert usuario is not None
    assert usuario.email == "auth@test.com"


def test_autenticar_usuario_no_existente(db_session):
    assert services.autenticar_usuario(db_session, "fantasma@test.com", "clave1234") is None


def test_autenticar_usuario_password_incorrecta(db_session):
    _registrar(db_session, email="auth2@test.com", password="claveBuena1")
    assert services.autenticar_usuario(db_session, "auth2@test.com", "claveMala1") is None


def test_autenticar_usuario_inactivo(db_session):
    usuario = _registrar(db_session, email="inactivo@test.com", password="clave1234")
    services.desactivar_usuario(db_session, usuario.id)
    assert services.autenticar_usuario(db_session, "inactivo@test.com", "clave1234") is None


# --- desactivar_usuario ---


def test_desactivar_usuario_exito(db_session):
    usuario = _registrar(db_session)
    desactivado = services.desactivar_usuario(db_session, usuario.id)
    assert desactivado is not None
    assert desactivado.activo is False


def test_desactivar_usuario_no_existente(db_session):
    assert services.desactivar_usuario(db_session, 999) is None


# --- crear_token_acceso / decodificar_token ---


def test_crear_token_incluye_subject_correcto(db_session):
    usuario = _registrar(db_session)
    token = services.crear_token_acceso(usuario.id)
    payload = services.decodificar_token(token)
    assert payload is not None
    assert payload["sub"] == str(usuario.id)


def test_decodificar_token_invalido():
    assert services.decodificar_token("token-completamente-invalido") is None


def test_decodificar_token_firma_incorrecta(db_session):
    usuario = _registrar(db_session)
    # Genera un token firmado con una clave distinta a la real
    payload = {"sub": str(usuario.id)}
    token_falso = pyjwt.encode(payload, "clave-incorrecta", algorithm="HS256")
    assert services.decodificar_token(token_falso) is None


def test_token_expirado_no_es_valido(db_session):
    usuario = _registrar(db_session)
    # Crear un token que ya expiro (expira_minutos negativo)
    token_expirado = services.crear_token_acceso(usuario.id, expira_minutos=-1)
    assert services.decodificar_token(token_expirado) is None


# --- obtener_usuario_desde_token ---


def test_obtener_usuario_desde_token_valido(db_session):
    usuario = _registrar(db_session)
    token = services.crear_token_acceso(usuario.id)
    encontrado = services.obtener_usuario_desde_token(db_session, token)
    assert encontrado is not None
    assert encontrado.id == usuario.id


def test_obtener_usuario_desde_token_invalido(db_session):
    assert services.obtener_usuario_desde_token(db_session, "token-invalido") is None


def test_obtener_usuario_desde_token_usuario_inactivo(db_session):
    usuario = _registrar(db_session)
    token = services.crear_token_acceso(usuario.id)
    services.desactivar_usuario(db_session, usuario.id)
    assert services.obtener_usuario_desde_token(db_session, token) is None


# --- Tests de endpoints (integracion) ---


def test_endpoint_registro_y_login(client):
    respuesta_registro = client.post(
        "/auth/registro", json={"email": "nuevo@test.com", "password": "clave1234"}
    )
    assert respuesta_registro.status_code == 201

    respuesta_login = client.post(
        "/auth/login", json={"email": "nuevo@test.com", "password": "clave1234"}
    )
    assert respuesta_login.status_code == 200
    assert "access_token" in respuesta_login.json()


def test_endpoint_login_credenciales_invalidas(client):
    respuesta = client.post(
        "/auth/login", json={"email": "noexiste@test.com", "password": "clave1234"}
    )
    assert respuesta.status_code == 401


def test_endpoint_registro_password_sin_numero_422(client):
    respuesta = client.post(
        "/auth/registro", json={"email": "test@test.com", "password": "sinnumeros"}
    )
    assert respuesta.status_code == 422


def test_endpoint_me_requiere_token(client):
    respuesta = client.get("/auth/me")
    assert respuesta.status_code in (401, 403)


def test_endpoint_me_con_token_valido(client):
    client.post("/auth/registro", json={"email": "perfil@test.com", "password": "clave1234"})
    login = client.post(
        "/auth/login", json={"email": "perfil@test.com", "password": "clave1234"}
    )
    token = login.json()["access_token"]

    respuesta = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 200
    assert respuesta.json()["email"] == "perfil@test.com"
