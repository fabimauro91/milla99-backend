from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, FileResponse
import subprocess
import json
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional
import asyncio
from pathlib import Path
from app.core.dependencies.admin_auth import get_current_admin
from app.core.config import settings


router = APIRouter(
    prefix="/tests",
    tags=["ADMIN - tests"],
    dependencies=[Depends(get_current_admin)]
)


class TestResult:
    def __init__(self):
        self.results = []
        self.summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0
        }
        self.duration = 0.0

    def add_result(self, test_name: str, status: str, duration: float, error_message: str = None):
        result = {
            "test_name": test_name,
            "status": status,
            "duration": duration,
            "error_message": error_message
        }
        self.results.append(result)
        self.update_summary(status)

    def update_summary(self, status: str):
        self.summary["total"] += 1
        if status == "passed":
            self.summary["passed"] += 1
        elif status == "failed":
            self.summary["failed"] += 1
        elif status == "skipped":
            self.summary["skipped"] += 1
        elif status == "error":
            self.summary["errors"] += 1

    def set_duration(self, duration: float):
        self.duration = duration


def run_tests_with_json_output() -> Dict:
    """Ejecuta los tests y devuelve resultados en formato JSON"""
    # FORZAR el uso de la base de datos de test para seguridad
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = settings.TEST_DATABASE_URL

    print(
        f"🔒 FORZANDO uso de base de datos de test: {settings.TEST_DATABASE_URL}")
    print(f"📊 Entorno actual: {settings.ENVIRONMENT}")

    try:
        # Crear archivo temporal para el reporte JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json_report_path = temp_file.name

        cmd = [
            "pytest",
            "app/test/",
            "--json-report",
            f"--json-report-file={json_report_path}",
            "--json-report-indent=2",
            "-v"
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )

        stdout, stderr = process.communicate()

        # Leer el reporte JSON
        results = {"success": process.returncode ==
                   0, "stdout": stdout, "stderr": stderr}

        if os.path.exists(json_report_path):
            with open(json_report_path, 'r') as f:
                json_data = json.load(f)
            results.update(json_data)

        return results
    finally:
        # Restaurar la configuración original
        if original_database_url:
            os.environ["DATABASE_URL"] = original_database_url
        else:
            os.environ.pop("DATABASE_URL", None)

        # Limpiar archivo temporal
        if os.path.exists(json_report_path):
            os.unlink(json_report_path)


def run_tests_with_html_output() -> str:
    """Ejecuta los tests y genera un reporte HTML"""
    # FORZAR el uso de la base de datos de test para seguridad
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = settings.TEST_DATABASE_URL

    print(
        f"🔒 FORZANDO uso de base de datos de test: {settings.TEST_DATABASE_URL}")
    print(f"📊 Entorno actual: {settings.ENVIRONMENT}")

    try:
        # Crear directorio para reportes si no existe
        reports_dir = Path("static/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Generar nombre único para el reporte
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_report_path = reports_dir / f"test_report_{timestamp}.html"

        # Ejecutar pytest con reporte HTML
        cmd = [
            "pytest",
            "app/test/",
            f"--html={html_report_path}",
            "--self-contained-html",
            "-v"
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )

        stdout, stderr = process.communicate()

        # Verificar que el archivo existe
        if html_report_path.exists():
            return str(html_report_path)
        else:
            raise Exception(f"Error generando reporte HTML: {stderr}")

    finally:
        # Restaurar la configuración original
        if original_database_url:
            os.environ["DATABASE_URL"] = original_database_url
        else:
            os.environ.pop("DATABASE_URL", None)


def run_tests_qa_standalone() -> Dict:
    """
    Ejecuta tests en entorno QA completamente aislado.
    Este método ejecuta un script independiente que no afecta el servidor principal.
    """
    print("Ejecutando tests en entorno QA aislado...")

    try:
        # Ejecutar el script independiente de QA
        cmd = ["python", "run_tests_qa_standalone.py"]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )

        stdout, stderr = process.communicate()

        print("Salida del script QA:")
        print(stdout)

        if stderr:
            print("Errores del script QA:")
            print(stderr)

        # Intentar parsear el resultado JSON del script
        try:
            # Buscar el JSON en la salida (está al final del output)
            lines = stdout.strip().split('\n')
            for line in reversed(lines):
                if line.strip().startswith('{') and line.strip().endswith('}'):
                    result = json.loads(line.strip())
                    return result
        except json.JSONDecodeError:
            pass

        # Si no se pudo parsear JSON, devolver resultado básico
        return {
            "success": process.returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "environment": "qa_standalone",
            "message": "Tests ejecutados en entorno QA aislado"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "environment": "qa_standalone"
        }


