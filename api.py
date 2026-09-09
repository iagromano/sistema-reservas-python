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
    CreacionReservaDTO, UsuarioCreate, UsuarioResponse, TokenResponse
)
from seguridad import crear_token_acceso, verificar_password, obtener_hash_password



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

@app.post("/reservas")
def crear_reserva(datos: CreacionReservaDTO, session: Session = Depends(obtener_sesion)):
    # 1. Leemos de la BD real (SQLite)
    usuario_db = session.get(UsuarioDB, datos.id_usuario)
    espacio_db = session.get(EspacioDB, datos.id_espacio)

    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not espacio_db:
        raise HTTPException(status_code=404, detail="UEspacio no encontrado")

    # 2. Reconstruimos los objetos para la lógica POO
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

    # 3. Validaciones y Lógica de Negocio (POO)
    try:
        reserva_poo = Reserva(
            id_reserva=datos.id_reserva,
            usuario=usuario_poo,
            espacio=espacio_poo,
            horas=datos.horas
        )
    except Exception as e:
        # Atrapa ReservaError o cualquier otro fallo y devuelve un 400 limpio
        raise HTTPException(status_code=400, detail=str(e))

    # 4. Sincronizamos el nuevo estado del Espacio con la Base de Datos
    espacio_db.esta_disponible = espacio_poo.esta_disponible
    session.add(espacio_db)

    # 5. Preparamos el registro de la Reserva para SQLite
    nueva_reserva_db = ReservaTabla(
        id_reserva=datos.id_reserva,
        id_usuario=datos.id_usuario,
        id_espacio=datos.id_espacio,
        horas=datos.horas,
        total=reserva_poo.calcular_total()
    )
    session.add(nueva_reserva_db)

    # 6. Escribimos físicamente en el archivo database.db
    session.commit()
    session.refresh(espacio_db)

    # 7. Retornamos la respuesta de éxito
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
def cancelar_reserva(id_reserva: int, session: Session = Depends(obtener_sesion)):
    # 1. Buscar la reserva en la BD
    reserva = session.get(ReservaTabla, id_reserva)
    if not reserva:
        raise HTTPException(status_code=404, detail="la reserva no existe")

    # 2. buscar el espacio asociado a esa reserva
    espacio = session.get(EspacioDB, reserva.id_espacio)
    if espacio:
        #3. volver a pner el espacio disponible
        espacio.esta_disponible = True
        session.add(espacio)

    #4. eliminar la reserva de la BD
    session.delete(reserva)

    #5. confirmar los cambios en el disco
    session.commit()

    return{"mensaje": f"Reserva {id_reserva} cancelada exitosamente y espacio liberado"}


@app.get("/reservas/{id_reserva}")
def obtener_reserva_detallada(
    id_reserva: int, 
    session: Session = Depends(obtener_sesion)
):
    reserva = session.get(ReservaTabla, id_reserva)
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

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
        "email": usuario.email
    }
    access_token = crear_token_acceso(datos_token)

    # 4. Devolver el token generado
    return TokenResponse(access_token=access_token)

