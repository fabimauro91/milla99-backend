#!/usr/bin/env python3
"""
Script para ejecutar test de carga optimizado para creación de usuarios
Enfoque: SOLO POST /users/ para medir 3000 requests/minuto
"""

import subprocess
import sys
import os
from datetime import datetime
import requests


def run_user_creation_test():
    """Ejecuta el test de carga optimizado para creación de usuarios"""

    print("INICIANDO TEST DE CARGA - CREACIÓN DE USUARIOS OPTIMIZADO")
    print("ENFOQUE: SOLO POST /users/ para 3000 requests/minuto")
    print("=" * 70)

    # Crear carpeta de reportes si no existe
    response_dir = "app/load_tests/response"
    if not os.path.exists(response_dir):
        os.makedirs(response_dir)

    # Configuración optimizada para 3000 requests/minuto
    config = {
        "users": 300,  # Más usuarios concurrentes
        "spawn_rate": 100,  # Spawn muy rápido
        "run_time": "2m",  # 1 minuto de prueba
        "host": "http://localhost:8000",
        "locustfile": "app/load_tests/locust/load_user_creation_only.py"
    }

    print(f"Usuarios concurrentes: {config['users']}")
    print(f"Tasa de spawn: {config['spawn_rate']} usuarios/segundo")
    print(f"Duración: {config['run_time']}")
    print(f"Objetivo: 3000 requests/minuto (50 requests/segundo)")
    print(f"Host: {config['host']}")
    print(f"Archivo: {config['locustfile']}")
    print("=" * 70)

    # Verificar que el servidor esté corriendo
    print("Verificando que el servidor esté corriendo...")
    try:
        response = requests.get(f"{config['host']}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor está corriendo")
        else:
            print("⚠️ Servidor responde pero con estado inesperado")
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        print(
            "Asegúrate de que el servidor esté corriendo con: uvicorn app.main:app --reload")
        return False

    # Generar timestamp para los archivos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_report = os.path.join(
        response_dir, f"user_creation_only_test_report_{timestamp}.html")
    csv_report = os.path.join(
        response_dir, f"user_creation_only_test_results_{timestamp}.csv")

    # Comando de Locust optimizado
    cmd = [
        "locust",
        "-f", config["locustfile"],
        "--host", config["host"],
        "--users", str(config["users"]),
        "--spawn-rate", str(config["spawn_rate"]),
        "--run-time", config["run_time"],
        "--headless",
        "--html", html_report,
        "--csv", csv_report,
        "--stop-timeout", "10"
    ]

    print(f"Comando: {' '.join(cmd)}")
    print("=" * 70)
    print("Ejecutando test optimizado... (puede tomar unos segundos)")
    print("Los logs detallados aparecerán a continuación:")
    print("=" * 70)

    try:
        # Ejecutar comando con output en tiempo real
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Mostrar output en tiempo real
        for line in process.stdout:
            print(line.rstrip())

        # Esperar a que termine
        process.wait()

        if process.returncode == 0:
            print("\n" + "=" * 70)
            print("✅ Test completado exitosamente")
            print("📊 Reporte HTML generado:", html_report)
            print("📈 Datos CSV generados en:", csv_report)

            # Verificar archivos generados
            print("\n📁 Archivos generados:")
            if os.path.exists(html_report):
                file_size = os.path.getsize(html_report)
                print(f"  📊 Reporte HTML: {html_report} ({file_size} bytes)")
            else:
                print(f"  ❌ Reporte HTML: {html_report} (no encontrado)")

            if os.path.exists(csv_report):
                file_size = os.path.getsize(csv_report)
                print(
                    f"  📈 Estadísticas CSV: {csv_report} ({file_size} bytes)")
            else:
                print(f"  ❌ Estadísticas CSV: {csv_report} (no encontrado)")

            return True
        else:
            print(f"\n❌ Test falló con código de salida: {process.returncode}")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Test falló")
        print(f"Error: {e}")
        if e.stdout:
            print("Output:", e.stdout)
        if e.stderr:
            print("Error:", e.stderr)
        return False
    except Exception as e:
        print(f"❌ Error ejecutando test: {e}")
        return False


def show_help():
    """Muestra ayuda sobre cómo usar el script"""
    print("""
USO DEL SCRIPT DE TEST DE CARGA OPTIMIZADO

Este script ejecuta un test de carga optimizado SOLO para creación de usuarios
con el objetivo de medir si la infraestructura soporta 3000 requests/minuto.

REQUISITOS:
1. Servidor corriendo en http://localhost:8000
2. Locust instalado: pip install locust
3. Base de datos con capacidad para alta carga

EJECUCIÓN:
python app/load_tests/run/run_user_creation_only_test.py

OBJETIVO:
- 3000 requests/minuto = 50 requests/segundo
- Response time < 2 segundos (P95)
- Error rate < 5%

ENFOQUE:
- SOLO POST /users/ (sin autenticación)
- Wait time muy bajo (0.05-0.2s)
- 300 usuarios concurrentes
- Spawn rate alto (100 usuarios/segundo)

MÉTRICAS QUE SE MIDEN:
- Response Time (min, max, avg) por endpoint
- Requests per second (RPS) por endpoint
- Failure rate (%) por endpoint
- Throughput sostenido

REPORTES GENERADOS:
- user_creation_only_test_report_*.html: Reporte detallado con gráficos
- user_creation_only_test_results_*.csv: Estadísticas por endpoint

ANÁLISIS AUTOMÁTICO:
- Alertas de performance lenta (>2s)
- Alertas de errores altos (>5%)
- Verificación de throughput objetivo
""")


def main():
    """Función principal"""
    try:
        success = run_user_creation_test()

        if success:
            print("\n✅ Test completado exitosamente!")
            print("📊 Revisa los reportes generados para analizar los resultados")
        else:
            print("\n❌ El test falló. Revisa los errores arriba.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⏹️ Test interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
