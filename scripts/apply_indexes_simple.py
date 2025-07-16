#!/usr/bin/env python3
"""
Script simple para aplicar índices de optimización
No depende del módulo app
"""

import mysql.connector
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


def get_database_connection():
    """Obtener conexión a la base de datos"""
    # Obtener DATABASE_URL del .env
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ Error: DATABASE_URL no encontrada en .env")
        return None

    print(f"🔍 DATABASE_URL encontrada: {database_url}")

    # Parsear DATABASE_URL
    try:
        # Remover el prefijo del driver si existe
        if database_url.startswith("mysql://"):
            url_parts = database_url.replace("mysql://", "")
        elif database_url.startswith("mysql+mysqlconnector://"):
            url_parts = database_url.replace("mysql+mysqlconnector://", "")
        else:
            url_parts = database_url

        print(f"🔍 URL sin prefijo: {url_parts}")

        # Buscar la última / para separar credenciales/host de la base de datos
        last_slash = url_parts.rfind("/")
        if last_slash == -1:
            print("❌ Error: Formato de URL inválido")
            return None

        credentials_host = url_parts[:last_slash]
        database = url_parts[last_slash + 1:]

        print(f"🔍 Credenciales/Host: {credentials_host}")
        print(f"🔍 Base de datos: {database}")

        # Separar usuario:contraseña y host:puerto
        if "@" in credentials_host:
            credentials, host_port = credentials_host.split("@")
            if ":" in credentials:
                username, password = credentials.split(":", 1)
            else:
                username = credentials
                password = ""
        else:
            # Sin @, asumir que es solo host:puerto
            username = "root"
            password = ""
            host_port = credentials_host

        # Separar host y puerto
        if ":" in host_port:
            host, port = host_port.split(":")
            port = int(port)
        else:
            host = host_port
            port = 3306

        print(f"🔌 Conectando a: {host}:{port}/{database}")
        print(f"🔌 Usuario: {username}")

        return mysql.connector.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database
        )

    except Exception as e:
        print(f"❌ Error parseando DATABASE_URL: {e}")
        print(f"🔍 URL original: {database_url}")
        return None


def check_existing_indexes(cursor):
    """Verificar índices existentes"""
    print("🔍 Verificando índices existentes...")

    cursor.execute("""
        SELECT 
            TABLE_NAME,
            INDEX_NAME,
            COLUMN_NAME
        FROM INFORMATION_SCHEMA.STATISTICS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'user' 
        AND INDEX_NAME IN ('idx_phone_number', 'idx_country_phone', 'idx_created_at')
    """)

    existing_indexes = cursor.fetchall()

    if existing_indexes:
        print("Índices existentes:")
        for row in existing_indexes:
            print(f"  - {row[1]} en {row[2]}")
    else:
        print("No se encontraron índices de optimización")

    return existing_indexes


def create_index_safe(cursor, index_name, sql):
    """Crear índice de forma segura"""
    try:
        print(f"  - Creando {index_name}...")
        cursor.execute(sql)
        print(f"    ✅ {index_name} creado exitosamente")
        return True
    except mysql.connector.Error as e:
        if e.errno == 1061:  # Duplicate key name
            print(f"    ⚠️ {index_name} ya existe")
            return True
        else:
            print(f"    ❌ Error creando {index_name}: {e}")
            return False


def create_indexes(cursor):
    """Crear índices de optimización"""
    try:
        print("🔧 Creando índices...")

        # Crear índice en phone_number
        success1 = create_index_safe(
            cursor,
            "índice en phone_number",
            "CREATE INDEX idx_phone_number ON user(phone_number)"
        )

        # Crear índice compuesto en country_code + phone_number
        success2 = create_index_safe(
            cursor,
            "índice compuesto en country_code + phone_number",
            "CREATE INDEX idx_country_phone ON user(country_code, phone_number)"
        )

        # Crear índice en created_at
        success3 = create_index_safe(
            cursor,
            "índice en created_at",
            "CREATE INDEX idx_created_at ON user(created_at)"
        )

        if success1 and success2 and success3:
            print("✅ Todos los índices creados exitosamente")
        else:
            print("⚠️ Algunos índices no se pudieron crear")

    except Exception as e:
        print(f"❌ Error creando índices: {e}")
        raise


def verify_indexes(cursor):
    """Verificar que los índices se crearon correctamente"""
    print("🔍 Verificando índices creados...")

    cursor.execute("""
        SHOW INDEX FROM user 
        WHERE Key_name IN ('idx_phone_number', 'idx_country_phone', 'idx_created_at')
    """)

    indexes = cursor.fetchall()

    print("Índices verificados:")
    for index in indexes:
        print(f"  - {index[2]} en {index[4]}")  # Key_name y Column_name

    return len(indexes) == 3


def show_table_stats(cursor):
    """Mostrar estadísticas de la tabla"""
    print("📊 Estadísticas de la tabla:")

    cursor.execute("""
        SELECT 
            TABLE_NAME,
            TABLE_ROWS,
            DATA_LENGTH,
            INDEX_LENGTH
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'user'
    """)

    stats = cursor.fetchone()

    if stats:
        print(f"  - Filas: {stats[1]:,}")
        print(f"  - Tamaño datos: {stats[2]:,} bytes")
        print(f"  - Tamaño índices: {stats[3]:,} bytes")


def main():
    """Función principal"""
    print("🚀 Iniciando optimización de índices")

    # Conectar a la base de datos
    connection = get_database_connection()
    if not connection:
        return

    try:
        cursor = connection.cursor()

        # Verificar índices existentes
        existing = check_existing_indexes(cursor)

        # Crear índices
        create_indexes(cursor)

        # Verificar que se crearon correctamente
        success = verify_indexes(cursor)

        if success:
            print("✅ Optimización completada exitosamente")
        else:
            print("⚠️ Algunos índices no se crearon correctamente")

        # Mostrar estadísticas
        show_table_stats(cursor)

        # Commit de los cambios
        connection.commit()

    except Exception as e:
        print(f"❌ Error durante la optimización: {e}")
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()
        print("🔌 Conexión cerrada")


if __name__ == "__main__":
    main()
