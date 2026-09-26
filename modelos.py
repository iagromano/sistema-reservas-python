from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

# ==========================================
# 1. TABLAS PARA LA BASE DE DATOS (SQLModel)
# ==========================================


# --- TABLA USUARIO ---
class UsuarioDB(SQLModel, table=True):
    __tablename__ = "usuario"

    id_usuario: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    email: str = Field(unique=True, index=True)
    hashed_password: str  
    es_admin: bool = False

    # Relación inversa con ReservaTabla
    reservas: List["ReservaTabla"] = Relationship(back_populates="usuario")


# --- TABLA ESPACIO ---
class EspacioDB(SQLModel, table=True):
    __tablename__ = "espacio"

    id_espacio: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    capacidad: int
    precio_por_hora: float
    esta_disponible: bool = True

    # Relación inversa: Un espacio puede tener muchas reservas
    reservas: List["ReservaTabla"] = Relationship(back_populates="espacio")


# --- TABLA RESERVA (Conecta ambas tablas) ---
class ReservaTabla(SQLModel, table=True):
    __tablename__ = "reserva"

    id_reserva: Optional[int] = Field(default=None, primary_key=True)
    total: float
    fecha_inicio: datetime
    fecha_fin: datetime

    # 1. Claves Foráneas (Restricción física en SQLite)
    id_usuario: int = Field(foreign_key="usuario.id_usuario")
    id_espacio: int = Field(foreign_key="espacio.id_espacio")

    # 2. Propiedades de Relación (Magia de Python para navegar entre objetos)
    usuario: Optional[UsuarioDB] = Relationship(back_populates="reservas")
    espacio: Optional[EspacioDB] = Relationship(back_populates="reservas")
# ==========================================
# 2. LÓGICA DE NEGOCIO POO (Tus clases intactas)
# ==========================================

class ReservaError(Exception):
    """Excepción personalizada para errores del sistema de reservas."""
    pass

class Usuario:
    def __init__(self, id_usuario: int, nombre: str, email: str):
        self.id_usuario = id_usuario
        self.nombre = nombre
        self.email = email
        self.es_admin = False

    def hacer_admin(self):
        self.es_admin = True
        print(f"ahora '{self.nombre}' es administrador")

    def obtener_perfil(self):
        rol = "Administrador" if self.es_admin else "Usuario común"
        return f" Nombre: {self.nombre} | Email: {self.email} | Rol: {rol}"


class Espacio:
    def __init__(self, id_espacio: int, nombre: str, capacidad: int, precio_por_hora: float, esta_disponible: bool = True):
        self.id_espacio = id_espacio
        self.nombre = nombre
        self.capacidad = capacidad
        self.precio_por_hora = precio_por_hora
        self.esta_disponible = esta_disponible  # Toma el valor de la BD (o True por defecto)

    def reservar(self):
        if self.esta_disponible:
            self.esta_disponible = False
            print(f"Éxito: El espacio '{self.nombre}' ha sido reservado.")
        else:
            raise ReservaError(f"Error: El espacio '{self.nombre}' ya se encuentra ocupado.")

    def liberar(self):
        self.esta_disponible = True
        print(f"El espacio '{self.nombre}' ahora está disponible.")

class Reserva:
    def __init__(self, id_reserva: int, usuario, espacio, fecha_inicio: datetime, fecha_fin: datetime):
        # 1. Validar que la fecha de inicio no sea en el pasado
        ahora = datetime.now()
        if fecha_inicio <= ahora:
            raise ReservaError("No puedes hacer reservas en el pasado.")

        # 2. Validar que el final sea posterior al inicio
        if fecha_fin < fecha_inicio:
            raise ReservaError("La fecha y hora de fin deben ser posteriores a la de inicio.")

        # 3. Validar disponibilidad del espacio
        if not espacio.esta_disponible:
            raise ReservaError(f"El espacio '{espacio.nombre}' no está disponible para reservar.")

        # Asignación de propiedades si todo es válido
        self.id_reserva = id_reserva
        self.usuario = usuario
        self.espacio = espacio
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin

        # Ocupar el espacio automáticamente
        self.espacio.reservar()

    def calcular_total(self) -> float:
        # Convertimos la diferencia de tiempo a horas totales exactas
        duracion_horas = (self.fecha_fin - self.fecha_inicio).total_seconds() / 3600
        return duracion_horas * self.espacio.precio_por_hora

    def obtener_resumen(self) -> str:
        total = self.calcular_total()
        return (
            f"Reserva #{self.id_reserva} | Usuario: {self.usuario.nombre} | "
            f"Espacio: {self.espacio.nombre} | Inicio: {self.fecha_inicio} | "
            f"Fin: {self.fecha_fin} | Total: ${total:.2f}"
        )

# ==========================================
# 3. DTOs (Data Transfer Objects / Schemas)
# ==========================================

# --- ESPACIOS ---
class EspacioCreateDTO(BaseModel):
    """DTO para el registro de un nuevo espacio."""
    nombre: str = Field(
        ...,
        description="Nombre identificatorio del espacio físico.",
    )
    capacidad: int = Field(
        ...,
        gt=0,
        description="Capacidad máxima de personas permitidas en el espacio.",
    )
    precio_por_hora: float = Field(
        ...,
        ge=0,
        description="Costo monetario por hora de uso del espacio.",
    )
    esta_disponible: bool = Field(
        default=True,
        description="Indica si el espacio se encuentra habilitado para recibir reservas.",
    )


class EspacioUpdateDTO(BaseModel):
    """DTO para la actualización parcial de un espacio."""
    nombre: Optional[str] = None
    capacidad: Optional[int] = None
    precio_por_hora: Optional[float] = None
    esta_disponible: Optional[bool] = None


# --- USUARIOS ---
class UsuarioCreate(BaseModel):
    """DTO para el registro de un nuevo usuario."""
    nombre: str = Field(
        ...,
        description="Nombre del Usuario",
    )
    email: EmailStr = Field(
        ...,
        description="correo electronico del usuario",
    )
    password: str = Field(
        ...,
        description="contraseña del usuario"
    )
    es_admin: bool = False


class UsuarioResponse(BaseModel):
    """DTO para la respuesta de datos públicos de usuario."""
    model_config = ConfigDict(from_attributes=True)
    id_usuario: int
    nombre: str
    email: str
    es_admin: bool


# --- AUTENTICACIÓN ---
class UsuarioLoginDTO(BaseModel):
    """DTO para la autenticación de usuario (credenciales)."""
    email: str
    password: str


class TokenResponse(BaseModel):
    """DTO para la respuesta con el token JWT de acceso."""
    access_token: str
    token_type: str = "bearer"


# --- RESERVAS ---
class ReservaCreate(BaseModel):
    """DTO para la solicitud de creación de una reserva."""
    id_espacio: int = Field(
        ...,
        description="numero de identificacion del espacio",
        ge=0,
    )
    fecha_inicio: datetime = Field(
        description="fecha de inicio de la reserva",
    )
    fecha_fin: datetime = Field(
            description="fecha de finalización de la reserva",
        )

class ReservaUpdateDTO(BaseModel):
    """DTO para la actualización parcial de una reserva."""
    id_espacio: int = None
    fecha_inicio: datetime = None
    fecha_fin: datetime = None

class ReservaResponse(BaseModel):
    """DTO para la respuesta detallada de una reserva creada."""
    model_config = ConfigDict(from_attributes=True)
    id_reserva: int
    id_usuario: int
    id_espacio: int
    fecha_inicio: datetime
    fecha_fin: datetime
    total: float
