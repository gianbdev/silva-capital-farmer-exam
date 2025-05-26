# Sistema de Cotizaciones - Capital & Farmer

## Instalación

1. Clonar el repositorio  

   ```git clone https://github.com/tu_usuario/apellido-capital-farmer-exam.git```  
   
   
   ```cd apellido-capital-farmer-exam```

2. Crear y activar un entorno virtual (opcional pero recomendado)  
   `python3 -m venv venv`  
   `source venv/bin/activate`  (Linux/macOS)  
   `venv\Scripts\activate` (Windows)

3. Instalar dependencias  
   `pip install -r requirements.txt`

4. Ejecutar la aplicación  
   `uvicorn main:app --reload`

## Uso

- Acceder a [http://localhost:8000](http://localhost:8000)
- Completar el formulario de cotización y enviar
- Verás la cotización generada en pantalla con precio y número único

## Funcionalidades implementadas

- Frontend simple con formulario y validación básica (HTML5)
- Backend FastAPI que recibe formulario, calcula precio, guarda en SQLite y responde JSON
- Número de cotización único generado con UUID
- Persistencia en base de datos SQLite

## APIs utilizadas

- No aplica (aún no está integrada IA)

## Funcionalidades bonus

- Envío y respuesta de formulario sin recargar página (fetch API)

