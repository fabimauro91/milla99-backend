#!/usr/bin/env python3
"""
Script independiente para ejecutar tests en entorno QA.
Este script se ejecuta de forma aislada sin afectar el servidor principal.
"""

import os
import sys
import subprocess
import tempfile
import json
from pathlib import Path
from datetime import datetime


def setup_qa_environment():
    """Configura el entorno QA de forma aislada"""
    print("Configurando entorno QA aislado...")

    # Establecer variable de entorno para QA
    os.environ["ENVIRONMENT"] = "qa"

    # Verificar que el archivo de configuración QA existe
    qa_config_file = Path("env.qa")
    if not qa_config_file.exists():
        print("ERROR: No se encontro el archivo env.qa")
        return False

    print("Entorno QA configurado correctamente")
    print("Base de datos: milla99_test")
    return True


def run_tests_with_json_output() -> dict:
    """Ejecuta los tests y devuelve resultados en formato JSON"""
    # FORZAR el uso de la base de datos de test
    os.environ["DATABASE_URL"] = "mysql+mysqlconnector://root:root@localhost:3306/milla99_test"

    print("FORZANDO uso de base de datos de test")
    print("Entorno actual: QA (aislado)")

    # Crear archivo temporal para el reporte JSON
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        json_report_path = temp_file.name

    try:
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
        # Limpiar archivo temporal
        if os.path.exists(json_report_path):
            os.unlink(json_report_path)


def run_tests_with_html_output() -> Path:
    """Ejecuta los tests y genera un reporte HTML"""
    # FORZAR el uso de la base de datos de test
    os.environ["DATABASE_URL"] = "mysql+mysqlconnector://root:root@localhost:3306/milla99_test"

    print("FORZANDO uso de base de datos de test")
    print("Entorno actual: QA (aislado)")

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
        return html_report_path
    else:
        raise Exception(f"Error generando reporte HTML: {stderr}")


def main():
    """Función principal"""
    print("Ejecutando tests en entorno QA aislado...")
    print("=" * 50)

    if not setup_qa_environment():
        sys.exit(1)

    try:
        # Ejecutar tests y generar reporte HTML
        html_report_path = run_tests_with_html_output()

        # Devolver la URL del reporte
        report_url = f"/static/reports/{html_report_path.name}"

        result = {
            "success": True,
            "message": "Reporte HTML generado exitosamente en entorno QA",
            "report_url": report_url,
            "file_path": html_report_path,
            "report_name": html_report_path.name,
            "environment": "qa",
            "database_used": "mysql+mysqlconnector://root:root@localhost:3306/milla99_test"
        }

        # Imprimir resultado en formato JSON para que el servidor principal lo capture
        print("\n" + "=" * 50)
        print("RESULTADO:")
        print(json.dumps(result, indent=2))

        return result

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "environment": "qa"
        }
        print("\nERROR:")
        print(json.dumps(error_result, indent=2))
        return error_result


if __name__ == "__main__":
    main()
