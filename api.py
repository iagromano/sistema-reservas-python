from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, status
from sqlmodel import Session, select, SQLModel
from typing import List
from typing import Optional

# Importamos la conexión a la BD
from database import engine, crear_db_y_tablas, obtener_sesion

# Importamos las tablas de SQLite, las clases de POO y los errores
from modelos import (
    EspacioDB, UsuarioDB, ReservaTabla,
    Espacio, Usuario, Reserva, ReservaError,
    UsuarioCreate, UsuarioResponse,
    TokenResponse, ReservaCreate, ReservaResponse,
    EspacioCreateDTO, EspacioUpdateDTO, UsuarioLoginDTO,
    ReservaUpdateDTO 
)

from seguridad import crear_token_acceso, verificar_password, obtener_hash_password, obtener_usuario_actual


# Evento que se ejecuta al iniciar la API: crea la base de datos y las tablas si no existen

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código que se ejecuta al arrancar la aplicación
    SQLModel.metadata.create_all(engine)
    yield
    # Código que se ejecuta al apagar la aplicación (si hiciera falta)

# Le pasás el lifespan al instanciar FastAPI
app = FastAPI(lifespan=lifespan)


# ==========================================
# ENDPOINTS DE ESPACIOS
# ==========================================

@app.get(
    "/espacios",
    response_model=List[EspacioDB],
    status_code=status.HTTP_200_OK,
)
def listar_espacios(
    esta_disponible: Optional[bool] = None,
    precio_maximo: Optional[float] = None,
    minima_capacidad: Optional[int] = None,
    session: Session = Depends(obtener_sesion),
):
    """Obtiene el listado de espacios permitiendo filtros opcionales combinados."""
    consulta = select(EspacioDB)

    # Aplicamos filtros opcionales según los parámetros recibidos
    if esta_disponible is not None:
        consulta = consulta.where(EspacioDB.esta_disponible == esta_disponible)

    if precio_maximo is not None:
        consulta = consulta.where(EspacioDB.precio_por_hora <= precio_maximo)

    if minima_capacidad is not None:
        consulta = consulta.where(EspacioDB.capacidad >= minima_capacidad)

    espacios = session.exec(consulta).all()
    return espacios


@app.post(
    "/espacios",
    response_model=EspacioDB,
    status_code=status.HTTP_201_CREATED,
)
def crear_espacio(
    nuevo_espacio: EspacioCreateDTO,
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    """Crea un nuevo espacio comercial (exclusivo para administradores)."""
    # 1. Validar permisos de administrador
    es_admin = usuario_token.get("es_admin", False)
    if not es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para crear espacios",
        )

    # 2. Mapear datos e instanciar la entidad de la base de datos
    espacio_db = EspacioDB(
        nombre=nuevo_espacio.nombre,
        capacidad=nuevo_espacio.capacidad,
        precio_por_hora=nuevo_espacio.precio_por_hora,
        esta_disponible=nuevo_espacio.esta_disponible,
    )

    # 3. Guardar en SQLite
    session.add(espacio_db)
    session.commit()
    session.refresh(espacio_db)

    return espacio_db


@app.patch(
    "/espacios/{id_espacio}",
    response_model=EspacioDB,
    status_code=status.HTTP_200_OK,
)
def actualizar_espacio(
    id_espacio: int,
    datos: EspacioUpdateDTO,
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    """Actualiza parcialmente un espacio existente (exclusivo para administradores)."""
    # 1. Validar permisos de administrador
    es_admin = usuario_token.get("es_admin", False)
    if not es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para modificar espacios",
        )

    # 2. Buscar si el espacio existe
    espacio = session.get(EspacioDB, id_espacio)
    if not espacio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El espacio no existe",
        )

    # 3. Aplicar cambios dinámicos sólo sobre los campos enviados
    datos_dict = datos.model_dump(exclude_unset=True)
    for clave, valor in datos_dict.items():
        setattr(espacio, clave, valor)

    # 4. Guardar cambios en la base de datos
    session.add(espacio)
    session.commit()
    session.refresh(espacio)

    return espacio


