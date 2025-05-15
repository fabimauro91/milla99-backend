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


class DriverService:
    def __init__(self, session: Session):
        self.session = session

    async def create_driver(
        self,
        user_data: UserCreate,
        driver_info_data: DriverInfoCreate,
        vehicle_info_data: VehicleInfoCreate,
        driver_documents_data: DriverDocumentsInput,
        selfie: Optional[UploadFile] = None
    ) -> DriverFullResponse:
        with Session(engine) as session:
            # Buscar usuario por teléfono
            existing_user = session.exec(
                select(User).where(User.phone_number == user_data.phone_number)
            ).first()

            if existing_user:
                # Buscar si ya tiene un driver asociado
                existing_driver = session.exec(
                    select(DriverInfo)
                    .where(DriverInfo.user_id == existing_user.id)
                ).first()

                if existing_driver:
                    # Buscar el vehicle_info asociado a ese driver_info y de tipo carro
                    driver_info = session.exec(
                        select(DriverInfo).where(DriverInfo.id ==
                                                 existing_driver.id)
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
                            detail="Ya existe un conductor de tipo carro para este usuario."
                        )

            # 1. Crear el Usuario
            user = User(**user_data.dict())
            session.add(user)
            session.commit()
            session.refresh(user)

            # 2. Asignar el rol DRIVER
            driver_role = session.exec(
                select(Role).where(Role.id == "DRIVER")).first()
            if not driver_role:
                raise HTTPException(
                    status_code=500, detail="Rol DRIVER no existe")

            user.roles.append(driver_role)
            session.add(user)
            session.commit()
            session.refresh(user)

            # 4. Crear el DriverInfo (sin selfie_url aún)
            driver_info = DriverInfo(
                **driver_info_data.dict(exclude={'selfie_url'}),
                user_id=user.id,
                selfie_url=None
            )
            session.add(driver_info)
            session.commit()
            session.refresh(driver_info)

            # 5. Manejar la selfie si se proporciona (usando driver_info.id)
            if selfie:
                document_info = await upload_service.save_document_dbtype(
                    file=selfie,
                    driver_id=driver_info.id,
                    document_type="selfie",
                    description="Selfie del conductor"
                )
                driver_info.selfie_url = uploader.get_file_url(
                    document_info["url"])
                session.add(driver_info)
                session.commit()
            elif driver_info_data.selfie_url:
                driver_info.selfie_url = driver_info_data.selfie_url
                session.add(driver_info)
                session.commit()

            # 6. Crear el VehicleInfo
            vehicle_info = VehicleInfo(
                **vehicle_info_data.dict(),
                driver_info_id=driver_info.id
            )
            session.add(vehicle_info)
            session.commit()
            session.refresh(vehicle_info)

            # 7. Manejar los documentos
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

            response = DriverFullResponse(
                user=UserResponse(
                    full_name=user.full_name,
                    country_code=user.country_code,
                    phone_number=user.phone_number
                ),
                driver_info=DriverInfoResponse(
                    first_name=driver_info.first_name,
                    last_name=driver_info.last_name,
                    birth_date=str(driver_info.birth_date),
                    email=driver_info.email,
                    selfie_url=driver_info.selfie_url
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
            return response
