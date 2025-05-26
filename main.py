import json
import re
from fastapi import FastAPI, Form, HTTPException, Request, Depends, status
import requests  # Importar requests como biblioteca independiente
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from datetime import datetime
import sqlite3
import uuid

# Configuración de Gemini API
API_KEY = "AIzaSyAqqC9HtGFu7TGxmRtmV6XfivE_lknNszQ"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

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
        fecha TEXT,
        complejidad TEXT,
        ajuste_precio INTEGER,
        servicios_adicionales TEXT,
        propuesta_texto TEXT
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
    response.headers["Cache-Control"] = "no-store"
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
    Genera una cotización con análisis de IA usando Gemini API
    """
    try:
        # Generamos número y fecha
        numero = generar_numero_cotizacion()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Precio base según servicio
        precio_base = calcular_precio(tipo_servicio)
        
        # Consultamos a Gemini para análisis
        print(f"[INFO] Iniciando análisis con Gemini para cotización {numero}")
        analisis_ia = analizar_con_gemini(descripcion, tipo_servicio)
        
        # Calculamos precio final con ajuste
        precio_final = precio_base * (1 + analisis_ia["ajuste_precio"] / 100)
        
        # Guardamos en base de datos con campos adicionales de IA
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO cotizaciones (
            numero, nombre, email, tipo_servicio, descripcion, precio, fecha,
            complejidad, ajuste_precio, servicios_adicionales, propuesta_texto
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            numero, nombre, email, tipo_servicio, descripcion, precio_final, fecha,
            analisis_ia["complejidad"], analisis_ia["ajuste_precio"], 
            json.dumps(analisis_ia["servicios_adicionales"]), analisis_ia["propuesta_texto"]
        ))
        conn.commit()
        conn.close()
        
        print(f"[SUCCESS] Cotización {numero} generada exitosamente")
        
        # Respuesta JSON con todos los datos
        return {
            "numero_cotizacion": numero,
            "cliente": nombre,
            "email": email,
            "tipo_servicio": tipo_servicio,
            "descripcion": descripcion,
            "precio_base": precio_base,
            "ajuste_precio_pct": analisis_ia["ajuste_precio"],
            "precio_final": precio_final,
            "fecha": fecha,
            "analisis_ia": {
                "complejidad": analisis_ia["complejidad"],
                "servicios_adicionales": analisis_ia["servicios_adicionales"],
                "propuesta_texto": analisis_ia["propuesta_texto"]
            }
        }
        
    except Exception as e:
        print(f"[ERROR] Error generando cotización: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generando cotización: {str(e)}"
        )


def analizar_con_gemini(descripcion: str, tipo_servicio: str) -> dict:
    """
    Analiza un caso legal usando Gemini API y devuelve:
    - Nivel de complejidad (Baja, Media, Alta)
    - Ajuste de precio recomendado (0%, 25%, 50%)
    - Servicios adicionales sugeridos
    - Propuesta profesional generada
    
    Args:
        descripcion (str): Descripción del caso legal proporcionada por el cliente
        tipo_servicio (str): Tipo de servicio seleccionado
    
    Returns:
        dict: Análisis completo del caso con recomendaciones
    """
    # Verificamos que la clave API esté configurada
    if not API_KEY:
        print("[ERROR] GEMINI_API_KEY no está configurada")
        return get_default_response()
    
    try:
        # URL de la API de Gemini
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-latest:generateContent?key={API_KEY}"
        
        # Prompt especializado para análisis legal con Gemini
        prompt = f"""
        Eres un asistente legal experto especializado en análisis de casos y cotizaciones legales en Perú. 
        Analiza el siguiente caso y proporciona un análisis detallado.
        
        CASO LEGAL:
        Tipo de servicio: {tipo_servicio}
        Descripción del cliente: {descripcion}
        
        Debes evaluar y responder ÚNICAMENTE en formato JSON con esta estructura exacta:
        {{
            "complejidad": "Baja|Media|Alta",
            "ajuste_precio": 0|25|50,
            "servicios_adicionales": ["servicio1", "servicio2", "servicio3"],
            "propuesta_texto": "Propuesta profesional de 2-3 párrafos dirigida al cliente"
        }}
        
        CRITERIOS DE EVALUACIÓN:
        
        COMPLEJIDAD:
        - Baja: Casos rutinarios, documentación estándar, sin complicaciones especiales
        - Media: Casos que requieren investigación adicional, múltiples partes involucradas
        - Alta: Casos complejos, precedentes legales, litigio prolongado, alta especialización
        
        AJUSTE DE PRECIO:
        - 0%: Complejidad baja, procedimiento estándar
        - 25%: Complejidad media, requiere trabajo adicional
        - 50%: Complejidad alta, requiere especialización y tiempo considerable
        
        SERVICIOS ADICIONALES (máximo 3, basados en el tipo de servicio):
        Para {tipo_servicio}, considera servicios como:
        - Asesoría especializada
        - Investigación jurídica
        - Representación en audiencias
        - Elaboración de documentos adicionales
        - Negociación con terceros
        - Seguimiento post-proceso
        
        PROPUESTA TEXTO:
        - Dirigirse al cliente de manera profesional y empática
        - Explicar brevemente la complejidad del caso
        - Destacar los servicios que se incluirán
        - Generar confianza en la experiencia del despacho
        - Mencionar el compromiso con el caso
        
        Responde SOLO con el JSON, sin texto adicional.
        """
        
        # Payload para la API de Gemini
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        # Headers
        headers = {
            "Content-Type": "application/json"
        }
        
        print(f"[INFO] Enviando consulta a Gemini API...")
        
        # Realizamos la consulta a Gemini
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"[ERROR] Error en API de Gemini: {response.status_code} - {response.text}")
            return get_default_response()
        
        response_data = response.json()
        
        # Extraemos el texto de la respuesta
        if "candidates" not in response_data or not response_data["candidates"]:
            print("[ERROR] Respuesta vacía de Gemini API")
            return get_default_response()
        
        content = response_data["candidates"][0]["content"]["parts"][0]["text"]
        print(f"[INFO] Respuesta recibida de Gemini: {content[:200]}...")
        
        # Limpiamos la respuesta para extraer solo el JSON
        content = content.strip()
        
        # Intentamos extraer JSON de la respuesta
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            json_text = json_match.group()
        else:
            json_text = content
        
        # Parseamos el JSON
        try:
            analisis = json.loads(json_text)
            
            # Validamos la estructura de la respuesta
            analisis_validado = validar_respuesta_gemini(analisis, tipo_servicio)
            
            print(f"[SUCCESS] Análisis completado - Complejidad: {analisis_validado['complejidad']}, Ajuste: {analisis_validado['ajuste_precio']}%")
            
            return analisis_validado
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] Error parseando JSON de Gemini: {str(e)}")
            print(f"[ERROR] Respuesta recibida: {content}")
            return get_default_response()
    
    except requests.exceptions.Timeout:
        print("[ERROR] Timeout consultando Gemini API")
        return get_default_response()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión con Gemini API: {str(e)}")
        return get_default_response()
    except Exception as e:
        print(f"[ERROR] Error inesperado consultando Gemini API: {str(e)}")
        return get_default_response()


def validar_respuesta_gemini(analisis: dict, tipo_servicio: str) -> dict:
    """
    Valida y corrige la respuesta de Gemini si es necesario
    
    Args:
        analisis (dict): Respuesta de Gemini
        tipo_servicio (str): Tipo de servicio para contexto
    
    Returns:
        dict: Análisis validado y corregido
    """
    # Valores por defecto
    complejidades_validas = ["Baja", "Media", "Alta"]
    ajustes_validos = [0, 25, 50]
    
    # Validar complejidad
    if "complejidad" not in analisis or analisis["complejidad"] not in complejidades_validas:
        analisis["complejidad"] = "Media"
        print("[WARNING] Complejidad inválida, usando valor por defecto: Media")
    
    # Validar ajuste de precio
    if "ajuste_precio" not in analisis or analisis["ajuste_precio"] not in ajustes_validos:
        analisis["ajuste_precio"] = 25
        print("[WARNING] Ajuste de precio inválido, usando valor por defecto: 25%")
    
    # Validar servicios adicionales
    if "servicios_adicionales" not in analisis or not isinstance(analisis["servicios_adicionales"], list):
        analisis["servicios_adicionales"] = get_servicios_default(tipo_servicio)
        print("[WARNING] Servicios adicionales inválidos, usando valores por defecto")
    else:
        # Limitar a máximo 3 servicios
        analisis["servicios_adicionales"] = analisis["servicios_adicionales"][:3]
    
    # Validar propuesta de texto
    if "propuesta_texto" not in analisis or not analisis["propuesta_texto"] or len(analisis["propuesta_texto"].strip()) < 50:
        analisis["propuesta_texto"] = get_propuesta_default(tipo_servicio, analisis["complejidad"])
        print("[WARNING] Propuesta de texto inválida, usando valor por defecto")
    
    return analisis


def get_servicios_default(tipo_servicio: str) -> list:
    """
    Devuelve servicios adicionales por defecto según el tipo de servicio
    
    Args:
        tipo_servicio (str): Tipo de servicio legal
    
    Returns:
        list: Lista de servicios adicionales por defecto
    """
    servicios_map = {
        "Derecho Civil": ["Elaboración de contratos", "Asesoría en negociaciones", "Seguimiento legal"],
        "Derecho Penal": ["Representación en audiencias", "Investigación del caso", "Asesoría familiar"],
        "Derecho Laboral": ["Negociación con empleador", "Cálculo de beneficios", "Representación ante autoridades"],
        "Derecho Comercial": ["Asesoría empresarial", "Revisión de documentos", "Trámites registrales"],
        "Derecho Familiar": ["Mediación familiar", "Elaboración de acuerdos", "Seguimiento psicológico"],
        "Derecho Tributario": ["Asesoría fiscal", "Representación ante SUNAT", "Planificación tributaria"]
    }
    
    return servicios_map.get(tipo_servicio, ["Asesoría especializada", "Elaboración de documentos", "Seguimiento del caso"])



def get_servicios_default(tipo_servicio: str) -> list:
    """
    Devuelve servicios adicionales por defecto según el tipo de servicio
    
    Args:
        tipo_servicio (str): Tipo de servicio legal
    
    Returns:
        list: Lista de servicios adicionales por defecto
    """
    servicios_map = {
        "Derecho Civil": ["Elaboración de contratos", "Asesoría en negociaciones", "Seguimiento legal"],
        "Derecho Penal": ["Representación en audiencias", "Investigación del caso", "Asesoría familiar"],
        "Derecho Laboral": ["Negociación con empleador", "Cálculo de beneficios", "Representación ante autoridades"],
        "Derecho Comercial": ["Asesoría empresarial", "Revisión de documentos", "Trámites registrales"],
        "Derecho Familiar": ["Mediación familiar", "Elaboración de acuerdos", "Seguimiento psicológico"],
        "Derecho Tributario": ["Asesoría fiscal", "Representación ante SUNAT", "Planificación tributaria"]
    }
    
    return servicios_map.get(tipo_servicio, ["Asesoría especializada", "Elaboración de documentos", "Seguimiento del caso"])


def get_propuesta_default(tipo_servicio: str, complejidad: str) -> str:
    """
    Genera una propuesta por defecto según el tipo de servicio y complejidad
    
    Args:
        tipo_servicio (str): Tipo de servicio legal
        complejidad (str): Nivel de complejidad del caso
    
    Returns:
        str: Propuesta profesional por defecto
    """
    return f"""Estimado cliente, hemos analizado su caso de {tipo_servicio} y determinamos que presenta una complejidad {complejidad.lower()}. 
    
    Nuestro equipo especializado se encargará de brindarle la asesoría legal más adecuada para su situación, aplicando nuestra experiencia y conocimiento del marco legal peruano. Nos comprometemos a mantenerlo informado en cada etapa del proceso y a trabajar diligentemente para lograr el mejor resultado posible.
    
    Confíe en nosotros para resolver su caso con la profesionalidad y dedicación que usted merece."""



def get_default_response() -> dict:
    """
    Respuesta por defecto cuando Gemini no está disponible
    
    Returns:
        dict: Análisis por defecto
    """
    return {
        "complejidad": "Media",
        "ajuste_precio": 25,
        "servicios_adicionales": ["Asesoría especializada", "Elaboración de documentos", "Seguimiento del caso"],
        "propuesta_texto": """Estimado cliente, hemos recibido su consulta legal y nos complace poder asistirle en este proceso. 
        
        Nuestro equipo de abogados especializados evaluará detalladamente su caso para brindarle la mejor estrategia legal posible. Nos comprometemos a mantener una comunicación constante y transparente durante todo el desarrollo de su asunto legal.
        
        Puede confiar en nuestra experiencia y dedicación para lograr los mejores resultados en la resolución de su caso."""
    }
