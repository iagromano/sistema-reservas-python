import datetime
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlmodel import Session, select



# ==========================================
# 1. CONFIGURACIÓN Y CONSTANTES DE SEGURIDAD
# ==========================================
SECRET_KEY = "tu_clave_secreta_super_segura_cambiame"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Instancia de hashing
password_hash = PasswordHash((BcryptHasher(),))

security = HTTPBearer()


# ==========================================
# 2. FUNCIONES PARA HASHING DE CONTRASEÑAS
# ==========================================
def obtener_hash_password(password: str) -> str:
    return password_hash.hash(password)


def verificar_password(password_plana: str, password_hash_bd: str) -> bool:
    return password_hash.verify(password_plana, password_hash_bd)


# ==========================================
# 3. FUNCIONES PARA MANEJO DE TOKENS JWT
# ==========================================
def crear_token_acceso(datos: dict) -> str:
    payload = datos.copy()
    expiracion = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload.update({"exp": expiracion})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verificar_token_acceso(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise ValueError("El token ha expirado.")
    except jwt.InvalidTokenError:
        raise ValueError("Token inválido o corrupto.")


# ==========================================
# 4. DEPENDENCIAS PARA PROTEGER ENDPOINTS
# ==========================================
def obtener_usuario_actual(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Extrae el token recibido en el header Authorization: Bearer <TOKEN>."""
    token = credentials.credentials
    excepcion_credenciales = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise excepcion_credenciales
        return payload
    except jwt.PyJWTError:
        raise excepcion_credenciales