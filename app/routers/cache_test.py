"""
Router de prueba para verificar el funcionamiento del cache
"""

from fastapi import APIRouter, Depends, HTTPException
from app.core.db import SessionDep
from app.core.cache import cache
from app.services.project_settings_service import get_busy_driver_config
from app.services.transaction_service import TransactionService
from app.services.driver_search_service import DriverSearchService
from uuid import UUID
import time

router = APIRouter(prefix="/cache-test", tags=["cache-test"])


@router.get("/redis-status")
async def check_redis_status():
    """Verifica el estado de conexión con Redis"""
    try:
        if cache.redis_client:
            cache.redis_client.ping()
            return {
                "status": "connected",
                "message": "Redis cache está funcionando correctamente"
            }
        else:
            return {
                "status": "disconnected",
                "message": "Redis cache no está disponible"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error conectando a Redis: {str(e)}"
        }


@router.get("/project-settings")
async def test_project_settings_cache(session: SessionDep):
    """Prueba el cache de configuraciones del proyecto"""
    start_time = time.time()

    # Primera consulta (debe ir a DB)
    config1 = get_busy_driver_config(session)
    time1 = time.time() - start_time

    # Segunda consulta (debe venir del cache)
    start_time = time.time()
    config2 = get_busy_driver_config(session)
    time2 = time.time() - start_time

    return {
        "primera_consulta": {
            "tiempo": f"{time1:.3f}s",
            "config": config1
        },
        "segunda_consulta": {
            "tiempo": f"{time2:.3f}s",
            "config": config2
        },
        "mejora": f"{((time1 - time2) / time1 * 100):.1f}%" if time1 > 0 else "0%"
    }


@router.get("/user-balance/{user_id}")
async def test_user_balance_cache(user_id: str, session: SessionDep):
    """Prueba el cache de balance de usuario"""
    try:
        transaction_service = TransactionService(session)

        start_time = time.time()
        # Primera consulta (debe ir a DB)
        balance1 = transaction_service.get_user_balance(UUID(user_id))
        time1 = time.time() - start_time

        start_time = time.time()
        # Segunda consulta (debe venir del cache)
        balance2 = transaction_service.get_user_balance(UUID(user_id))
        time2 = time.time() - start_time

        return {
            "primera_consulta": {
                "tiempo": f"{time1:.3f}s",
                "balance": balance1
            },
            "segunda_consulta": {
                "tiempo": f"{time2:.3f}s",
                "balance": balance2
            },
            "mejora": f"{((time1 - time2) / time1 * 100):.1f}%" if time1 > 0 else "0%"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


@router.get("/driver-search")
async def test_driver_search_cache(
    session: SessionDep,
    lat: float = 4.7109,
    lng: float = -74.0721,
    vehicle_type_id: int | None = None
):
    """Prueba el cache de búsqueda de conductores"""
    try:
        driver_search_service = DriverSearchService(session)

        start_time = time.time()
        # Primera consulta (debe ir a DB)
        drivers1 = driver_search_service.find_available_drivers(
            lat, lng, vehicle_type_id)
        time1 = time.time() - start_time

        start_time = time.time()
        # Segunda consulta (debe venir del cache)
        drivers2 = driver_search_service.find_available_drivers(
            lat, lng, vehicle_type_id)
        time2 = time.time() - start_time

        return {
            "primera_consulta": {
                "tiempo": f"{time1:.3f}s",
                "conductores_encontrados": len(drivers1)
            },
            "segunda_consulta": {
                "tiempo": f"{time2:.3f}s",
                "conductores_encontrados": len(drivers2)
            },
            "mejora": f"{((time1 - time2) / time1 * 100):.1f}%" if time1 > 0 else "0%"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")


@router.delete("/clear-cache")
async def clear_all_cache():
    """Limpia todo el cache de Redis"""
    try:
        # Eliminar todas las claves de Milla99
        deleted_keys = cache.delete_pattern("milla99:*")
        return {
            "message": f"Cache limpiado exitosamente",
            "claves_eliminadas": deleted_keys
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error limpiando cache: {str(e)}")


@router.get("/cache-stats")
async def get_cache_stats():
    """Obtiene estadísticas del cache"""
    try:
        if not cache.redis_client:
            return {"error": "Redis no está disponible"}

        # Obtener todas las claves de Milla99
        keys = cache.redis_client.keys("milla99:*")

        stats = {
            "total_keys": len(keys),
            "keys_by_prefix": {}
        }

        # Contar claves por prefijo
        for key in keys:
            prefix = key.split(":")[1] if ":" in key else "other"
            stats["keys_by_prefix"][prefix] = stats["keys_by_prefix"].get(
                prefix, 0) + 1

        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")