@app.delete(
    "/espacios/{id_espacio}",
    status_code=status.HTTP_200_OK,
)
def eliminar_espacio(
    id_espacio: int,
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    """Elimina un espacio si no posee reservas activas (exclusivo para administradores)."""
    # 1. Validar permisos de administrador
    es_admin = usuario_token.get("es_admin", False)
    if not es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para eliminar espacios",
        )

    # 2. Buscar si el espacio existe
    espacio = session.get(EspacioDB, id_espacio)
    if not espacio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El espacio no existe",
        )

    # 3. Validar si existen reservas asociadas al espacio
    reserva_existente = session.exec(
        select(ReservaTabla).where(ReservaTabla.id_espacio == id_espacio)
    ).first()

    if reserva_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el espacio porque tiene reservas activas. Cancelá o borrá sus reservas primero.",
        )

    # 4. Eliminar el espacio de la base de datos
    session.delete(espacio)
    session.commit()

    return {"mensaje": f"Espacio {id_espacio} eliminado con éxito"}



# ==========================================
# ENDPOINTS DE USUARIOS
# ==========================================

@app.post(
    "/usuarios",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_usuario(
    usuario_input: UsuarioCreate,
    session: Session = Depends(obtener_sesion),
):
    """Registra un nuevo usuario en la plataforma."""
    # 1. Validar que el email no esté registrado previamente
    usuario_existente = session.exec(
        select(UsuarioDB).where(UsuarioDB.email == usuario_input.email)
    ).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya se encuentra registrado",
        )

    # 2. Generar el hash de la contraseña
    password_encriptada = obtener_hash_password(usuario_input.password)

    # 3. Instanciar y guardar la entidad en SQLite
    nuevo_usuario_db = UsuarioDB(
        nombre=usuario_input.nombre,
        email=usuario_input.email,
        hashed_password=password_encriptada,
        es_admin=usuario_input.es_admin,
    )

    session.add(nuevo_usuario_db)
    session.commit()
    session.refresh(nuevo_usuario_db)

    return nuevo_usuario_db


@app.get(
    "/usuarios",
    response_model=List[UsuarioResponse],
    status_code=status.HTTP_200_OK,
)
def listar_usuarios(
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    """Obtiene la lista completa de usuarios (exclusivo para administradores)."""
    # 1. Validar permisos de administrador
    es_admin = usuario_token.get("es_admin", False)
    if not es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver el listado de usuarios",
        )

    # 2. Consultar todos los usuarios
    usuarios = session.exec(select(UsuarioDB)).all()
    return usuarios


@app.get(
    "/usuarios/{id_usuario}",
    response_model=UsuarioResponse,
    status_code=status.HTTP_200_OK,
)
def obtener_usuario(
    id_usuario: int,
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    """Obtiene la información pública de un usuario específico."""
    # 1. Buscar usuario por ID
    usuario = session.get(UsuarioDB, id_usuario)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El usuario con ID {id_usuario} no existe",
        )

    return usuario


@app.patch(
    "/usuarios/{id_usuario}",
    response_model=UsuarioResponse,
    status_code=status.HTTP_200_OK,
)
def actualizar_usuario(
    id_usuario: int,
    nombre: Optional[str] = None,
    email: Optional[str] = None,
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    """Actualiza la información de un usuario registrado."""
    # 1. Validar si el usuario existe
    usuario = session.get(UsuarioDB, id_usuario)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no existe",
        )

    # 2. Validar que el usuario que intenta editar sea el mismo o un admin
    id_usuario_actual = int(usuario_token.get("sub", 0))
    es_admin = usuario_token.get("es_admin", False)

    if id_usuario_actual != id_usuario and not es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para modificar este perfil",
        )

    # 3. Modificar campos enviados
    if nombre is not None:
        usuario.nombre = nombre

    if email is not None:
        usuario.email = email

    # 4. Guardar cambios en SQLite
    session.add(usuario)
    session.commit()
    session.refresh(usuario)

    return usuario


