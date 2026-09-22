from fastapi import status
from tests.test_espacios import obtener_token_admin, obtener_token_usuario_comun
from modelos import EspacioDB, UsuarioDB
from sqlmodel import Session

def test_crear_reserva_exitosa(client):
    token_admin = obtener_token_admin(client)
    res_espacio = client.post(
        "/espacios",
        json={
            "nombre": "sala de Reuniones A",
            "capacidad": 6,
            "precio_por_hora": 2000.0,
            "esta_disponible": True,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )

    id_espacio_creado = res_espacio.json()["id_espacio"]

    token_usuario = obtener_token_usuario_comun(client)

    response = client.post(
        "/reservas",
        json={
            "id_espacio": id_espacio_creado,
            "horas": 3,
        },
        headers={"Authorization": f"Bearer {token_usuario}"},
    )

    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert data["id_espacio"] == id_espacio_creado
    assert data["horas"] == 3
    assert data["total"] == 6000.0
    assert "id_reserva" in data
    assert "id_usuario" in data


def test_crear_reserva_id_espacio_invalido(client):
    # 1. Obtenemos el token del usuario que intentará reservar
    token_usuario = obtener_token_usuario_comun(client)
    headers = {"Authorization": f"Bearer {token_usuario}"}

    # 2. Intentamos reservar el espacio 999 que no existe
    response = client.post(
        "/reservas",
        json={
            "id_espacio": 999,
            "horas": 3,
        },
        headers=headers,
    )

    # 3. Comprobamos que responda 404 y devuelva el mensaje esperado
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "El espacio no existe"

def test_crear_reserva_sin_token_falla(client):
    """hacemos la peticion directamente sin incluir el parámetro 'headers'"""
    response = client.post(
        "/reservas",
        json={
            "id_espacio": 1,
            "horas": 2,
        }
    )

    """ fastAPI/Starlette frena la petición automaticamente y devuelve 401"""
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_crear_reserva_espacio_no_disponible(client):
    
    # 1. Necesitamos crear un espacio NO disponible usando el token de admin
    nombre_espacio = "Sala B"
    token_admin = obtener_token_admin(client)
    res_espacio = client.post(
        "/espacios",
        json={
            "nombre": nombre_espacio,
            "capacidad": 10,
            "precio_por_hora": 3000.0,
            "esta_disponible": False,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    id_espacio_creado = res_espacio.json()["id_espacio"]

    # 2. Token del usuario común que intentará la reserva
    token_usuario = obtener_token_usuario_comun(client)

    # 3. Intentar la reserva
    response = client.post(
        "/reservas",
        json={
            "id_espacio": id_espacio_creado,
            "horas": 3,
        },
        headers={"Authorization": f"Bearer {token_usuario}"},
    )

    # 4. Verificar que se rechace con 400 Bad Request
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == f"el espacio '{nombre_espacio}' no esta disponible para reservar."

def test_cancelar_reserva_exitoso_y_libera_espacio(client, session: Session):
    token_admin = obtener_token_admin(client)
    res_espacio = client.post(
        "/espacios",
        json={
            "nombre": "Sala C - Cancelación",
            "capacidad": 4,
            "precio_por_hora": 1000.0,
            "esta_disponible": True,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    id_espacio = res_espacio.json()["id_espacio"]

    token_usuario = obtener_token_usuario_comun(client)
    res_reserva = client.post(
        "/reservas",
        json={"id_espacio": id_espacio, "horas": 2},
        headers={"Authorization": f"Bearer {token_usuario}"},
    )
    id_reserva = res_reserva.json()["id_reserva"]

    res_cancelar = client.delete(
        f"/reservas/{id_reserva}",
        headers={"Authorization": f"Bearer {token_usuario}"},
    )


    assert res_cancelar.status_code == status.HTTP_200_OK

    # Consultamos la BD directamente para verificar que se volvió a poner en True
    session.expire_all()  # Forzamos recarga desde la BD
    espacio_db = session.get(EspacioDB, id_espacio)

    assert espacio_db is not None
    assert espacio_db.esta_disponible is True


def test_cancelar_reserva_otro_usuario_falla(client):
    # 1. Usuario 1 crea la reserva
    token_admin = obtener_token_admin(client)
    res_espacio = client.post(
        "/espacios",
        json={
            "nombre": "Sala D",
            "capacidad": 8,
            "precio_por_hora": 1200.0,
            "esta_disponible": True,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    id_espacio = res_espacio.json()["id_espacio"]

    token_usuario1 = obtener_token_usuario_comun(client)
    res_reserva = client.post(
        "/reservas",
        json={"id_espacio": id_espacio, "horas": 1},
        headers={"Authorization": f"Bearer {token_usuario1}"},
    )
    id_reserva = res_reserva.json()["id_reserva"]

    # Creamos un Usuario 2
    client.post(
        "/usuarios",
        json={
            "nombre": "Usuario Intruso",
            "email": "intruso@example.com",
            "password": "password123",
            "es_admin": False,
        },
    )
    res_login2 = client.post(
        "/login",
        json={"email": "intruso@example.com", "password": "password123"},
    )
    token_usuario2 = res_login2.json()["access_token"]

    # 2.  Usuario 2 intenta cancelar la reserva del Usuario 1
    res_cancelar = client.delete(
        f"/reservas/{id_reserva}",
        headers={"Authorization": f"Bearer {token_usuario2}"},
    )

    # 3. Debe ser rechazado por falta de permisos (403)
    assert res_cancelar.status_code == status.HTTP_403_FORBIDDEN
    assert (
        res_cancelar.json()["detail"]
        == "No tienes permisos para cancelar esta reserva"
    )


def test_eliminar_usuario_exitoso(client, session: Session):
    # 1. Token Admin + Usuario a eliminar)
    token_admin = obtener_token_admin(client)

    # Creamos un usuario común para luego eliminarlo
    res_usuario = client.post(
        "/usuarios",
        json={
            "nombre": "Usuario a Borrar",
            "email": "borrar@example.com",
            "password": "secretpassword",
            "es_admin": False,
        },
    )
    id_usuario = res_usuario.json()["id_usuario"]


    # 2.  DELETE enviando el ID en la URL
   
    res_eliminar = client.delete(
        f"/usuarios/{id_usuario}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )

 
    # 3. Verificar respuesta HTTP y confirmación en BD
    
    assert res_eliminar.status_code == status.HTTP_200_OK

    # Verificamos directamente en la BD que el usuario ya no exista
    session.expire_all()
    usuario_db = session.get(UsuarioDB, id_usuario)

    assert usuario_db is None

def test_modificar_reserva_patch_exitoso(client):
    # -------------------------------------------------------------------------
    # 1. ARRANGE (Espacio + Reserva inicial)
    # -------------------------------------------------------------------------
    token_admin = obtener_token_admin(client)
    res_espacio = client.post(
        "/espacios",
        json={
            "nombre": "Sala Conferencia",
            "capacidad": 20,
            "precio_por_hora": 5000.0,
            "esta_disponible": True,
        },
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    id_espacio = res_espacio.json()["id_espacio"]

    token_usuario1 = obtener_token_usuario_comun(client)
    headers_usuario = {"Authorization": f"Bearer {token_usuario1}"}

    res_reserva = client.post(
        "/reservas",
        json={"id_espacio": id_espacio, "horas": 2},
        headers=headers_usuario,
    )
    id_reserva = res_reserva.json()["id_reserva"]

    # -------------------------------------------------------------------------
    # 2. ACT (Modificar las horas a 4 usando PATCH y el token del usuario)
    # -------------------------------------------------------------------------
    res_patch = client.patch(
        f"/reservas/{id_reserva}",
        json={"horas": 4},
        headers=headers_usuario,
    )

    # -------------------------------------------------------------------------
    # 3. ASSERT (Verificar 200 OK, actualización de horas y recalculito de total)
    # -------------------------------------------------------------------------
    assert res_patch.status_code == status.HTTP_200_OK

    data_actualizada = res_patch.json()

    # Verificamos que las horas hayan cambiado a 4
    assert data_actualizada["horas"] == 4

    # Verificamos que el total se haya recalculado: 4 horas * $5000 = $20000
    assert data_actualizada["total"] == 20000.0

