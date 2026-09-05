from sqlmodel import SQLModel, create_engine, Session

# Nombre del archivo donde se guardará la base de datos local
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# El "engine" es el motor que gestiona la conexión física con el archivo
engine = create_engine(sqlite_url, echo=True)


def crear_db_y_tablas():
    """Crea el archivo database.db y las tablas si aún no existen."""
    SQLModel.metadata.create_all(engine)


def obtener_sesion():
    """Abre una sesión de trabajo con la base de datos y la cierra al terminar."""
    with Session(engine) as session:
        yield session