from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from modelos import Usuario, Espacio, Reserva, ReservaError

app = FastAPI(title="Sistema de Reservas API")

# Base de datos simulada en memoria
espacios_db = {
    1: Espacio(1, "Sala A", 4, 1000.0),
    2: Espacio(2, "Sala B", 10, 2500.0)
}
usuarios_db = {
    1: Usuario(1, "aris", "aris@gmail.com")
}
reservas_db = []


# --- ESQUEMA PYDANTIC ---
# Define la estructura requerida del JSON que nos enviará el cliente
class CreacionReservaDTO(BaseModel):
    id_reserva: int
    id_usuario: int
    id_espacio: int
    horas: int


# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"mensaje": "API de Gestión de Reservas activa"}


@app.get("/espacios")
def listar_espacios():
    return [
        {
            "id_espacio": esp.id_espacio,
            "nombre": esp.nombre,
            "capacidad": esp.capacidad,
            "precio_por_hora": esp.precio_por_hora,
            "esta_disponible": esp.esta_disponible
        }
        for esp in espacios_db.values()
    ]


@app.post("/reservas")
def crear_reserva(datos: CreacionReservaDTO):
    # 1. Buscar si existen el usuario y el espacio solicitados
    usuario = usuarios_db.get(datos.id_usuario)
    espacio = espacios_db.get(datos.id_espacio)

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")

    # 2. Intentar instanciar el modelo con sus validaciones de POO
    try:
        nueva_reserva = Reserva(
            id_reserva=datos.id_reserva,
            usuario=usuario,
            espacio=espacio,
            horas=datos.horas
        )
        
        reservas_db.append(nueva_reserva)
        
        return {
            "mensaje": "Reserva creada con éxito",
            "resumen": nueva_reserva.obtener_resumen(),
            "total": nueva_reserva.calcular_total()
        }

    # 3. Si la lógica de POO arroja ReservaError, devolvemos error HTTP 400 (Bad Request)
    except ReservaError as e:
        raise HTTPException(status_code=400, detail=str(e))