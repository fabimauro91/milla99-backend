# Proyecto FastAPI

Este es un proyecto backend basado en FastAPI, estructurado para escalar y mantener buenas prácticas.

## Estructura del Proyecto

```
app/
├── __init__.py
├── main.py
├── core/         # Configuración y base de datos
├── models/       # Modelos de datos (SQLModel)
├── routers/      # Endpoints de la API
├── services/     # Lógica de negocio
├── test/         # Pruebas automáticas
├── utils/        # Utilidades generales
```

## Instalación

1. Crear y activar el entorno virtual:
```bash
python -m venv venv
# En Windows:
.\venv\Scripts\Activate.ps1
# En Linux/Mac:
source venv/bin/activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Configuración

Crea un archivo `.env` en la raíz del proyecto con las variables necesarias para la configuración (ver ejemplo en el código fuente).

## Ejecución

```bash
uvicorn app.main:app --reload
```

La API estará disponible en http://127.0.0.1:8000

## Pruebas

Para ejecutar los tests automáticos:
```bash
pytest
``` 