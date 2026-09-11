from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Session, select, SQLModel
from typing import List

# Importamos la conexión a la BD
from database import engine, crear_db_y_tablas, obtener_sesion

# Importamos las tablas de SQLite, las clases de POO y los errores
from modelos import (
    EspacioDB, UsuarioDB, ReservaTabla,
    Espacio, Usuario, Reserva, ReservaError,
    UsuarioCreate, UsuarioResponse,
    TokenResponse, ReservaCreate, ReservaResponse
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

@app.get("/espacios")
def listar_espacios(session: Session = Depends(obtener_sesion)):
    # Buscamos todas las filas de la tabla 'espacio' en SQLite
    espacios = session.exec(select(EspacioDB)).all()
    return espacios


@app.post("/espacios")
def crear_espacio(espacio: EspacioDB, session: Session = Depends(obtener_sesion)):
    # Guarda un nuevo espacio directamente en la BD
    session.add(espacio)
    session.commit()
    session.refresh(espacio)
    return espacio

from typing import Optional

# Buscador dinámico: permite combinar filtros opcionales (precio, capacidad y disponibilidad) 
# usando Optional para no exigir parámetros y acumulando .where() según lo enviado.
@app.get("/espacios/buscar")
def buscar_espacios(
    precio_maximo: Optional[float] = None,
    minima_capacidad: Optional[int] = None,
    session: Session = Depends(obtener_sesion)
):
    # Paso A: Arrancamos con la consulta base (sin filtros todavía)
    consulta = select(EspacioDB)

    # Paso B: Evaluamos si el usuario mandó el precio
    if precio_maximo is not None:
        consulta = consulta.where(EspacioDB.precio_por_hora <= precio_maximo)

    # Paso C: Evaluamos si el usuario mandó la capacidad
    if minima_capacidad is not None:
        consulta = consulta.where(EspacioDB.capacidad >= minima_capacidad)

    # Paso D: Recién acá enviamos la consulta final acumulada a la BD
    resultados = session.exec(consulta).all()
    
    return resultados

@app.patch("/espacios/{id_espacio}")
def actualizar_espacio(
    id_espacio: int,
    precio_por_hora: Optional[float] = None,
    capacidad: Optional[int] = None,
    session: Session = Depends(obtener_sesion)
):
    #1. Buscar espacio
    espacio = session.get(EspacioDB, id_espacio)
    if not espacio:
        raise HTTPException(status_code= 404, detail="el espacio no existe")

    #2. Modificar solo los datos que me dieron
    if precio_por_hora is not None:
        espacio.precio_por_hora = precio_por_hora

    if capacidad is not None:
        espacio.capacidad = capacidad

    #3. Guardar los cambios es SQLite
    session.add(espacio)
    session.commit()
    session.refresh(espacio)

    return espacio




# ==========================================
# ENDPOINTS DE USUARIOS
# ==========================================

@app.post("/usuarios", response_model=UsuarioResponse, status_code=201)
def crear_usuario(
    usuario_input: UsuarioCreate, 
    session: Session = Depends(obtener_sesion)
):
    # 1. Convertimos la contraseña plana en un hash seguro
    password_encriptada = obtener_hash_password(usuario_input.password)

    # 2. Creamos la entidad para SQLite con el hash (NUNCA la clave plana)
    nuevo_usuario_db = UsuarioDB(
        nombre=usuario_input.nombre,
        email=usuario_input.email,
        hashed_password=password_encriptada
    )

    # 3. Guardamos en la base de datos
    session.add(nuevo_usuario_db)
    session.commit()
    session.refresh(nuevo_usuario_db)

    # 4. FastAPI automáticamente lo filtra usando UsuarioResponse (gracias a response_model)
    return nuevo_usuario_db

@app.get("/usuarios")
def listar_usuarios(session: Session = Depends(obtener_sesion)):
    usuarios = session.exec(select(UsuarioDB)).all()
    return usuarios


@app.get("/usuarios/{id_usuario}")
def obtener_usuario(id_usuario: int, session: Session = Depends(obtener_sesion)):
    usuario = session.get(UsuarioDB, id_usuario)

    if not usuario:
        raise HTTPException(status_code=404, detail=f"usuario con ID: {id_usuario} no existe")

    return usuario

@app.patch("/usuarios/{id_usuario}")
def actualizar_usuario(
    id_usuario: int,
    nombre: Optional[str] = None,
    email: Optional[str] = None,
    session: Session = Depends(obtener_sesion)
):
    #1. Buscar usuario
    usuario = session.get(UsuarioDB, id_usuario)
    if not usuario:
        raise HTTPException(status_code= 404, detail="el usuario no existe")

    #2. Modificar solo los datos que me dieron
    if nombre is not None:
        usuario.nombre = nombre

    if email is not None:
        usuario.email = email

    #3. Guardar los cambios es SQLite
    session.add(usuario)
    session.commit()
    session.refresh(usuario)

    return usuario

@app.delete("/usuarios/{id_usuario}")
def eliminar_usuario(id_usuario: int, session: Session = Depends(obtener_sesion)):
    # 1. Buscar si el usuario existe
    usuario = session.get(UsuarioDB, id_usuario)
    if not usuario:
        raise HTTPException(status_code=404, detail="El usuario no existe")

    # 2. Validar si tiene reservas asociadas
    reserva_existente = session.exec(
        select(ReservaTabla).where(ReservaTabla.id_usuario == id_usuario)
    ).first()

    if reserva_existente:
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar el usuario porque tiene reservas activas. Cancelá o borrá sus reservas primero."
        )

    # 3. Borrar el usuario
    session.delete(usuario)
    session.commit()

    return {"mensaje": f"Usuario {id_usuario} eliminado con éxito"}

