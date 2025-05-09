from sqlmodel import select, and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
from app.models.driver_documents import DriverDocuments, DriverStatus,DriverDocumentsCreateRequest
from app.models.user import User
from app.models.document_type import DocumentType
from fastapi import HTTPException, status
from sqlalchemy import func

class VerifyDocsService:
    def __init__(self, db):
        self.db = db

    def get_users_with_pending_docs(self) -> List[User]:
        """Lista usuarios con documentos pendientes"""
        query = (
            select(User)
            .join(DriverDocuments)
            .where(DriverDocuments.status == DriverStatus.PENDING)
            .distinct()
        )
        return self.db.exec(query).all()

    def get_users_with_all_approved_docs(self) -> List[User]:
        """Lista usuarios con todos sus documentos aprobados"""
        users_with_non_approved = (
            select(DriverDocuments.user_id)
            .where(DriverDocuments.status != DriverStatus.APPROVED)
        )

        query = (
            select(User)
            .join(DriverDocuments)
            .where(
                and_(
                    DriverDocuments.status == DriverStatus.APPROVED,
                    User.id.not_in(users_with_non_approved)
                )
            )
            .distinct()
        )
        return self.db.exec(query).all()

    def get_users_with_rejected_docs(self) -> List[User]:
        """Lista usuarios con documentos rechazados"""
        query = (
            select(User)
            .join(DriverDocuments)
            .where(DriverDocuments.status == DriverStatus.REJECTED)
            .distinct()
        )
        return self.db.exec(query).all()

    def get_users_with_expired_docs(self) -> List[User]:
        """Lista usuarios con documentos expirados"""
        query = (
            select(User)
            .join(DriverDocuments)
            .where(DriverDocuments.status == DriverStatus.EXPIRED)
            .distinct()
        )
        return self.db.exec(query).all()

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

    def check_soon_to_expire_documents(self) -> List[dict]:
        """Verifica documentos próximos a expirar"""
        current_date = datetime.utcnow()
        warning_date = current_date + timedelta(days=7)

        query = (
            select(DriverDocuments, User)
            .join(User)
            .where(
                and_(
                    DriverDocuments.status == DriverStatus.APPROVED,
                    DriverDocuments.expiration_date <= warning_date,
                    DriverDocuments.expiration_date > current_date
                )
            )
        )
        results = self.db.exec(query).all()

        warnings = []
        for doc, user in results:
            warnings.append({
                "user_id": user.id,
                "document_id": doc.id,
                "expiration_date": doc.expiration_date,
                "days_remaining": (doc.expiration_date - current_date).days
            })

        return warnings

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