@app.delete(
    "/usuarios/{id_usuario}",
    status_code=status.HTTP_200_OK,
)
def eliminar_usuario(
    id_usuario: int,
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    """Elimina un usuario de la plataforma si no posee reservas activas (exclusivo para administradores)."""
    # 1. Validar permisos de administrador
    es_admin = usuario_token.get("es_admin", False)
    if not es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para eliminar usuarios",
        )

    # 2. Buscar si el usuario existe
    usuario = session.get(UsuarioDB, id_usuario)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no existe",
        )

    # 3. Validar si tiene reservas asociadas
    reserva_existente = session.exec(
        select(ReservaTabla).where(ReservaTabla.id_usuario == id_usuario)
    ).first()

    if reserva_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el usuario porque tiene reservas activas. Cancelá o borrá sus reservas primero.",
        )

    # 4. Eliminar el usuario
    session.delete(usuario)
    session.commit()

    return {"mensaje": f"Usuario {id_usuario} eliminado con éxito"}


@app.get(
    "/usuarios/{id_usuario}/reservas",
    status_code=status.HTTP_200_OK,
)
def obtener_reservas_de_usuarios(
    id_usuario: int,
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    """Obtiene el listado de reservas asociadas a un usuario específico."""
    # 1. Validar existencia del usuario
    usuario = session.get(UsuarioDB, id_usuario)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El usuario con ID {id_usuario} no existe",
        )

    return usuario.reservas

# ==========================================
# ENDPOINT PRINCIPAL: CREAR RESERVA (POO + SQL)
# ==========================================

@app.post(
    "/reservas",
    response_model=ReservaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_reserva(
    datos: ReservaCreate,
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    """Crea una nueva reserva validando disponibilidad y calculando el total."""
    # 1. Obtener ID del usuario autenticado desde el JWT
    id_usuario_logueado = int(usuario_token["sub"])

    # 2. Consultar entidades de la base de datos
    espacio_db = session.get(EspacioDB, datos.id_espacio)
    if not espacio_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El espacio no existe",
        )

    usuario_db = session.get(UsuarioDB, id_usuario_logueado)

    # 3. Reconstrucción POO y Validaciones de Negocio
    usuario_poo = Usuario(
        id_usuario=usuario_db.id_usuario,
        nombre=usuario_db.nombre,
        email=usuario_db.email,
    )
    espacio_poo = Espacio(
        id_espacio=espacio_db.id_espacio,
        nombre=espacio_db.nombre,
        capacidad=espacio_db.capacidad,
        precio_por_hora=espacio_db.precio_por_hora,
        esta_disponible=espacio_db.esta_disponible,
    )

    try:
        reserva_poo = Reserva(
            id_reserva=None,
            usuario=usuario_poo,
            espacio=espacio_poo,
            horas=datos.horas,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    # 4. Actualizar disponibilidad del espacio y guardar la reserva
    espacio_db.esta_disponible = espacio_poo.esta_disponible
    session.add(espacio_db)

    nueva_reserva_db = ReservaTabla(
        id_usuario=id_usuario_logueado,
        id_espacio=datos.id_espacio,
        horas=datos.horas,
        total=reserva_poo.calcular_total(),
    )
    session.add(nueva_reserva_db)
    session.commit()
    session.refresh(nueva_reserva_db)

    return nueva_reserva_db

@app.patch(
    "/reservas/{id_reserva}",
    response_model=ReservaResponse,
    status_code=status.HTTP_200_OK,
)
def actualizar_reserva(
    id_reserva: int,
    reserva_update: ReservaUpdateDTO,
    session: Session = Depends(obtener_sesion),
    usuario_actual: dict = Depends(
        obtener_usuario_actual
    ),  # Especificamos dict
):
    """Actualiza parcialmente una reserva (p. ej. las horas) y recalcula el total."""
    # 1. Buscar la reserva en BD
    reserva_db = session.get(ReservaTabla, id_reserva)
    if not reserva_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La reserva no existe",
        )

    # 2. Verificar permisos extrayendo del diccionario JWT
    id_usuario_actual = int(usuario_actual.get("sub"))
    es_admin_actual = usuario_actual.get("es_admin", False)

    if reserva_db.id_usuario != id_usuario_actual and not es_admin_actual:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para modificar esta reserva",
        )

    # 3. Aplicar los cambios enviados
    datos_actualizar = reserva_update.model_dump(exclude_unset=True)

    if "horas" in datos_actualizar and datos_actualizar["horas"] is not None:
        nuevas_horas = datos_actualizar["horas"]

        if nuevas_horas <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Las horas deben ser mayores a cero",
            )

        # Traemos el espacio para recalcular el precio total dinámicamente
        espacio = session.get(EspacioDB, reserva_db.id_espacio)
        if espacio:
            reserva_db.total = nuevas_horas * espacio.precio_por_hora

        reserva_db.horas = nuevas_horas

    # 4. Guardar cambios en la BD
    session.add(reserva_db)
    session.commit()
    session.refresh(reserva_db)

    return reserva_db

