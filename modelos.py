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
            print(f"Error: El espacio '{self.nombre}' ya se encuentra ocupado.")

    def liberar(self):
        self.esta_disponible = True
        print(f"El espacio '{self.nombre}' ahora está disponible.")

class Reserva:
    def __init__ (self, id_reserva: int, usuario: Usuario, espacio: Espacio, horas: int):
        self.id_reserva = id_reserva
        self.usuario = usuario
        self.espacio = espacio
        self.horas = horas

    def calcular_total(self):
        total = self.horas * self.espacio.precio_por_hora
        return total

    def obtener_resumen(self):
        total = self.calcular_total()
        return f"Reserva #{self.id_reserva} | Usuario: {self.usuario.nombre} | Espacio: {self.espacio.nombre} | Total: ${total}"

 # 1. Creamos las entidades base
usr1 = Usuario(1, "aris", "aris@gmail.com")
esp1 = Espacio(10, "Sala de Reuniones A", capacidad=6, precio_por_hora=1500.0)

# 2. Creamos la reserva pasando las instancias anteriores
res1 = Reserva(id_reserva=100, usuario=usr1, espacio=esp1, horas=3)

# 3. Probamos los métodos
print(f"Total a pagar: ${res1.calcular_total()}")
print(res1.obtener_resumen())