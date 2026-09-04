from modelos import Usuario, Espacio, Reserva, ReservaError

# Crear entidades
usr = Usuario(1, "aris", "aris@gmail.com")
esp = Espacio(1, "Sala A", 4, 1000.0)

# Probar la reserva
try:
    reserva = Reserva(101, usr, esp, 2)
    print(reserva.obtener_resumen())
except ReservaError as e:
    print(f"Error: {e}")