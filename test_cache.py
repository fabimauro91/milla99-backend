#!/usr/bin/env python3
"""
Script de prueba para verificar el funcionamiento del cache con Redis
"""

import requests
import time
import json

# Configuración
BASE_URL = "http://localhost:8000"
CACHE_TEST_ENDPOINTS = [
    "/cache-test/redis-status",
    "/cache-test/project-settings",
    "/cache-test/cache-stats"
]


def test_redis_connection():
    """Prueba la conexión con Redis"""
    print("🔍 Probando conexión con Redis...")

    try:
        response = requests.get(f"{BASE_URL}/cache-test/redis-status")
        data = response.json()

        if response.status_code == 200:
            print(f"✅ {data['message']}")
            return True
        else:
            print(f"❌ Error: {data.get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        return False


def test_project_settings_cache():
    """Prueba el cache de configuraciones del proyecto"""
    print("\n🔍 Probando cache de ProjectSettings...")

    try:
        response = requests.get(f"{BASE_URL}/cache-test/project-settings")
        data = response.json()

        if response.status_code == 200:
            print("✅ Test de ProjectSettings completado")
            print(f"   Primera consulta: {data['primera_consulta']['tiempo']}")
            print(f"   Segunda consulta: {data['segunda_consulta']['tiempo']}")
            print(f"   Mejora: {data['mejora']}")
            return True
        else:
            print(f"❌ Error: {data.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_cache_stats():
    """Prueba las estadísticas del cache"""
    print("\n🔍 Obteniendo estadísticas del cache...")

    try:
        response = requests.get(f"{BASE_URL}/cache-test/cache-stats")
        data = response.json()

        if response.status_code == 200:
            print("✅ Estadísticas del cache:")
            print(f"   Total de claves: {data.get('total_keys', 0)}")
            if 'keys_by_prefix' in data:
                for prefix, count in data['keys_by_prefix'].items():
                    print(f"   - {prefix}: {count} claves")
            return True
        else:
            print(f"❌ Error: {data.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_user_balance_cache(user_id):
    """Prueba el cache de balance de usuario"""
    print(f"\n🔍 Probando cache de balance para usuario {user_id}...")

    try:
        response = requests.get(
            f"{BASE_URL}/cache-test/user-balance/{user_id}")
        data = response.json()

        if response.status_code == 200:
            print("✅ Test de User Balance completado")
            print(f"   Primera consulta: {data['primera_consulta']['tiempo']}")
            print(f"   Segunda consulta: {data['segunda_consulta']['tiempo']}")
            print(f"   Mejora: {data['mejora']}")
            return True
        else:
            print(f"❌ Error: {data.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_driver_search_cache():
    """Prueba el cache de búsqueda de conductores"""
    print("\n🔍 Probando cache de búsqueda de conductores...")

    try:
        response = requests.get(f"{BASE_URL}/cache-test/driver-search")
        data = response.json()

        if response.status_code == 200:
            print("✅ Test de Driver Search completado")
            print(f"   Primera consulta: {data['primera_consulta']['tiempo']}")
            print(f"   Segunda consulta: {data['segunda_consulta']['tiempo']}")
            print(f"   Mejora: {data['mejora']}")
            return True
        else:
            print(f"❌ Error: {data.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def clear_cache():
    """Limpia todo el cache"""
    print("\n🧹 Limpiando cache...")

    try:
        response = requests.delete(f"{BASE_URL}/cache-test/clear-cache")
        data = response.json()

        if response.status_code == 200:
            print(
                f"✅ Cache limpiado: {data.get('claves_eliminadas', 0)} claves eliminadas")
            return True
        else:
            print(f"❌ Error: {data.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas de cache con Redis")
    print("=" * 50)

    # Test 1: Conexión con Redis
    if not test_redis_connection():
        print("❌ No se puede continuar sin Redis")
        return

    # Test 2: Cache de ProjectSettings
    test_project_settings_cache()

    # Test 3: Cache de User Balance (necesita un user_id válido)
    # test_user_balance_cache("some-user-id")

    # Test 4: Cache de Driver Search
    test_driver_search_cache()

    # Test 5: Estadísticas del cache
    test_cache_stats()

    # Test 6: Limpiar cache
    clear_cache()

    print("\n" + "=" * 50)
    print("✅ Pruebas de cache completadas")


if __name__ == "__main__":
    main()
