from datetime import datetime, timedelta

from models import Sala, Reserva
from schemas import SalaCrear, ReservaCrear
import services


def _crear_sala_directa(db, nombre="Sala A", capacidad=10, activa=True):
    sala = Sala(nombre=nombre, capacidad=capacidad, activa=activa)
    db.add(sala)
    db.commit()
    db.refresh(sala)
    return sala


def test_crear_sala(db_session):
    sala = services.crear_sala(db_session, SalaCrear(nombre="Sala 1", capacidad=8))
    assert sala.id is not None
    assert sala.nombre == "Sala 1"
    assert sala.capacidad == 8
    assert sala.activa is True


def test_obtener_sala_existente(db_session):
    sala = _crear_sala_directa(db_session)
    encontrada = services.obtener_sala(db_session, sala.id)
    assert encontrada is not None
    assert encontrada.nombre == "Sala A"


def test_obtener_sala_inexistente(db_session):
    assert services.obtener_sala(db_session, 999) is None


def test_desactivar_sala(db_session):
    sala = _crear_sala_directa(db_session)
    resultado = services.desactivar_sala(db_session, sala.id)
    assert resultado is not None
    assert resultado.activa is False


def test_desactivar_sala_inexistente(db_session):
    assert services.desactivar_sala(db_session, 999) is None


def test_crear_reserva_exito(db_session):
    sala = _crear_sala_directa(db_session)
    inicio = datetime(2026, 8, 1, 9, 0)
    fin = datetime(2026, 8, 1, 10, 0)
    reserva = services.crear_reserva(
        db_session,
        ReservaCrear(sala_id=sala.id, titulo="Reunion", inicio=inicio, fin=fin),
    )
    assert reserva.id is not None
    assert reserva.cancelada is False


def test_crear_reserva_sala_inexistente(db_session):
    inicio = datetime(2026, 8, 1, 9, 0)
    fin = datetime(2026, 8, 1, 10, 0)
    try:
        services.crear_reserva(
            db_session,
            ReservaCrear(sala_id=999, titulo="X", inicio=inicio, fin=fin),
        )
        assert False, "Debio lanzar SalaNoEncontradaError"
    except services.SalaNoEncontradaError:
        pass


def test_crear_reserva_sala_inactiva(db_session):
    sala = _crear_sala_directa(db_session, activa=False)
    inicio = datetime(2026, 8, 1, 9, 0)
    fin = datetime(2026, 8, 1, 10, 0)
    try:
        services.crear_reserva(
            db_session,
            ReservaCrear(sala_id=sala.id, titulo="X", inicio=inicio, fin=fin),
        )
        assert False, "Debio lanzar SalaInactivaError"
    except services.SalaInactivaError:
        pass


def test_existe_solapamiento_reservas_identicas(db_session):
    sala = _crear_sala_directa(db_session)
    inicio = datetime(2026, 8, 1, 9, 0)
    fin = datetime(2026, 8, 1, 10, 0)
    services.crear_reserva(
        db_session, ReservaCrear(sala_id=sala.id, titulo="R1", inicio=inicio, fin=fin)
    )
    assert services.existe_solapamiento(db_session, sala.id, inicio, fin) is True


def test_existe_solapamiento_parcial_inicio(db_session):
    sala = _crear_sala_directa(db_session)
    services.crear_reserva(
        db_session,
        ReservaCrear(
            sala_id=sala.id,
            titulo="R1",
            inicio=datetime(2026, 8, 1, 9, 0),
            fin=datetime(2026, 8, 1, 11, 0),
        ),
    )
    # Nueva reserva empieza antes y termina dentro del rango existente
    solapa = services.existe_solapamiento(
        db_session, sala.id, datetime(2026, 8, 1, 8, 0), datetime(2026, 8, 1, 9, 30)
    )
    assert solapa is True


def test_no_existe_solapamiento_horarios_adyacentes(db_session):
    sala = _crear_sala_directa(db_session)
    services.crear_reserva(
        db_session,
        ReservaCrear(
            sala_id=sala.id,
            titulo="R1",
            inicio=datetime(2026, 8, 1, 9, 0),
            fin=datetime(2026, 8, 1, 10, 0),
        ),
    )
    # Empieza justo cuando la anterior termina -> NO debe solapar
    solapa = services.existe_solapamiento(
        db_session, sala.id, datetime(2026, 8, 1, 10, 0), datetime(2026, 8, 1, 11, 0)
    )
    assert solapa is False


def test_no_existe_solapamiento_reserva_cancelada(db_session):
    sala = _crear_sala_directa(db_session)
    reserva = services.crear_reserva(
        db_session,
        ReservaCrear(
            sala_id=sala.id,
            titulo="R1",
            inicio=datetime(2026, 8, 1, 9, 0),
            fin=datetime(2026, 8, 1, 10, 0),
        ),
    )
    services.cancelar_reserva(db_session, reserva.id)

    solapa = services.existe_solapamiento(
        db_session, sala.id, datetime(2026, 8, 1, 9, 0), datetime(2026, 8, 1, 10, 0)
    )
    assert solapa is False


def test_crear_reserva_conflicto_horario(db_session):
    sala = _crear_sala_directa(db_session)
    services.crear_reserva(
        db_session,
        ReservaCrear(
            sala_id=sala.id,
            titulo="R1",
            inicio=datetime(2026, 8, 1, 9, 0),
            fin=datetime(2026, 8, 1, 10, 0),
        ),
    )
    try:
        services.crear_reserva(
            db_session,
            ReservaCrear(
                sala_id=sala.id,
                titulo="R2",
                inicio=datetime(2026, 8, 1, 9, 30),
                fin=datetime(2026, 8, 1, 10, 30),
            ),
        )
        assert False, "Debio lanzar ConflictoHorarioError"
    except services.ConflictoHorarioError:
        pass


