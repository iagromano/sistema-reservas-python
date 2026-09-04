# Heredamos de Exception para crear nuestro propio tipo de error
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
    def __init__(self, id_espacio: int, nombre: str, capacidad: int, precio_por_hora: float):
        self.id_espacio = id_espacio
        self.nombre = nombre
        self.capacidad = capacidad
        self.precio_por_hora = precio_por_hora
        self.esta_disponible = True

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

"""  # 1. Creamos las entidades base
usr1 = Usuario(1, "aris", "aris@gmail.com")
esp1 = Espacio(10, "Sala de Reuniones A", capacidad=6, precio_por_hora=1500.0)

# 2. Creamos la reserva pasando las instancias anteriores
res1 = Reserva(id_reserva=100, usuario=usr1, espacio=esp1, horas=3)

# 3. Probamos los métodos
print(f"Total a pagar: ${res1.calcular_total()}")
print(res1.obtener_resumen()) """

# --- PRUEBA DE VALIDACIONES ---

usr = Usuario(1, "aris", "aris@gmail.com")
esp = Espacio(1, "Sala de Reuniones A", 6, 1500.0)

# 1. Intentamos crear una reserva con horas inválidas
try:
    reserva_falida = Reserva(id_reserva=1, usuario=usr, espacio=esp, horas=-3)
except ReservaError as e:
    print(f"Error atrapado con éxito: {e}")

# 2. Creamos una reserva válida (esto va a ocupar la Sala A)
reserva_ok = Reserva(id_reserva=2, usuario=usr, espacio=esp, horas=2)
print(reserva_ok.obtener_resumen())

# 3. Intentamos reservar la misma sala de nuevo (debería fallar porque ya no está disponible)
try:
    reserva_duplicada = Reserva(id_reserva=3, usuario=usr, espacio=esp, horas=1)
except ReservaError as e:
    print(f"Error atrapado con éxito: {e}")