@app.get(
    "/reservas/propias",
    response_model=List[ReservaResponse],
    status_code=status.HTTP_200_OK,
)
def listar_mis_reservas(
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    """Obtiene el listado de reservas del usuario autenticado."""
    id_usuario_logueado = int(usuario_token["sub"])

    statement = select(ReservaTabla).where(
        ReservaTabla.id_usuario == id_usuario_logueado
    )
    reservas = session.exec(statement).all()

    return reservas


@app.get(
    "/reservas",
    response_model=List[ReservaResponse],
    status_code=status.HTTP_200_OK,
)
def listar_reservas(
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    """Obtiene la lista completa de reservas registradas (exclusivo para administradores)."""
    # Validar permisos de administrador
    es_admin = usuario_token.get("es_admin", False)
    if not es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver todas las reservas",
        )

    reservas = session.exec(select(ReservaTabla)).all()
    return reservas


@app.get(
    "/reservas/{id_reserva}",
    status_code=status.HTTP_200_OK,
)
def obtener_reserva_detallada(
    id_reserva: int,
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    """Obtiene el detalle completo de una reserva (cliente y espacio asociados)."""
    id_usuario_logueado = int(usuario_token["sub"])

    reserva = session.get(ReservaTabla, id_reserva)
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva no encontrada",
        )

    es_admin = usuario_token.get("es_admin", False)
    es_dueno = reserva.id_usuario == id_usuario_logueado

    if not es_dueno and not es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta reserva",
        )

    return {
        "id_reserva": reserva.id_reserva,
        "horas": reserva.horas,
        "total": reserva.total,
        "cliente": {
            "nombre": reserva.usuario.nombre,
            "email": reserva.usuario.email,
        },
        "espacio_reservado": {
            "nombre": reserva.espacio.nombre,
            "precio_por_hora": reserva.espacio.precio_por_hora,
        },
    }


@app.delete(
    "/reservas/{id_reserva}",
    status_code=status.HTTP_200_OK,
)
def cancelar_reserva(
    id_reserva: int,
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    """Cancela una reserva activa y libera automáticamente la disponibilidad del espacio."""
    id_usuario_logueado = int(usuario_token["sub"])

    # 1. Buscar la reserva
    reserva = session.get(ReservaTabla, id_reserva)
    if not reserva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La reserva no existe",
        )

    # 2. Verificar Permisos (dueño o admin)
    es_admin = usuario_token.get("es_admin", False)
    es_dueno = reserva.id_usuario == id_usuario_logueado

    if not es_dueno and not es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para cancelar esta reserva",
        )

    # 3. Liberar el espacio asociado
    espacio = session.get(EspacioDB, reserva.id_espacio)
    if espacio:
        espacio.esta_disponible = True
        session.add(espacio)

    # 4. Eliminar el registro de la reserva
    session.delete(reserva)
    session.commit()

    return {
        "mensaje": f"Reserva {id_reserva} cancelada exitosamente y espacio liberado"
    }

# ==========================================
# ENDPOINTS DE Login
# ==========================================

@app.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    credenciales: UsuarioLoginDTO,
    session: Session = Depends(obtener_sesion),
):
    """Autentica a un usuario registrado y genera un token de acceso JWT."""
    # 1. Buscar al usuario por su email
    query = select(UsuarioDB).where(UsuarioDB.email == credenciales.email)
    usuario = session.exec(query).first()

    # 2. Validar existencia del usuario y verificación de contraseña hash
    if not usuario or not verificar_password(
        credenciales.password, usuario.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Construir los datos del payload para el token JWT
    datos_token = {
        "sub": str(usuario.id_usuario),
        "email": usuario.email,
        "es_admin": usuario.es_admin,
    }

    # 4. Generar el token de acceso
    access_token = crear_token_acceso(datos_token)

    # 5. Devolver la respuesta estructurada
    return TokenResponse(access_token=access_token, token_type="bearer")