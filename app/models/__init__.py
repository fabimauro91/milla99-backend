
# Módulo models: define las clases y estructuras de datos principales de la aplicación (SQLModel/Pydantic)
# El orden de las importaciones es importante para la creación de las tablas en la base de datos
# Las tablas se crean en el orden en que se importan sus modelos
# Las tablas con claves foráneas deben importarse después de las tablas que referencian

from .role import Role
from .user_has_roles import UserHasRole
from .document_type import DocumentType
from .driver_documents import DriverDocuments