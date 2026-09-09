import datetime
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

# --- CONFIGURACIÓN DE SEGURIDAD ---
SECRET_KEY = "tu_clave_secreta_super_segura_cambiame"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Instancia moderna de hashing
password_hash = PasswordHash((BcryptHasher(),))


# ==========================================
# 1. FUNCIONES PARA HASHING DE CONTRASEÑAS
# ==========================================

def obtener_hash_password(password: str) -> str:
    """Transforma una contraseña en texto plano en un hash irreversible."""
    return password_hash.hash(password)


def verificar_password(password_plana: str, password_hash_bd: str) -> bool:
    """Compara la contraseña recibida en el login con el hash de la BD."""
    return password_hash.verify(password_plana, password_hash_bd)


# ==========================================
# 2. FUNCIONES PARA MANEJO DE TOKENS JWT
# ==========================================

def crear_token_acceso(datos: dict) -> str:
    """Genera un nuevo token JWT firmando el payload recibido."""
    payload = datos.copy()
    
    expiracion = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({"exp": expiracion})
    
    token_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token_jwt


def verificar_token_acceso(token: str) -> dict:
    """Decodifica y valida la firma/expiración del JWT."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("El token ha expirado.")
    except jwt.InvalidTokenError:
        raise ValueError("Token inválido o corrupto.")