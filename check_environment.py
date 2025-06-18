#!/usr/bin/env python3
"""
Script para verificar la configuración del entorno actual.
Útil para diagnosticar problemas de configuración.
"""

import os
import sys
from pathlib import Path


def check_environment():
    """Verifica la configuración del entorno actual"""
    print("🔍 Verificando configuración del entorno...")
    print("=" * 50)

    # Verificar variable de entorno
    environment = os.getenv("ENVIRONMENT", "development")
    print(f"🌍 Entorno detectado: {environment}")

    # Verificar archivos de configuración
    config_files = {
        "development": "env.development",
        "qa": "env.qa",
        "default": ".env"
    }

    current_config = config_files.get(environment, config_files["default"])
    config_path = Path(current_config)

    if config_path.exists():
        print(f"✅ Archivo de configuración encontrado: {current_config}")
    else:
        print(f"❌ Archivo de configuración NO encontrado: {current_config}")
        return False

    # Verificar variables de entorno críticas
    critical_vars = [
        "DATABASE_URL",
        "TEST_DATABASE_URL",
        "SECRET_KEY",
        "GOOGLE_API_KEY"
    ]

    print("\n📊 Variables de entorno críticas:")
    for var in critical_vars:
        value = os.getenv(var)
        if value:
            # Ocultar valores sensibles
            if "SECRET" in var or "KEY" in var:
                display_value = value[:10] + \
                    "..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: NO DEFINIDA")

    # Verificar conexión a base de datos
    print("\n🗄️ Verificación de base de datos:")
    database_url = os.getenv("DATABASE_URL", "")
    test_database_url = os.getenv("TEST_DATABASE_URL", "")

    if "milla99_test" in database_url:
        print("  🧪 Base de datos principal: TEST (seguro para testing)")
    elif "milla99" in database_url:
        print("  📊 Base de datos principal: PRODUCCIÓN (cuidado con testing)")
    else:
        print("  ❓ Base de datos principal: DESCONOCIDA")

    if "milla99_test" in test_database_url:
        print("  ✅ Base de datos de test: CONFIGURADA")
    else:
        print("  ❌ Base de datos de test: NO CONFIGURADA")

    # Verificar directorios necesarios
    print("\n📁 Verificación de directorios:")
    directories = ["static", "static/reports", "app/test"]

    for directory in directories:
        dir_path = Path(directory)
        if dir_path.exists():
            print(f"  ✅ {directory}/")
        else:
            print(f"  ❌ {directory}/ (NO EXISTE)")

    # Verificar archivos de test
    print("\n🧪 Verificación de archivos de test:")
    test_dir = Path("app/test")
    if test_dir.exists():
        test_files = list(test_dir.glob("test_*.py"))
        if test_files:
            print(f"  ✅ {len(test_files)} archivos de test encontrados")
            for test_file in test_files[:5]:  # Mostrar solo los primeros 5
                print(f"    - {test_file.name}")
            if len(test_files) > 5:
                print(f"    ... y {len(test_files) - 5} más")
        else:
            print("  ❌ No se encontraron archivos de test")
    else:
        print("  ❌ Directorio de tests no existe")

    print("\n" + "=" * 50)

    # Resumen y recomendaciones
    print("📋 RESUMEN Y RECOMENDACIONES:")

    if environment == "qa":
        print("  🧪 Entorno QA detectado - Seguro para testing")
        print("  ✅ Los endpoints de testing usarán la base de datos de test")
    elif environment == "development":
        print("  🛠️ Entorno de desarrollo detectado")
        print("  ⚠️ Los endpoints de testing pueden afectar datos de producción")
        print("  💡 Considera usar 'python run_qa.py' para testing seguro")
    else:
        print("  ❓ Entorno no reconocido")
        print("  💡 Usa 'set ENVIRONMENT=qa' para testing seguro")

    return True


def main():
    """Función principal"""
    try:
        success = check_environment()
        if success:
            print("\n✅ Verificación completada exitosamente")
        else:
            print("\n❌ Se encontraron problemas en la configuración")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error durante la verificación: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