def test_existe_solapamiento_excluir_reserva_propia(db_session):
    sala = _crear_sala_directa(db_session)
    reserva = services.crear_reserva(
        db_session,
        ReservaCrear(
            sala_id=sala.id,
            titulo="R1",
            inicio=datetime(2026, 8, 1, 9, 0),
            fin=datetime(2026, 8, 1, 10, 0),
        ),
    )
    # Al excluir su propio ID, no debe detectarse solapamiento consigo misma
    solapa = services.existe_solapamiento(
        db_session,
        sala.id,
        datetime(2026, 8, 1, 9, 0),
        datetime(2026, 8, 1, 10, 0),
        excluir_reserva_id=reserva.id,
    )
    assert solapa is False


def test_cancelar_reserva(db_session):
    sala = _crear_sala_directa(db_session)
    reserva = services.crear_reserva(
        db_session,
        ReservaCrear(
            sala_id=sala.id,
            titulo="R1",
            inicio=datetime(2026, 8, 1, 9, 0),
            fin=datetime(2026, 8, 1, 10, 0),
        ),
    )
    cancelada = services.cancelar_reserva(db_session, reserva.id)
    assert cancelada.cancelada is True


def test_cancelar_reserva_inexistente(db_session):
    assert services.cancelar_reserva(db_session, 999) is None


def test_listar_reservas_excluye_canceladas_por_defecto(db_session):
    sala = _crear_sala_directa(db_session)
    r1 = services.crear_reserva(
        db_session,
        ReservaCrear(
            sala_id=sala.id,
            titulo="R1",
            inicio=datetime(2026, 8, 1, 9, 0),
            fin=datetime(2026, 8, 1, 10, 0),
        ),
    )
    services.crear_reserva(
        db_session,
        ReservaCrear(
            sala_id=sala.id,
            titulo="R2",
            inicio=datetime(2026, 8, 1, 11, 0),
            fin=datetime(2026, 8, 1, 12, 0),
        ),
    )
    services.cancelar_reserva(db_session, r1.id)

    activas = services.listar_reservas_de_sala(db_session, sala.id)
    assert len(activas) == 1
    assert activas[0].titulo == "R2"

    todas = services.listar_reservas_de_sala(db_session, sala.id, incluir_canceladas=True)
    assert len(todas) == 2


def test_listar_reservas_orden_por_inicio(db_session):
    sala = _crear_sala_directa(db_session)
    services.crear_reserva(
        db_session,
        ReservaCrear(
            sala_id=sala.id,
            titulo="Tarde",
            inicio=datetime(2026, 8, 1, 15, 0),
            fin=datetime(2026, 8, 1, 16, 0),
        ),
    )
    services.crear_reserva(
        db_session,
        ReservaCrear(
            sala_id=sala.id,
            titulo="Manana",
            inicio=datetime(2026, 8, 1, 8, 0),
            fin=datetime(2026, 8, 1, 9, 0),
        ),
    )
    reservas = services.listar_reservas_de_sala(db_session, sala.id)
    assert reservas[0].titulo == "Manana"
    assert reservas[1].titulo == "Tarde"


def test_calcular_ocupacion_horas_vacio(db_session):
    sala = _crear_sala_directa(db_session)
    assert services.calcular_ocupacion_horas(db_session, sala.id) == 0.0


def test_calcular_ocupacion_horas_con_reservas(db_session):
    sala = _crear_sala_directa(db_session)
    services.crear_reserva(
        db_session,
        ReservaCrear(
            sala_id=sala.id,
            titulo="R1",
            inicio=datetime(2026, 8, 1, 9, 0),
            fin=datetime(2026, 8, 1, 11, 0),  # 2 horas
        ),
    )
    services.crear_reserva(
        db_session,
        ReservaCrear(
            sala_id=sala.id,
            titulo="R2",
            inicio=datetime(2026, 8, 1, 14, 0),
            fin=datetime(2026, 8, 1, 14, 30),  # 0.5 horas
        ),
    )
    assert services.calcular_ocupacion_horas(db_session, sala.id) == 2.5


def test_calcular_ocupacion_ignora_canceladas(db_session):
    sala = _crear_sala_directa(db_session)
    reserva = services.crear_reserva(
        db_session,
        ReservaCrear(
            sala_id=sala.id,
            titulo="R1",
            inicio=datetime(2026, 8, 1, 9, 0),
            fin=datetime(2026, 8, 1, 11, 0),
        ),
    )
    services.cancelar_reserva(db_session, reserva.id)
    assert services.calcular_ocupacion_horas(db_session, sala.id) == 0.0


def test_endpoint_health(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_endpoint_crear_reserva_conflicto_devuelve_409(client):
    sala = client.post("/salas", json={"nombre": "Sala X", "capacidad": 5}).json()
    payload = {
        "sala_id": sala["id"],
        "titulo": "R1",
        "inicio": "2026-08-01T09:00:00",
        "fin": "2026-08-01T10:00:00",
    }
    client.post("/reservas", json=payload)
    respuesta = client.post("/reservas", json=payload)
    assert respuesta.status_code == 409


def test_endpoint_reserva_duracion_excesiva_422(client):
    sala = client.post("/salas", json={"nombre": "Sala Y", "capacidad": 5}).json()
    payload = {
        "sala_id": sala["id"],
        "titulo": "Maraton",
        "inicio": "2026-08-01T08:00:00",
        "fin": "2026-08-01T18:00:00",  # 10 horas, excede el limite de 8
    }
    respuesta = client.post("/reservas", json=payload)
    assert respuesta.status_code == 422
