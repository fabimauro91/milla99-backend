#!/usr/bin/env python3
"""
Script para ejecutar la aplicación en entorno QA.
Este script asegura que siempre se use la base de datos de test.
"""

import os
import sys
import uvicorn
from pathlib import Path


def setup_qa_environment():
    """Configura el entorno QA"""
    print("🔧 Configurando entorno QA...")

    # Establecer variable de entorno para QA
    os.environ["ENVIRONMENT"] = "qa"

    # Verificar que el archivo de configuración QA existe
    qa_config_file = Path("env.qa")
    if not qa_config_file.exists():
        print("❌ Error: No se encontró el archivo env.qa")
        print("💡 Asegúrate de que el archivo env.qa existe en el directorio raíz")
        sys.exit(1)

    print("✅ Entorno QA configurado correctamente")
    print("📋 Usando configuración de: env.qa")
    print("🧪 Base de datos: milla99_test")


def main():
    """Función principal"""
    setup_qa_environment()

    print("\n🚀 Iniciando aplicación en modo QA...")
    print("📊 La aplicación usará SIEMPRE la base de datos de test")
    print("🔒 Los endpoints de testing están disponibles")
    print("🌐 Servidor disponible en: http://localhost:8000")
    print("📚 Documentación en: http://localhost:8000/docs")
    print("\n" + "="*50)

    # Ejecutar uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