@app.get("/usuarios/{id_usuario}/reservas")
def obtener_reservas_de_usuarios(
    id_usuario: int,
    session: Session = Depends(obtener_sesion)
):
    usuario = session.get(UsuarioDB,id_usuario)

    if not usuario:
        raise HTTPException(status_code=404, detail= f"usuario con id: {id_usuario} no existe")

    return usuario.reservas

# ==========================================
# ENDPOINT PRINCIPAL: CREAR RESERVA (POO + SQL)
# ==========================================

@app.post("/reservas", status_code=201)
def crear_reserva(
    datos: ReservaCreate,
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual)
):
    # 1. Obtenemos el ID del usuario autenticado desde el JWT (ya validado por el token)
    id_usuario_logueado = int(usuario_token["sub"])

    # 2. Leemos el espacio de SQLite
    espacio_db = session.get(EspacioDB, datos.id_espacio)
    if not espacio_db:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")

    usuario_db = session.get(UsuarioDB, id_usuario_logueado)

    # 3. Reconstrucción POO y Validaciones de Negocio
    usuario_poo = Usuario(
        id_usuario=usuario_db.id_usuario,
        nombre=usuario_db.nombre,
        email=usuario_db.email
    )
    espacio_poo = Espacio(
        id_espacio=espacio_db.id_espacio,
        nombre=espacio_db.nombre,
        capacidad=espacio_db.capacidad,
        precio_por_hora=espacio_db.precio_por_hora,
        esta_disponible=espacio_db.esta_disponible
    )

    try:
        reserva_poo = Reserva(
            id_reserva= None,
            usuario=usuario_poo,
            espacio=espacio_poo,
            horas=datos.horas
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 4. Actualización del espacio y creación del registro
    espacio_db.esta_disponible = espacio_poo.esta_disponible
    session.add(espacio_db)

    nueva_reserva_db = ReservaTabla(
        id_usuario=id_usuario_logueado,  # <--- Asignado automáticamente desde la sesión
        id_espacio=datos.id_espacio,
        horas=datos.horas,
        total=reserva_poo.calcular_total()
    )
    session.add(nueva_reserva_db)
    session.commit()
    session.refresh(espacio_db)

    return {
        "mensaje": "Reserva guardada con éxito en SQLite",
        "id_reserva": nueva_reserva_db.id_reserva,
        "total": nueva_reserva_db.total
    }

@app.get("/reservas")
def listar_reservas(session: Session = Depends(obtener_sesion)):
    # Buscamos todos los registros en la tabla ReservaTabla
    reservas = session.exec(select(ReservaTabla)).all()
    return reservas



@app.delete("/reservas/{id_reserva}")
def cancelar_reserva(id_reserva: int, 
                     session: Session = Depends(obtener_sesion),
                     usuario_token: dict = Depends(obtener_usuario_actual)
):
    id_usuario_logueado = int(usuario_token["sub"])

    # 1. Buscar la reserva en la BD
    reserva = session.get(ReservaTabla, id_reserva)
    if not reserva:
        raise HTTPException(status_code=404, detail="la reserva no existe")

    #2. Verificar Permisos
    es_admin = usuario_token.get("es_admin", False)
    es_dueno = reserva.id_usuario == id_usuario_logueado

    if not es_dueno and not es_admin :
        raise HTTPException(status_code=400, detail="no tienes permisos para cancelar esta reserva")

    # 3. buscar el espacio asociado a esa reserva
    espacio = session.get(EspacioDB, reserva.id_espacio)
    if espacio:
        #4. volver a pner el espacio disponible
        espacio.esta_disponible = True
        session.add(espacio)

    #5. eliminar la reserva de la BD
    session.delete(reserva)

    #6. confirmar los cambios en el disco
    session.commit()

    return{"mensaje": f"Reserva {id_reserva} cancelada exitosamente y espacio liberado"}

@app.get("/reservas/propias", response_model=list[ReservaResponse])
def listar_mis_reservas(
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual),
):
    # 1. Extraemos el ID del usuario del JWT
    id_usuario_logueado = int(usuario_token["sub"])

    # 2. Consultamos solo las reservas asociadas a este usuario
    statement = select(ReservaTabla).where(
        ReservaTabla.id_usuario == id_usuario_logueado
    )
    reservas = session.exec(statement).all()

    # 3. Retornamos la lista (FastAPI las convierte a ReservaResponse)
    return reservas

