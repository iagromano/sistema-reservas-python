from fastapi import status
from modelos import EspacioDB
from sqlmodel import Session


def obtener_token_admin(client) -> str:
    """Helper para crear un usuario admin y obtener su token JWT."""
    client.post(
        "/usuarios",
        json={
            "nombre": "Admin",
            "email": "admin@example.com",
            "password": "adminpassword",
            "es_admin": True,
        },
    )
    res = client.post(
        "/login",
        json={"email": "admin@example.com", "password": "adminpassword"},
    )
    return res.json()["access_token"]


def obtener_token_usuario_comun(client) -> str:
    """Helper para crear un usuario estándar y obtener su token JWT."""
    client.post(
        "/usuarios",
        json={
            "nombre": "Usuario Comun",
            "email": "user@example.com",
            "password": "userpassword",
            "es_admin": False,
        },
    )
    res = client.post(
        "/login",
        json={"email": "user@example.com", "password": "userpassword"},
    )
    return res.json()["access_token"]


def test_crear_espacio_como_admin(client):
    """Valida que un administrador pueda crear un espacio correctamente."""
    token = obtener_token_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/espacios",
        json={
            "nombre": "Sala A",
            "capacidad": 10,
            "precio_por_hora": 1500.0,
            "esta_disponible": True,
        },
        headers=headers,
    )

    data = response.json()
    assert response.status_code == status.HTTP_201_CREATED
    assert data["nombre"] == "Sala A"
    assert "id_espacio" in data


def test_crear_espacio_sin_permisos_falla(client):
    """Valida que un usuario común NO pueda crear un espacio (403 Forbidden)."""
    token = obtener_token_usuario_comun(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/espacios",
        json={
            "nombre": "Sala B",
            "capacidad": 5,
            "precio_por_hora": 1000.0,
            "esta_disponible": True,
        },
        headers=headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_listar_espacios_publico(client):
    """Valida que la lista de espacios sea accesible públicamente sin autenticación."""
    response = client.get("/espacios")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


def test_eliminar_espacio_admin_exitoso(client, session: Session):
    # 1. Token Admin + espacio a eliminar
    token_admin = obtener_token_admin(client)
    headers = {"Authorization": f"Bearer {token_admin}"}

    # Creamos un espacio para luego eliminarlo
    response = client.post(
        "/espacios",
        json={
            "nombre": "Sala C",
            "capacidad": 15,
            "precio_por_hora": 4000.0,
            "esta_disponible": True,
        },
        headers=headers,
    )
    id_espacio = response.json()["id_espacio"]

    # 2. DELETE enviando el ID en la URL de /espacios
    espacio_eliminar = client.delete(
        f"/espacios/{id_espacio}",
        headers=headers,
    )

    # 3.  Verificar respuesta HTTP y confirmación en BD
    assert espacio_eliminar.status_code == status.HTTP_200_OK

    # Verificamos directamente en la BD que el espacio ya no exista
    session.expire_all()
    espacio_db = session.get(EspacioDB, id_espacio)

    assert espacio_db is None

def test_modificar_espacio_patch_exitoso(client):
    # -------------------------------------------------------------------------
    # 1. ARRANGE (Crear espacio inicial)
    # -------------------------------------------------------------------------
    token_admin = obtener_token_admin(client)
    headers = {"Authorization": f"Bearer {token_admin}"}

    res_crear = client.post(
        "/espacios",
        json={
            "nombre": "Sala Conferencia Original",
            "capacidad": 20,
            "precio_por_hora": 5000.0,
            "esta_disponible": True,
        },
        headers=headers,
    )
    id_espacio = res_crear.json()["id_espacio"]

    # -------------------------------------------------------------------------
    # 2. ACT (Modificar ÚNICAMENTE el precio mediante PATCH)
    # -------------------------------------------------------------------------
    res_patch = client.patch(
        f"/espacios/{id_espacio}",
        json={"precio_por_hora": 7500.0},
        headers=headers,
    )

    # -------------------------------------------------------------------------
    # 3. ASSERT (Verificar 200 OK, nuevo precio y constancia del resto)
    # -------------------------------------------------------------------------
    assert res_patch.status_code == status.HTTP_200_OK

    data_actualizada = res_patch.json()

    # El precio DEBE HABER CAMBIADO al valor que enviamos
    assert data_actualizada["precio_por_hora"] == 7500.0

    # Los demás campos DEBEN MANTENERSE IGUAL a como se crearon
    assert data_actualizada["nombre"] == "Sala Conferencia Original"
    assert data_actualizada["capacidad"] == 20
    assert data_actualizada["esta_disponible"] is True