from sqlmodel import select, and_, or_, SQLModel
from datetime import datetime, timedelta
from typing import List, Optional
from app.models.driver_documents import DriverDocuments, DriverStatus,DriverDocumentsCreateRequest
from app.models.user import User
from app.models.document_type import DocumentType
from app.models.user_has_roles import UserHasRole, RoleStatus
from fastapi import HTTPException, status
from sqlalchemy import func
from pydantic import BaseModel
from uuid import UUID

# modelo  para la respuesta de listas en ususario
class UserWithDocs(BaseModel):
    user: User
    documents: List[DriverDocuments]

    class Config:
        from_attributes = True

# Primero, creamos un modelo para la respuesta del documento
class DocumentExpirationInfo(SQLModel):
    document_id: UUID
    expiration_date: datetime
    days_remaining: int

    class Config:
        from_attributes = True

# Modelo para la respuesta completa
class UserWithExpiringDocsResponse(SQLModel):
    # Datos del usuario
    user_id: UUID
    user_full_name: str
    user_phone: str
    user_country_code: str
    # Datos de los documentos
    warning: List[DocumentExpirationInfo]

    class Config:
        from_attributes = True

class VerifyDocsService:
    def __init__(self, db):
        self.db = db

    

    def get_users_with_pending_docs(self) -> List[UserWithDocs]:
        """Lista usuarios con documentos pendientes y sus documentos"""
        # Primero obtenemos los usuarios con documentos pendientes
        users_query = (
            select(User)
            .join(DriverDocuments)
            .where(DriverDocuments.status == DriverStatus.PENDING)
            .distinct()
        )
        users = self.db.exec(users_query).all()

        result = []
        for user in users:
            # Para cada usuario, obtenemos sus documentos pendientes
            docs_query = (
                select(DriverDocuments)
                .where(
                    DriverDocuments.user_id == user.id,
                    DriverDocuments.status == DriverStatus.PENDING
                )
            )
            pending_docs = self.db.exec(docs_query).all()

            result.append(UserWithDocs(
                user=user,
                documents=pending_docs
            ))

        return result
        


    def get_users_with_all_approved_docs(self) -> List[User]:
        """Lista usuarios con todos sus documentos aprobados y rol aprobado"""
        users_with_non_approved = (
            select(DriverDocuments.user_id)
            .where(DriverDocuments.status != DriverStatus.APPROVED)
        )

        query = (
            select(User)
            .join(DriverDocuments)
            .join(UserHasRole, User.id == UserHasRole.id_user)  # Join con UserHasRole
            .where(
                and_(
                    DriverDocuments.status == DriverStatus.APPROVED,
                    User.id.not_in(users_with_non_approved),
                    UserHasRole.status == RoleStatus.APPROVED,  # Condición para UserHasRole
                    UserHasRole.id_rol == "DRIVER"  # Asegurarse que sea rol conductor
                )
            )
            .distinct()
        )
        return self.db.exec(query).all()
    

    def update_user_role_status(self):
        """
        Actualiza el status en UserHasRole basado en el estado de los documentos
        """
        # Primero obtenemos todos los usuarios con rol DRIVER
        driver_users = (
            select(UserHasRole)
            .where(
                and_(
                    UserHasRole.id_rol == "DRIVER",
                    UserHasRole.is_verified == True
                )
            )
        )
        driver_users_result = self.db.exec(driver_users).all()

        for user_role in driver_users_result:
            # Contamos los documentos aprobados del usuario
            docs_query = (
                select(func.count(DriverDocuments.id))
                .where(
                    and_(
                        DriverDocuments.user_id == user_role.id_user,
                        DriverDocuments.status == DriverStatus.APPROVED
                    )
                )
            )
            approved_docs_count = self.db.exec(docs_query).first()

            # Contamos el total de documentos del usuario
            total_docs_query = (
                select(func.count(DriverDocuments.id))
                .where(DriverDocuments.user_id == user_role.id_user)
            )
            total_docs = self.db.exec(total_docs_query).first()

            # Si tiene todos los documentos y todos están aprobados
            if total_docs == 4 and approved_docs_count == 4:
                user_role.status = RoleStatus.APPROVED
            else:
                user_role.status = RoleStatus.PENDING

            self.db.add(user_role)

        self.db.commit()
        return {"message": "Estados de roles actualizados correctamente"}
    


    def get_users_with_rejected_docs(self) -> List[UserWithDocs]:
        """Lista usuarios con documentos rechazados"""
        query = (
            select(User)
            .join(DriverDocuments)
            .where(DriverDocuments.status == DriverStatus.REJECTED)
            .distinct()
        )

        users = self.db.exec(query).all()

        result = []
        for user in users:
            # Para cada usuario, obtenemos sus documentos revocado
            docs_query = (
                select(DriverDocuments)
                .where(
                    DriverDocuments.user_id == user.id,
                    DriverDocuments.status == DriverStatus.REJECTED
                )
            )
            rejected_docs = self.db.exec(docs_query).all()

            result.append(UserWithDocs(
                user=user,
                documents=rejected_docs
            ))
        return result
    


    def get_users_with_expired_docs(self) -> List[UserWithDocs]:
        """Lista usuarios con documentos expirados"""
        query = (
            select(User)
            .join(DriverDocuments)
            .where(DriverDocuments.status == DriverStatus.EXPIRED)
            .distinct()
        )
        users = self.db.exec(query).all()

        result = []
        for user in users:
            # Para cada usuario, obtenemos sus documentos pendientes
            docs_query = (
                select(DriverDocuments)
                .where(
                    DriverDocuments.user_id == user.id,
                    DriverDocuments.status == DriverStatus.EXPIRED
                )
            )
            expired_docs = self.db.exec(docs_query).all()

            result.append(UserWithDocs(
                user=user,
                documents=expired_docs
            ))

        return result
    

    #actualiza los documentos que se venciron en fecha a expirado
    def update_expired_documents(self) -> int:
        """Actualiza documentos expirados"""
        current_date = datetime.utcnow()
        query = (
            select(DriverDocuments)
            .where(
                and_(
                    DriverDocuments.status == DriverStatus.APPROVED,
                    DriverDocuments.expiration_date < current_date
                )
            )
        )
        expired_docs = self.db.exec(query).all()

        count = 0
        for doc in expired_docs:
            doc.status = DriverStatus.EXPIRED
            count += 1

        self.db.commit()
        return count


    #muestra los usuarios que tienen documentos proximos a vencersen en fecha
    def check_soon_to_expire_documents(self) -> List[UserWithExpiringDocsResponse]:
        """Verifica documentos próximos a expirar"""
        current_date = datetime.utcnow()
        warning_date = current_date + timedelta(days=7)

        # Primero obtenemos los usuarios y documentos
        query = (
            select(User, DriverDocuments)
            .join(DriverDocuments)
            .where(
                and_(
                    DriverDocuments.status == DriverStatus.APPROVED,
                    DriverDocuments.expiration_date <= warning_date,
                    DriverDocuments.expiration_date > current_date
                )
            )
        )
        results = self.db.exec(query).all()

        # se organiza resultados por usuario
        users_dict = {}
        for user, doc in results:
            if user.id not in users_dict:
                users_dict[user.id] = {
                    "user_id": user.id,
                    "user_full_name": user.full_name,
                    "user_phone": user.phone_number,
                    "user_country_code": user.country_code,
                    "warning": []
                }

            # Calculamos los días restantes
            days_remaining = (doc.expiration_date - current_date).days

            # Añadimos la información del documento
            doc_info = DocumentExpirationInfo(
                document_id=doc.id,
                expiration_date=doc.expiration_date,
                days_remaining=days_remaining
            )
            users_dict[user.id]["warning"].append(doc_info)

        # Convertimos el diccionario en una lista de respuestas
        return [UserWithExpiringDocsResponse(**user_data) for user_data in users_dict.values()]
    


    def update_documents(self, updates: List[dict]) -> List[DriverDocuments]:
        """Actualiza múltiples documentos"""
        updated_docs = []

        for update in updates:
            doc_id = update.pop("id", None)
            if not doc_id:
                continue

            doc = self.db.get(DriverDocuments, doc_id)
            if not doc:
                continue

            for key, value in update.items():
                if hasattr(doc, key):
                    setattr(doc, key, value)

            updated_docs.append(doc)

        self.db.commit()
        return updated_docs
    
    def create_document(self, document_data: DriverDocumentsCreateRequest) -> DriverDocuments:
        """Crea un nuevo documento para un usuario"""
        try:
            # Verificar si el usuario existe
            user = self.db.get(User, document_data.user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Verificar si el tipo de documento existe
            document_type = self.db.get(DocumentType, document_data.document_type_id)
            if not document_type:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document type not found"
                )

            # Crear el nuevo documento
            new_document = DriverDocuments(
                user_id=document_data.user_id,
                document_type_id=document_data.document_type_id,
                document_front_url=document_data.document_front_url,
                document_back_url=document_data.document_back_url,
                expiration_date=document_data.expiration_date,
                status=DriverStatus.PENDING  # Por defecto, el estado es pendiente
            )

            self.db.add(new_document)
            self.db.commit()
            self.db.refresh(new_document)

            return new_document

        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )