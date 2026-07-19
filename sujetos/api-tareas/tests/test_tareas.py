def test_crear_tarea(client):
    respuesta = client.post(
        "/tareas/", json={"titulo": "Comprar pan", "prioridad": 2}
    )
    assert respuesta.status_code == 201
    data = respuesta.json()
    assert data["titulo"] == "Comprar pan"
    assert data["prioridad"] == 2
    assert data["completada"] is False


def test_crear_tarea_titulo_vacio_falla(client):
    respuesta = client.post("/tareas/", json={"titulo": "   "})
    assert respuesta.status_code == 422


def test_crear_tarea_prioridad_default(client):
    respuesta = client.post("/tareas/", json={"titulo": "Sin prioridad"})
    assert respuesta.status_code == 201
    assert respuesta.json()["prioridad"] == 1


def test_crear_tarea_prioridad_fuera_de_rango_falla(client):
    respuesta = client.post(
        "/tareas/", json={"titulo": "Prioridad invalida", "prioridad": 5}
    )
    assert respuesta.status_code == 422


def test_obtener_tarea_existente(client):
    creada = client.post("/tareas/", json={"titulo": "Tarea X"}).json()
    respuesta = client.get(f"/tareas/{creada['id']}")
    assert respuesta.status_code == 200
    assert respuesta.json()["titulo"] == "Tarea X"


def test_obtener_tarea_inexistente_404(client):
    respuesta = client.get("/tareas/9999")
    assert respuesta.status_code == 404


def test_listar_tareas_vacio(client):
    respuesta = client.get("/tareas/")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_listar_tareas_orden_por_id_por_defecto(client):
    client.post("/tareas/", json={"titulo": "Primera", "prioridad": 1})
    client.post("/tareas/", json={"titulo": "Segunda", "prioridad": 3})
    respuesta = client.get("/tareas/")
    data = respuesta.json()
    assert data[0]["titulo"] == "Primera"
    assert data[1]["titulo"] == "Segunda"


def test_listar_tareas_ordenar_por_prioridad(client):
    client.post("/tareas/", json={"titulo": "Baja", "prioridad": 1})
    client.post("/tareas/", json={"titulo": "Alta", "prioridad": 3})
    respuesta = client.get("/tareas/?ordenar_por_prioridad=true")
    data = respuesta.json()
    assert data[0]["prioridad"] == 3
    assert data[1]["prioridad"] == 1


def test_listar_tareas_filtro_completada(client):
    creada = client.post("/tareas/", json={"titulo": "A completar"}).json()
    client.patch(f"/tareas/{creada['id']}/completar")
    client.post("/tareas/", json={"titulo": "Pendiente"})

    respuesta = client.get("/tareas/?completada=true")
    data = respuesta.json()
    assert len(data) == 1
    assert data[0]["titulo"] == "A completar"


def test_listar_tareas_filtro_prioridad_minima(client):
    client.post("/tareas/", json={"titulo": "Baja", "prioridad": 1})
    client.post("/tareas/", json={"titulo": "Alta", "prioridad": 3})

    respuesta = client.get("/tareas/?prioridad_minima=3")
    data = respuesta.json()
    assert len(data) == 1
    assert data[0]["titulo"] == "Alta"


def test_actualizar_tarea_parcial(client):
    creada = client.post("/tareas/", json={"titulo": "Original"}).json()
    respuesta = client.patch(
        f"/tareas/{creada['id']}", json={"titulo": "Modificada"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["titulo"] == "Modificada"


def test_actualizar_tarea_inexistente_404(client):
    respuesta = client.patch("/tareas/9999", json={"titulo": "No existe"})
    assert respuesta.status_code == 404


def test_completar_tarea(client):
    creada = client.post("/tareas/", json={"titulo": "Por completar"}).json()
    respuesta = client.patch(f"/tareas/{creada['id']}/completar")
    assert respuesta.status_code == 200
    assert respuesta.json()["completada"] is True


def test_completar_tarea_inexistente_404(client):
    respuesta = client.patch("/tareas/9999/completar")
    assert respuesta.status_code == 404


def test_eliminar_tarea(client):
    creada = client.post("/tareas/", json={"titulo": "A borrar"}).json()
    respuesta = client.delete(f"/tareas/{creada['id']}")
    assert respuesta.status_code == 204

    verificacion = client.get(f"/tareas/{creada['id']}")
    assert verificacion.status_code == 404


def test_eliminar_tarea_inexistente_404(client):
    respuesta = client.delete("/tareas/9999")
    assert respuesta.status_code == 404


def test_resumen_sin_tareas(client):
    respuesta = client.get("/tareas/resumen")
    data = respuesta.json()
    assert data["total"] == 0
    assert data["completadas"] == 0
    assert data["pendientes"] == 0
    assert data["porcentaje_completado"] == 0.0
    assert data["alta_prioridad_pendientes"] == 0


def test_resumen_con_tareas_mixtas(client):
    t1 = client.post("/tareas/", json={"titulo": "Uno", "prioridad": 3}).json()
    client.post("/tareas/", json={"titulo": "Dos", "prioridad": 1})
    client.patch(f"/tareas/{t1['id']}/completar")

    respuesta = client.get("/tareas/resumen")
    data = respuesta.json()
    assert data["total"] == 2
    assert data["completadas"] == 1
    assert data["pendientes"] == 1
    assert data["porcentaje_completado"] == 50.0


def test_resumen_alta_prioridad_pendiente(client):
    client.post("/tareas/", json={"titulo": "Urgente", "prioridad": 3})
    client.post("/tareas/", json={"titulo": "No urgente", "prioridad": 1})

    respuesta = client.get("/tareas/resumen")
    assert respuesta.json()["alta_prioridad_pendientes"] == 1


def test_health_check(client):
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}
