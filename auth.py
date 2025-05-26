from fastapi import Request, status
from starlette.responses import RedirectResponse
from fastapi import Depends

# Usuarios hardcodeados (en un sistema real, iría a DB)
USUARIOS = {
    "admin": "1234",
    "user": "abcd"
}

# Función para validar usuario
def validar_usuario(username: str, password: str) -> bool:
    return USUARIOS.get(username) == password

# Dependencia para proteger rutas
def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return user
