from typing import Optional, List
from pydantic import BaseModel, EmailStr
from sqlmodel import SQLModel, Field, Relationship

# ==========================================
# 1. TABLAS PARA LA BASE DE DATOS (SQLModel)
# ==========================================


# --- TABLA USUARIO ---
class UsuarioDB(SQLModel, table=True):
    __tablename__ = "usuario"

    id_usuario: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    email: str = Field(unique=True, index=True)
    hashed_password: str  # <--- Nuevo campo para almacenar el hash de passlib

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
    horas: int
    total: float

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
    def __init__ (self, id_reserva: int, usuario: Usuario, espacio: Espacio, horas: int):
        #  --- Validacion 1: horas positivas ---
        if horas <= 0:
            raise ReservaError("la cantidad de horas debe ser mayor a cero.")

        # --- Validacion 2: disponibilidad del espacio ---
        if not espacio.esta_disponible:
            raise ReservaError(f"el espacio '{espacio.nombre}' no esta disponible para reservar.")

        #si las validaciones pasan, asignamos las propiedades
        self.id_reserva = id_reserva
        self.usuario = usuario
        self.espacio = espacio
        self.horas = horas

        #ocupamos el espacio automaticamente al crear la reserva exitosa
        self.espacio.reservar()

    def calcular_total(self):
        total = self.horas * self.espacio.precio_por_hora
        return total

    def obtener_resumen(self):
        total = self.calcular_total()
        return f"Reserva #{self.id_reserva} | Usuario: {self.usuario.nombre} | Espacio: {self.espacio.nombre} | Total: ${total}"


# ==========================================
# 3. DTOs (Data Transfer Objects / Schemas)
# ==========================================

class UsuarioCreate(BaseModel):
    """DTO para el registro de usuario (recibe la contraseña plana)."""
    nombre: str
    email: EmailStr
    password: str  # Se recibe en texto plano desde el cliente


class UsuarioResponse(BaseModel):
    """DTO para la respuesta pública (Oculta la contraseña y el hash)."""
    id_usuario: int
    nombre: str
    email: EmailStr

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Lo que el cliente ENVIARÁ en el cuerpo JSON al hacer la reserva
class ReservaCreate(BaseModel):
    id_espacio: int
    horas: int

# Lo que la API DEVOLVERÁ al cliente tras crear la reserva
class ReservaResponse(BaseModel):
    id_reserva: int
    id_usuario: int
    id_espacio: int
    horas: int
    total: float

    class Config:
        from_attributes = True
