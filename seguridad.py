import datetime
import jwt
from passlib.context import CryptContext

# --- CONFIGURACIÓN DE SEGURIDAD ---
# La clave secreta debe guardarse en variables de entorno en producción
SECRET_KEY = "tu_clave_secreta_super_segura_cambiame"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Contexto de hashing configurado con algoritmo bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==========================================
# 1. FUNCIONES PARA HASHING DE CONTRASEÑAS
# ==========================================

def obtener_hash_password(password: str) -> str:
    """Transforma una contraseña en texto plano en un hash irreversible."""
    return pwd_context.hash(password)


def verificar_password(password_plana: str, password_hash: str) -> bool:
    """Compara la contraseña recibida en el login con el hash de la BD."""
    return pwd_context.verify(password_plana, password_hash)


# ==========================================
# 2. FUNCIONES PARA MANEJO DE TOKENS JWT
# ==========================================

def crear_token_acceso(datos: dict) -> str:
    """Genera un nuevo token JWT firmando el payload recibido."""
    payload = datos.copy()
    
    # Definir fecha/hora de expiración
    expiracion = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({"exp": expiracion})
    
    # Firmar y codificar el token
    token_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token_jwt


def verificar_token_acceso(token: str) -> dict:
    """
    Decodifica y valida la firma/expiración del JWT.
    Retorna el payload si es válido o lanza excepciones si expiró/es inválido.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("El token ha expirado.")
    except jwt.InvalidTokenError:
        raise ValueError("Token inválido o corrupto.")