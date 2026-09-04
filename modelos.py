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

