from sqlmodel import select, and_, or_, SQLModel
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from app.models.driver_documents import DocumentsUpdate, DriverDocuments, DriverStatus, DriverDocumentsCreateRequest
from app.models.user import User
from app.models.document_type import DocumentType
from app.models.user_has_roles import UserHasRole, RoleStatus
from fastapi import HTTPException, status
from sqlalchemy import func
from pydantic import BaseModel
from uuid import UUID
from app.models.driver_info import DriverInfo

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
        """Lista usuarios con documentos pendientes y sus documentos, pero solo para conductores NO verificados (is_verified = False)"""
        # Primero obtenemos los usuarios que son conductores NO verificados
        unverified_drivers_query = (
            select(User)
            .join(UserHasRole, User.id == UserHasRole.id_user)
            .where(
                and_(
                    UserHasRole.id_rol == "DRIVER",
                    UserHasRole.is_verified == False  # Solo conductores no verificados
                )
            )
        )
        unverified_drivers = self.db.exec(unverified_drivers_query).all()

        result = []
        for user in unverified_drivers:
            # Para cada conductor no verificado, obtenemos sus documentos pendientes
            docs_query = (
                select(DriverDocuments)
                .join(DriverInfo, DriverDocuments.driver_info_id == DriverInfo.id)
                .where(
                    and_(
                        DriverInfo.user_id == user.id,
                        DriverDocuments.status == DriverStatus.PENDING
                    )
                )
            )
            pending_docs = self.db.exec(docs_query).all()

            # Solo añadimos al resultado si el conductor tiene documentos pendientes
            if pending_docs:
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
            # Join con UserHasRole
            .join(UserHasRole, User.id == UserHasRole.id_user)
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

    def get_verification_status(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas sobre el estado de verificación de los conductores.
        """
        # Total de conductores
        total_drivers = self.db.exec(
            select(func.count(UserHasRole.id))
            .where(UserHasRole.id_rol == "DRIVER")
        ).first() or 0

        # Conductores verificados (is_verified = True)
        verified_drivers = self.db.exec(
            select(func.count(UserHasRole.id))
            .where(
                and_(
                    UserHasRole.id_rol == "DRIVER",
                    UserHasRole.is_verified == True
                )
            )
        ).first() or 0

        # Conductores con status APPROVED
        approved_drivers = self.db.exec(
            select(func.count(UserHasRole.id))
            .where(
                and_(
                    UserHasRole.id_rol == "DRIVER",
                    UserHasRole.status == RoleStatus.APPROVED
                )
            )
        ).first() or 0

        # Conductores con documentos pendientes
        drivers_with_pending_docs = self.db.exec(
            select(func.count(func.distinct(DriverInfo.user_id)))
            .join(DriverDocuments, DriverInfo.id == DriverDocuments.driver_info_id)
            .where(DriverDocuments.status == DriverStatus.PENDING)
        ).first() or 0

        return {
            "total_drivers": total_drivers,
            "verified_drivers": verified_drivers,
            "approved_drivers": approved_drivers,
            "drivers_with_pending_docs": drivers_with_pending_docs,
            "verification_rate": (verified_drivers / total_drivers * 100) if total_drivers > 0 else 0,
            "approval_rate": (approved_drivers / total_drivers * 100) if total_drivers > 0 else 0
        }

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

    # actualiza los documentos que se venciron en fecha a expirado

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

    # muestra los usuarios que tienen documentos proximos a vencersen en fecha

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

    def update_documents(self, updates: List[DocumentsUpdate]) -> List[DriverDocuments]:
        """Actualiza múltiples documentos"""
        updated_docs = []
        driver_info_ids_affected = set()  # Usamos un set para evitar duplicados

        try:
            for update in updates:
                # Acceder al atributo id directamente
                doc_id = update.id
                if not doc_id:
                    continue

                doc = self.db.get(DriverDocuments, doc_id)
                if not doc:
                    continue

                # Guardar el driver_info_id antes de actualizar
                if doc.driver_info_id:
                    driver_info_ids_affected.add(doc.driver_info_id)

                # Convertir el modelo a diccionario y excluir campos None y el id
                update_data = update.model_dump(
                    exclude_unset=True, exclude={'id'})

                # Actualizar solo los campos que tienen valor
                for key, value in update_data.items():
                    if hasattr(doc, key) and value is not None:
                        setattr(doc, key, value)

                updated_docs.append(doc)

            if not updated_docs:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se encontraron documentos válidos para actualizar"
                )

            self.db.commit()  # Commit all individual document updates

            # Ahora, para cada driver cuyos documentos fueron actualizados, verificar si su estado is_verified necesita cambiar
            for d_info_id in driver_info_ids_affected:
                if d_info_id:  # Asegurar que driver_info_id no es None
                    # Obtener el registro DriverInfo
                    driver_info = self.db.get(DriverInfo, d_info_id)
                    if driver_info:
                        # Obtener el registro UserHasRole para este driver
                        user_has_role = self.db.exec(
                            select(UserHasRole).where(
                                UserHasRole.id_user == driver_info.user_id,
                                UserHasRole.id_rol == "DRIVER"  # Asumiendo 'DRIVER' es el rol para conductores
                            )
                        ).first()

                        if user_has_role:
                            # Definir los IDs de tipo de documento requeridos
                            # 1=Tarjeta de Propiedad, 2=Licencia, 3=SOAT, 4=Tecnomecánica
                            REQUIRED_DOC_TYPE_IDS = [1, 2, 3, 4]

                            # Contar cuántos de los tipos de documento *requeridos* están actualmente APROBADOS para este conductor
                            approved_required_doc_types_count = self.db.exec(
                                select(func.count(func.distinct(
                                    DriverDocuments.document_type_id)))
                                .where(
                                    DriverDocuments.driver_info_id == d_info_id,
                                    DriverDocuments.status == DriverStatus.APPROVED,
                                    DriverDocuments.document_type_id.in_(
                                        REQUIRED_DOC_TYPE_IDS)
                                )
                            ).first() or 0

                            # Verificar si los 4 tipos de documentos requeridos están aprobados
                            if approved_required_doc_types_count == len(REQUIRED_DOC_TYPE_IDS):
                                if not user_has_role.is_verified:  # Solo actualizar si no es ya True
                                    user_has_role.is_verified = True
                                    user_has_role.status = RoleStatus.APPROVED  # Actualizar status a APPROVED
                                    self.db.add(user_has_role)
                                    self.db.commit()  # Commit este cambio específico para UserHasRole
                                    self.db.refresh(user_has_role)
                            else:
                                # Si no todos los 4 documentos requeridos están aprobados, asegurar que is_verified sea False
                                if user_has_role.is_verified:  # Solo actualizar si es actualmente True
                                    user_has_role.is_verified = False
                                    user_has_role.status = RoleStatus.PENDING  # Mantener status como PENDING
                                    self.db.add(user_has_role)
                                    self.db.commit()  # Commit este cambio específico para UserHasRole
                                    self.db.refresh(user_has_role)

            return updated_docs

        except HTTPException as he:
            self.db.rollback()
            raise he
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al actualizar documentos: {str(e)}"
            )

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
            document_type = self.db.get(
                DocumentType, document_data.document_type_id)
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
