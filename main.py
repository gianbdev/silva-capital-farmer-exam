from fastapi import FastAPI, Form, Request, Depends, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import uuid
from openai import OpenAI

import os
openai_key = os.getenv("OPENAI_API_KEY")  # Cargar desde .env

# Importamos lo del auth
from auth import validar_usuario, get_current_user

app = FastAPI()

# Monta la carpeta static en la ruta /static
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(SessionMiddleware, secret_key="7c969c170f14fce3adbfc192d2e3494b9b2f6501fe567c3acf1e4d851765ec93")

templates = Jinja2Templates(directory="templates")


def init_db():
    """
    Inicializa la base de datos SQLite y crea la tabla 'cotizaciones' 
    si no existe aún. Se ejecuta al inicio del servidor para asegurar 
    que la estructura está lista para usarse.
    """
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cotizaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE,
        nombre TEXT,
        email TEXT,
        tipo_servicio TEXT,
        descripcion TEXT,
        precio REAL,
        fecha TEXT
    )
    """)
    conn.commit()
    conn.close()


init_db()


def generar_numero_cotizacion() -> str:
    """
    Genera un número de cotización único con formato COT-2025-XXXXXXXX
    donde XXXXXXXX es una cadena alfanumérica aleatoria de 8 caracteres en mayúsculas.

    Returns:
        str: Número de cotización único.
    """
    return f"COT-2025-{str(uuid.uuid4())[:8].upper()}"


def calcular_precio(tipo_servicio: str) -> float:
    """
    Calcula el precio de la cotización basado en el tipo de servicio seleccionado.

    Args:
        tipo_servicio (str): Nombre del tipo de servicio.

    Returns:
        float: Precio correspondiente al tipo de servicio. Si no existe, retorna 0.0.
    """
    precios = {
        "Constitución de empresa": 1500.0,
        "Defensa laboral": 2000.0,
        "Consultoría tributaria": 800.0
    }
    return precios.get(tipo_servicio, 0.0)


@app.get("/")
def root():
    """
    Redirige automáticamente a la página de login.
    """
    return RedirectResponse(url="/login")


@app.get("/login")
def login_get(request: Request):
    """
    Renderiza la página de login si el usuario no está autenticado.
    Si ya hay sesión activa, redirige a la página de cotizaciones.

    Args:
        request (Request): Objeto de la petición HTTP.

    Returns:
        TemplateResponse | RedirectResponse: Página de login o redirección.
    """
    user = request.session.get("user")
    if user:
        return RedirectResponse(url="/cotizaciones")
    response = templates.TemplateResponse("login.html", {"request": request, "error": None})
    response.headers.Cache-Control = "no-store"
    return response


@app.post("/login")
def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Procesa el login del usuario. Valida las credenciales usando la función
    validar_usuario. Si es válido, crea la sesión y redirige a cotizaciones,
    de lo contrario vuelve a mostrar el login con error.

    Args:
        request (Request): Objeto de la petición HTTP.
        username (str): Nombre de usuario enviado por formulario.
        password (str): Contraseña enviada por formulario.

    Returns:
        RedirectResponse | TemplateResponse: Redirige a cotizaciones o renderiza login con error.
    """
    if validar_usuario(username, password):
        request.session["user"] = username
        return RedirectResponse(url="/cotizaciones", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Usuario o contraseña incorrectos"})


@app.get("/logout")
def logout(request: Request):
    """
    Limpia la sesión del usuario y redirige a la página de login.

    Args:
        request (Request): Objeto de la petición HTTP.

    Returns:
        RedirectResponse: Redirección a login.
    """
    request.session.clear()
    return RedirectResponse(url="/login")


@app.get("/cotizaciones")
def formulario(request: Request, user: str = Depends(get_current_user)):
    """
    Renderiza la página principal del formulario para generar cotizaciones,
    sólo accesible si el usuario está autenticado.

    Args:
        request (Request): Objeto de la petición HTTP.
        user (str): Usuario autenticado (obtenido vía Depends).

    Returns:
        TemplateResponse: Página HTML con el formulario.
    """
    return templates.TemplateResponse("form.html", {"request": request, "user": user})


@app.post("/cotizacion", response_class=JSONResponse)
async def generar_cotizacion(
    nombre: str = Form(...),
    email: str = Form(...),
    tipo_servicio: str = Form(...),
    descripcion: str = Form(...),
    user: str = Depends(get_current_user)
):
    """
    Recibe datos del formulario para generar una nueva cotización.
    Calcula el precio, genera un número único, guarda en la base de datos 
    y devuelve los datos en formato JSON.

    Args:
        nombre (str): Nombre del cliente.
        email (str): Email del cliente.
        tipo_servicio (str): Tipo de servicio seleccionado.
        descripcion (str): Descripción adicional.
        user (str): Usuario autenticado (vía Depends).

    Returns:
        dict: Datos de la cotización generada en JSON.
    """
    numero = generar_numero_cotizacion()
    precio_base = calcular_precio(tipo_servicio)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Llamar a la IA para análisis
    resultado_ia = analizar_con_ia(descripcion, tipo_servicio)
    ajuste = resultado_ia.get("ajuste_precio", 0)
    precio_final = precio_base * (1 + ajuste / 100)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO cotizaciones (numero, nombre, email, tipo_servicio, descripcion, precio, fecha)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (numero, nombre, email, tipo_servicio, descripcion, precio_final, fecha))
    conn.commit()
    conn.close()

    return {
        "numero_cotizacion": numero,
        "cliente": nombre,
        "email": email,
        "tipo_servicio": tipo_servicio,
        "descripcion": descripcion,
        "precio": precio_base,
        "ajuste_precio_pct": ajuste,
        "precio_final": precio_final,
        "fecha": fecha,
        "analisis_ia": {
            "complejidad": resultado_ia.get("complejidad"),
            "servicios_adicionales": resultado_ia.get("servicios_adicionales"),
            "propuesta_texto": resultado_ia.get("propuesta_texto")
        }
    }

def analizar_con_ia(descripcion: str, tipo_servicio: str):
    prompt = f"""
    Eres un asistente legal experto. Analiza este caso legal:
    Descripción: {descripcion}
    Tipo de servicio: {tipo_servicio}

    Por favor responde con:
    1. Nivel de complejidad (Baja, Media, Alta)
    2. Recomendación de ajuste de precio (0%, 25%, 50%)
    3. Servicios adicionales necesarios (si aplica, separados por comas)
    4. Genera un texto profesional como propuesta para cliente, 2-3 párrafos.

    Responde en formato JSON como este ejemplo:
    {{
      "complejidad": "Media",
      "ajuste_precio": 25,
      "servicios_adicionales": ["Revisión de contratos"],
      "propuesta_texto": "Texto profesional..."
    }}
    """

    try:
        response = openai_key.chat.completions.create(model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500)
        contenido = response.choices[0].message.content

        import json
        resultado = json.loads(contenido)
        return resultado

    except Exception as e:
        print(f"Error en IA: {e}")
        # Retorna valores por defecto para no bloquear la app
        return {
            "complejidad": "Media",
            "ajuste_precio": 0,
            "servicios_adicionales": [],
            "propuesta_texto": "No fue posible generar la propuesta automática en este momento."
        }