@app.get("/reservas/{id_reserva}")
def obtener_reserva_detallada(
    id_reserva: int, 
    session: Session = Depends(obtener_sesion),
    usuario_token: dict = Depends(obtener_usuario_actual)
):
    id_usuario_logueado = int(usuario_token["sub"])
    
    reserva = session.get(ReservaTabla, id_reserva)
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    es_admin = usuario_token.get("es_admin", False)
    es_dueno = reserva.id_usuario == id_usuario_logueado
    
    if not es_dueno and not es_admin :
        raise HTTPException(status_code=400, detail="no tienes permisos para ver esta reserva")
    

    # Accedemos directamente a los objetos relacionados sin hacer session.get manual
    return {
        "id_reserva": reserva.id_reserva,
        "horas": reserva.horas,
        "total": reserva.total,
        "cliente": {
            "nombre": reserva.usuario.nombre,
            "email": reserva.usuario.email
        },
        "espacio_reservado": {
            "nombre": reserva.espacio.nombre,
            "precio_por_hora": reserva.espacio.precio_por_hora
        }
    }


# ==========================================
# ENDPOINTS DE Login
# ==========================================

@app.post("/login", response_model=TokenResponse)
def login(
    credenciales: UsuarioCreate,  # Reutilizamos el DTO que recibe email y password
    session: Session = Depends(obtener_sesion)
):
    # 1. Buscar al usuario por su email
    query = select(UsuarioDB).where(UsuarioDB.email == credenciales.email)
    usuario = session.exec(query).first()

    # 2. Validar existencia de usuario y contraseña correcta
    # IMPORTANTE: Usamos un mensaje genérico por seguridad (evita listar emails válidos)
    if not usuario or not verificar_password(credenciales.password, usuario.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Crear el token con los datos que nos interesan (payload)
    datos_token = {
        "sub": str(usuario.id_usuario),
        "email": usuario.email,
        "es_admin": getattr(UsuarioDB, "es_admin", False)
    }
    access_token = crear_token_acceso(datos_token)

    # 4. Devolver el token generado
    return TokenResponse(access_token=access_token)