@router.post("/run", description="""
Ejecuta todos los tests del proyecto y devuelve los resultados en formato JSON.

**Permisos:** Solo administradores pueden ejecutar tests.

**Seguridad:** Este endpoint SIEMPRE usa la base de datos de test para proteger los datos de producción.

**Respuesta:**
- `success`: Boolean indicando si todos los tests pasaron
- `summary`: Resumen de resultados (total, passed, failed, skipped, errors, duration)
- `results`: Lista detallada de cada test con su estado y duración
- `stdout`: Salida estándar de pytest
- `stderr`: Salida de errores de pytest
""")
async def run_tests():
    """Ejecuta todos los tests y devuelve resultados en JSON - Solo ADMIN"""
    try:
        results = run_tests_with_json_output()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=results
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ejecutando tests: {str(e)}"
        )


@router.post("/run-html", description="""
Ejecuta todos los tests del proyecto y genera un reporte HTML visual.

**Permisos:** Solo administradores pueden ejecutar tests.

**Seguridad:** Este endpoint ejecuta tests en un entorno QA completamente aislado.
El servidor principal continúa usando la base de datos de producción sin interrupciones.

**Respuesta:**
- Mensaje de éxito y recomendación de consultar /tests/reports
""")
async def run_tests_html():
    """Ejecuta todos los tests y genera un reporte HTML - Solo ADMIN"""
    try:
        # Usar el método aislado de QA
        result = run_tests_qa_standalone()

        if result.get("success"):
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "message": "Reporte HTML generado exitosamente. Consulta /tests/reports para ver la lista de reportes."
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error ejecutando tests en QA: {result.get('error', 'Error desconocido')}"
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando reporte HTML: {str(e)}"
        )


@router.get("/reports", description="""
Obtiene la lista de reportes HTML disponibles.

**Permisos:** Solo administradores pueden ver reportes.
""")
async def list_reports():
    """Lista todos los reportes HTML disponibles - Solo ADMIN"""
    reports_dir = Path("static/reports")

    if not reports_dir.exists():
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"reports": [], "total": 0}
        )

    reports = []
    for report_file in reports_dir.glob("test_report_*.html"):
        reports.append({
            "name": report_file.name,
            "url": f"/static/reports/{report_file.name}",
            "size": report_file.stat().st_size,
            "created": datetime.fromtimestamp(report_file.stat().st_mtime).isoformat()
        })

    # Ordenar por fecha de creación (más reciente primero)
    reports.sort(key=lambda x: x["created"], reverse=True)

    return {
        "reports": reports,
        "total": len(reports)
    }


@router.post("/run-specific", description="""
Ejecuta tests específicos basados en patrones o nombres de archivo.

**Permisos:** Solo administradores pueden ejecutar tests.

**Seguridad:** Este endpoint SIEMPRE usa la base de datos de test.

**Parámetros:**
- `test_pattern`: Patrón para filtrar tests (ej: "test_auth", "test_client_request")
""")
async def run_specific_tests(test_pattern: str):
    """Ejecuta tests específicos basados en un patrón - Solo ADMIN"""
    # FORZAR el uso de la base de datos de test para seguridad
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = settings.TEST_DATABASE_URL

    try:
        # Crear archivo temporal para el reporte JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json_report_path = temp_file.name

        cmd = [
            "pytest",
            f"app/test/{test_pattern}",
            "--json-report",
            f"--json-report-file={json_report_path}",
            "--json-report-indent=2",
            "-v"
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )

        stdout, stderr = process.communicate()

        # Leer el reporte JSON
        results = {"success": process.returncode ==
                   0, "stdout": stdout, "stderr": stderr}

        if os.path.exists(json_report_path):
            with open(json_report_path, 'r') as f:
                json_data = json.load(f)
            results.update(json_data)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=results
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ejecutando tests específicos: {str(e)}"
        )
    finally:
        # Restaurar la configuración original
        if original_database_url:
            os.environ["DATABASE_URL"] = original_database_url
        else:
            os.environ.pop("DATABASE_URL", None)

        # Limpiar archivo temporal
        if os.path.exists(json_report_path):
            os.unlink(json_report_path)
