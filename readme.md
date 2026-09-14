# 🏢 Sistema de Gestión de Reservas API

API RESTful desarrollada con **FastAPI** y **SQLModel** para la gestión, control de disponibilidad y reserva de espacios, implementando autenticación basada en tokens JWT y arquitectura orientada a objetos (POO).

---

## 🛠️ Tecnologías Utilizadas

* **Python 3.10+**
* **FastAPI**: Framework web asíncrono de alto rendimiento.
* **SQLModel**: ORM basado en Pydantic y SQLAlchemy para interactuar con la BD.
* **SQLite**: Base de datos relacional persistente.
* **PyJWT / Passlib**: Generación de tokens de acceso Bearer JWT y cifrado de contraseñas.
* **Uvicorn**: Servidor ASGI para desarrollo e implementación.

---

## 🔒 Características y Seguridad

* **Autenticación Bearer JWT**: Flujo de inicio de sesión seguro mediante `HTTPBearer` y tokens firmados.
* **Autorización basada en Tokens**: Extracción de identidad (`sub`) y permisos (`es_admin`) directamente desde los claims del JWT para minimizar consultas a la BD.
* **Persistencia de Datos**: Configuración optimizada de SQLite para garantizar la retención de registros de usuarios, espacios y reservas.
* **Reglas de Negocio POO**: Liberación automática de disponibilidad de espacios al cancelar reservas.

---

## 🚀 Inicio Rápido

### 1. Clonar el repositorio e instalar dependencias

```bash
git clone [https://github.com/TU_USUARIO/TU_REPOSITY.git](https://github.com/TU_USUARIO/TU_REPOSITY.git)
cd TU_REPOSITORIO

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install fastapi sqlmodel uvicorn pyjwt passlib[bcrypt]