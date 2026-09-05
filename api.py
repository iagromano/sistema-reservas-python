from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Session, select
from typing import List

# Importamos la conexión a la BD
from database import engine, crear_db_y_tablas, obtener_sesion

# Importamos las tablas de SQLite, las clases de POO y los errores
from modelos import (
    EspacioDB, UsuarioDB, ReservaTabla,
    Espacio, Usuario, Reserva, ReservaError,
    CreacionReservaDTO
)

app = FastAPI(title="Sistema de Reservas con SQLite")


# Evento que se ejecuta al iniciar la API: crea la base de datos y las tablas si no existen
@app.on_event("startup")
def on_startup():
    crear_db_y_tablas()


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


# ==========================================
# ENDPOINTS DE USUARIOS
# ==========================================

@app.post("/usuarios")
def crear_usuario(usuario: UsuarioDB, session: Session = Depends(obtener_sesion)):
    # Guarda un nuevo usuario en la BD
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


# ==========================================
# ENDPOINT PRINCIPAL: CREAR RESERVA (POO + SQL)
# ==========================================

@app.post("/reservas")
def crear_reserva(datos: CreacionReservaDTO, session: Session = Depends(obtener_sesion)):
    # 1. Leemos de la BD real (SQLite)
    usuario_db = session.get(UsuarioDB, datos.id_usuario)
    espacio_db = session.get(EspacioDB, datos.id_espacio)

    if not usuario_db or not espacio_db:
        raise HTTPException(status_code=404, detail="Usuario o Espacio no encontrado")

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