from sqlmodel import Session, select
from fastapi import HTTPException, status, UploadFile
from app.models.driver_documents import DriverDocuments, DriverDocumentsCreate
from app.models.user import User, UserCreate, UserRead
from app.models.role import Role
from app.models.driver_info import DriverInfo, DriverInfoCreate
from app.models.vehicle_info import VehicleInfo, VehicleInfoCreate
from app.models.driver import DriverFullRead, DriverDocumentsInput
from app.core.db import engine
from app.services.upload_service import upload_service, DocumentType
from typing import Optional
from app.models.driver_response import (
    DriverFullResponse, UserResponse, DriverInfoResponse, VehicleInfoResponse, DriverDocumentsResponse
)
from app.utils.uploads import uploader
from decimal import Decimal
import traceback
from app.models.verify_mount import VerifyMount
from app.models.transaction import Transaction, TransactionType


class DriverService:
    def __init__(self, session: Session):
        self.session = session

    async def create_driver(
        self,
        user_data: UserCreate,
        driver_info_data: DriverInfoCreate,
        vehicle_info_data: VehicleInfoCreate,
        driver_documents_data: DriverDocumentsInput
    ) -> DriverFullResponse:
        with Session(engine) as session:
            try:
                # Buscar usuario por teléfono y país
                existing_user = session.exec(
                    select(User).where(
                        User.phone_number == user_data.phone_number,
                        User.country_code == user_data.country_code
                    )
                ).first()

                if existing_user:
                    # Verificar si ya tiene el rol DRIVER
                    driver_role = session.exec(
                        select(Role).where(Role.id == "DRIVER")).first()
                    if not driver_role:
                        raise HTTPException(
                            status_code=500, detail="Rol DRIVER no existe")
                    if driver_role in existing_user.roles:
                        # Ya es conductor, puedes lanzar error o continuar
                        existing_driver = session.exec(
                            select(DriverInfo)
                            .where(DriverInfo.user_id == existing_user.id)
                        ).first()
                        if existing_driver:
                            driver_info = session.exec(
                                select(DriverInfo).where(
                                    DriverInfo.id == existing_driver.id)
                            ).first()
                            vehicle_info = session.exec(
                                select(VehicleInfo).where(
                                    VehicleInfo.driver_info_id == driver_info.id,
                                    VehicleInfo.vehicle_type_id == 1
                                )
                            ).first()
                            if vehicle_info:
                                raise HTTPException(
                                    status_code=400,
                                    detail="Ya existe un conductor de tipo carro para este usuario.")
                        user = existing_user
                    else:
                        # Asignar el rol DRIVER
                        existing_user.roles.append(driver_role)
                        session.add(existing_user)
                        session.commit()
                        session.refresh(existing_user)
                        user = existing_user
                else:
                    # Crear el Usuario
                    user = User(**user_data.dict())
                    session.add(user)
                    session.commit()
                    session.refresh(user)
                    # Asignar el rol DRIVER
                    driver_role = session.exec(
                        select(Role).where(Role.id == "DRIVER")).first()
                    if not driver_role:
                        raise HTTPException(
                            status_code=500, detail="Rol DRIVER no existe")
                    user.roles.append(driver_role)
                    session.add(user)
                    session.commit()
                    session.refresh(user)

                # Crear VerifyMount con mount=0
                verify_mount = VerifyMount(user_id=user.id, mount=0)
                session.add(verify_mount)
                session.commit()
                session.refresh(verify_mount)

                # 4. Crear el DriverInfo (ya no maneja selfie_url)
                driver_info = DriverInfo(
                    **driver_info_data.dict(),
                    user_id=user.id
                )
                session.add(driver_info)
                session.commit()
                session.refresh(driver_info)

                # 5. Crear el VehicleInfo
                vehicle_info = VehicleInfo(
                    **vehicle_info_data.dict(),
                    driver_info_id=driver_info.id
                )
                session.add(vehicle_info)
                session.commit()
                session.refresh(vehicle_info)

                # 6. Manejar los documentos
                docs = []

                # Función auxiliar para manejar la subida de documentos
                async def handle_document_upload(
                    file: Optional[UploadFile],
                    doc_type: str,
                    side: Optional[str] = None,
                    existing_url: Optional[str] = None
                ) -> Optional[str]:
                    if file:
                        doc_info = await upload_service.save_document_dbtype(
                            file=file,
                            driver_id=driver_info.id,
                            document_type=doc_type,
                            side=side,
                            description=f"{doc_type} {side if side else ''}"
                        )
                        return uploader.get_file_url(doc_info["url"])
                    return existing_url

                # Tarjeta de propiedad
                if driver_documents_data.property_card_front or driver_documents_data.property_card_back:
                    property_front_url = await handle_document_upload(
                        driver_documents_data.property_card_front,
                        "property_card",
                        "front",
                        driver_documents_data.property_card_front_url
                    )
                    property_back_url = await handle_document_upload(
                        driver_documents_data.property_card_back,
                        "property_card",
                        "back",
                        driver_documents_data.property_card_back_url
                    )
                    docs.append(DriverDocuments(
                        driver_info_id=driver_info.id,
                        vehicle_info_id=vehicle_info.id,
                        document_type_id=1,  # 1 = Tarjeta de propiedad
                        document_front_url=property_front_url,
                        document_back_url=property_back_url,
                        expiration_date=None
                    ))

                # Licencia de conducir
                if (driver_documents_data.license_front or driver_documents_data.license_back or
                        driver_documents_data.license_expiration_date):
                    license_front_url = await handle_document_upload(
                        driver_documents_data.license_front,
                        "license",
                        "front",
                        driver_documents_data.license_front_url
                    )
                    license_back_url = await handle_document_upload(
                        driver_documents_data.license_back,
                        "license",
                        "back",
                        driver_documents_data.license_back_url
                    )
                    docs.append(DriverDocuments(
                        driver_info_id=driver_info.id,
                        vehicle_info_id=vehicle_info.id,
                        document_type_id=2,  # 2 = Licencia
                        document_front_url=license_front_url,
                        document_back_url=license_back_url,
                        expiration_date=driver_documents_data.license_expiration_date
                    ))

                # SOAT
                if driver_documents_data.soat or driver_documents_data.soat_expiration_date:
                    soat_url = await handle_document_upload(
                        driver_documents_data.soat,
                        "soat",
                        None,
                        driver_documents_data.soat_url
                    )
                    docs.append(DriverDocuments(
                        driver_info_id=driver_info.id,
                        vehicle_info_id=vehicle_info.id,
                        document_type_id=3,  # 3 = SOAT
                        document_front_url=soat_url,
                        expiration_date=driver_documents_data.soat_expiration_date
                    ))

                # Tecnomecánica
                if (driver_documents_data.vehicle_technical_inspection or
                        driver_documents_data.vehicle_technical_inspection_expiration_date):
                    tech_url = await handle_document_upload(
                        driver_documents_data.vehicle_technical_inspection,
                        "technical_inspections",
                        None,
                        driver_documents_data.vehicle_technical_inspection_url
                    )
                    docs.append(DriverDocuments(
                        driver_info_id=driver_info.id,
                        vehicle_info_id=vehicle_info.id,
                        document_type_id=4,  # 4 = Tecnomecánica
                        document_front_url=tech_url,
                        expiration_date=driver_documents_data.vehicle_technical_inspection_expiration_date
                    ))

                for doc in docs:
                    session.add(doc)
                session.commit()

                # Consultar documentos actualizados desde la base de datos
                property_card_doc = session.exec(
                    select(DriverDocuments).where(
                        DriverDocuments.driver_info_id == driver_info.id,
                        DriverDocuments.document_type_id == 1
                    )
                ).first()

                license_doc = session.exec(
                    select(DriverDocuments).where(
                        DriverDocuments.driver_info_id == driver_info.id,
                        DriverDocuments.document_type_id == 2
                    )
                ).first()

                soat_doc = session.exec(
                    select(DriverDocuments).where(
                        DriverDocuments.driver_info_id == driver_info.id,
                        DriverDocuments.document_type_id == 3
                    )
                ).first()

                vehicle_tech_doc = session.exec(
                    select(DriverDocuments).where(
                        DriverDocuments.driver_info_id == driver_info.id,
                        DriverDocuments.document_type_id == 4
                    )
                ).first()

                session.refresh(user)
                print(
                    f"DEBUG selfie_url del usuario REFRESH: {user.selfie_url}")
                response = DriverFullResponse(
                    user=UserResponse(
                        full_name=user.full_name,
                        country_code=user.country_code,
                        phone_number=user.phone_number,
                        selfie_url=user.selfie_url
                    ),
                    driver_info=DriverInfoResponse(
                        first_name=driver_info.first_name,
                        last_name=driver_info.last_name,
                        birth_date=str(driver_info.birth_date),
                        email=driver_info.email,
                        selfie_url=user.selfie_url
                    ),
                    vehicle_info=VehicleInfoResponse(
                        brand=vehicle_info.brand,
                        model=vehicle_info.model,
                        model_year=vehicle_info.model_year,
                        color=vehicle_info.color,
                        plate=vehicle_info.plate,
                        vehicle_type_id=vehicle_info.vehicle_type_id
                    ),
                    driver_documents=DriverDocumentsResponse(
                        property_card_front_url=property_card_doc.document_front_url if property_card_doc else None,
                        property_card_back_url=property_card_doc.document_back_url if property_card_doc else None,
                        license_front_url=license_doc.document_front_url if license_doc else None,
                        license_back_url=license_doc.document_back_url if license_doc else None,
                        license_expiration_date=str(
                            license_doc.expiration_date) if license_doc and license_doc.expiration_date else None,
                        soat_url=soat_doc.document_front_url if soat_doc else None,
                        soat_expiration_date=str(
                            soat_doc.expiration_date) if soat_doc and soat_doc.expiration_date else None,
                        vehicle_technical_inspection_url=vehicle_tech_doc.document_front_url if vehicle_tech_doc else None,
                        vehicle_technical_inspection_expiration_date=str(
                            vehicle_tech_doc.expiration_date) if vehicle_tech_doc and vehicle_tech_doc.expiration_date else None
                    )
                )

                # Crear transacción de bono y actualizar mount
                bonus_transaction = Transaction(
                    user_id=user.id,
                    income=50000,
                    expense=0,
                    type=TransactionType.BONUS,
                    client_request_id=None
                )
                session.add(bonus_transaction)
                session.commit()
                # Actualizar el mount en VerifyMount
                verify_mount.mount += 50000
                session.add(verify_mount)
                session.commit()

                return response

            except Exception as e:
                session.rollback()
                print(f"Error en create_driver: {str(e)}")
                print(traceback.format_exc())
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error al crear el conductor: {str(e)}"
                )

    def get_driver_detail_service(self, session: Session, driver_id: int):
        """
        Devuelve la información personal, de usuario y del vehículo de un conductor dado su driver_id.
        """
        from app.models.driver_info import DriverInfo
        from app.models.user import User
        from app.models.vehicle_info import VehicleInfo
        from sqlalchemy import select

        driver_info = session.get(DriverInfo, driver_id)
        if not driver_info:
            raise HTTPException(
                status_code=404, detail="DriverInfo no encontrado")

        # Obtener el usuario asociado
        user = session.get(User, driver_info.user_id)
        user_data = {
            "id": user.id,
            "full_name": user.full_name,
            "country_code": user.country_code,
            "phone_number": user.phone_number
        } if user else None

        # Obtener el vehículo asociado
        vehicle_info = session.exec(
            select(VehicleInfo).where(
                VehicleInfo.driver_info_id == driver_info.id)
        ).scalars().first()

        vehicle_data = {
            "brand": vehicle_info.brand,
            "model": vehicle_info.model,
            "model_year": vehicle_info.model_year,
            "color": vehicle_info.color,
            "plate": vehicle_info.plate,
            "vehicle_type_id": vehicle_info.vehicle_type_id
        } if vehicle_info else None

        return {
            "user": user_data,
            "driver_info": {
                "id": driver_info.id,
                "first_name": driver_info.first_name,
                "last_name": driver_info.last_name,
                "email": driver_info.email,
                "selfie_url": driver_info.user.selfie_url if hasattr(driver_info, 'user') and hasattr(driver_info.user, 'selfie_url') else None
            },
            "vehicle_info": vehicle_data
        }
