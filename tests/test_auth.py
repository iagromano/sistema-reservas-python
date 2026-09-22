from fastapi import status


def test_registrar_usuario_exitoso(client):
    """Valida el registro exitoso de un nuevo usuario."""
    response = client.post(
        "/usuarios",
        json={
            "nombre": "Test User",
            "email": "test@example.com",
            "password": "password123",
            "es_admin": False,
        },
    )
    data = response.json()

    assert response.status_code == status.HTTP_201_CREATED
    assert data["email"] == "test@example.com"
    assert "id_usuario" in data
    # Verificamos que NUNCA devuelva el hash ni la clave en la respuesta
    assert "hashed_password" not in data
    assert "password" not in data


def test_login_exitoso(client):
    """Valida la autenticación de un usuario existente y generación de token."""
    # 1. Creamos el usuario
    client.post(
        "/usuarios",
        json={
            "nombre": "Test User",
            "email": "login@example.com",
            "password": "secretpassword",
            "es_admin": False,
        },
    )

    # 2. Intentamos iniciar sesión
    response = client.post(
        "/login",
        json={
            "email": "login@example.com",
            "password": "secretpassword",
        },
    )
    data = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_credenciales_invalidas(client):
    """Valida que devuelva 401 Unauthorized ante una contraseña incorrecta."""
    client.post(
        "/usuarios",
        json={
            "nombre": "Test User",
            "email": "user@example.com",
            "password": "correctpassword",
            "es_admin": False,
        },
    )

    response = client.post(
        "/login",
        json={
            "email": "user@example.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Email o contraseña incorrectos"


    