# 🧾 Sistema de Cotizaciones - Capital & Farmer

Este sistema permite generar cotizaciones legales personalizadas para clientes del estudio. La aplicación analiza la complejidad del caso usando inteligencia artificial, ajusta precios y sugiere servicios adicionales automáticamente.

---

## 🚀 Tecnologías usadas

- Python 3.10+
- FastAPI
- SQLite
- Jinja2 (templates)
- Google Gemini API (IA)
- HTML + Bootstrap (frontend)

---

## 📦  Instalación

1. Clonar el repositorio  

   ```bash
   git clone https://github.com/gdev/silva-capital-farmer-exam.git```  
   ```
   
   ```bash
   cd silva-capital-farmer-exam
   ```

2. Crear y activar un entorno virtual (opcional pero recomendado)  
   
   ```bash
   python3 -m venv venv
   ```  
   
   * (Linux/macOS)
   ```bash
   source venv/bin/activate
   ```

   * (Windows)
   ```bash
   venv\Scripts\activate
   ```

3. Instalar dependencias  
   ```bash
   pip install -r requirements.txt
   ```

---

## [IMPORTANTE] 🔐 Variables de entorno (example.env)

- Copia este archivo como .env y agrega tus claves privadas:

```bash
# Clave de API Gemini
GEMINI_API_KEY=tu_clave_api

# Clave pública para firmar tokens u otros usos futuros (no necesario para este caso)
PUBLIC_KEY=clave_publica_dummy_o_real
```
* ⚠️ Nunca subas tu .env real al repositorio.

---

4. Ejecutar la aplicación  
   ```bash
   uvicorn main:app --reload
   ```

---

## Uso

- Acceder a 
```bash
[http://localhost:8000](http://localhost:8000)
```
- Completar el formulario de cotización y enviar
- Verás la cotización generada en pantalla con precio y número único

## Funcionalidades implementadas

- Frontend simple con formulario y validación básica (HTML5)
- Backend FastAPI que recibe formulario, calcula precio, guarda en SQLite y responde JSON
- Número de cotización único generado con UUID
- Persistencia en base de datos SQLite

## APIs utilizadas

- Google Gemini Pro

    Se utiliza para analizar la descripción del caso y generar contenido legal profesional. (Se genera en la cotizacion)

## Funcionalidades bonus

- ✅ Autenticación básica (login/logout)

- ✅ Validaciones en el formulario HTML

- ✅ Diseño responsive básico con Bootstrap

---

## 📁 Estructura del proyecto

```bash
apellido-capital-farmer-exam/
├── app.py
├── templates/
│   ├── form.html
│   └── cotizacion.html
├── static/
├── database.db
├── requirements.txt
├── README.md
└── example.env
```

---

## 🏁 Recomendaciones finales

    Los commits están organizados por funcionalidad.

    Todo el código está comentado para facilitar mantenimiento.

    Los errores de IA y base de datos son controlados adecuadamente.