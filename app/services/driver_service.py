from sqlmodel import Session, select
from fastapi import HTTPException, status
from app.models.driver_documents import DriverDocuments, DriverDocumentsCreate
from app.models.user import User, UserCreate, UserRead
from app.models.role import Role
from app.models.driver_info import DriverInfo, DriverInfoCreate
from app.models.vehicle_info import VehicleInfo, VehicleInfoCreate
from app.models.driver import DriverFullRead, Driver
from app.core.db import engine


class DriverService:
    def __init__(self, session: Session):
        self.session = session

    def create_driver(
        self,
        user_data: UserCreate,
        driver_info_data: DriverInfoCreate,
        vehicle_info_data: VehicleInfoCreate,
        driver_documents_data
    ) -> DriverFullRead:
        with Session(engine) as session:
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

            # 3. Crear el DriverInfo
            driver_info = DriverInfo(
                **driver_info_data.dict(),
                user_id=user.id
            )
            session.add(driver_info)
            session.commit()
            session.refresh(driver_info)

            # 3.5 Crear el Driver (registro principal en la tabla driver)
            driver = Driver(
                user_id=user.id,
                driver_info_id=driver_info.id
            )
            session.add(driver)
            session.commit()
            session.refresh(driver)

            # 4. Crear el VehicleInfo
            vehicle_info = VehicleInfo(
                **vehicle_info_data.dict(),
                driver_info_id=driver_info.id
            )
            session.add(vehicle_info)
            session.commit()
            session.refresh(vehicle_info)

            # 5. Crear múltiples DriverDocuments
            docs = []
            docs_data = driver_documents_data

            # Tarjeta de propiedad
            if docs_data.property_card_front_url or docs_data.property_card_back_url:
                docs.append(DriverDocuments(
                    driver_info_id=driver_info.id,
                    vehicle_info_id=vehicle_info.id,
                    document_type_id=1,  # 1 = Tarjeta de propiedad
                    document_front_url=docs_data.property_card_front_url,
                    document_back_url=docs_data.property_card_back_url,
                    expiration_date=None
                ))

            # Licencia de conducir
            if docs_data.license_front_url or docs_data.license_back_url or docs_data.license_expiration_date:
                docs.append(DriverDocuments(
                    driver_info_id=driver_info.id,
                    vehicle_info_id=vehicle_info.id,
                    document_type_id=2,  # 2 = Licencia
                    document_front_url=docs_data.license_front_url,
                    document_back_url=docs_data.license_back_url,
                    expiration_date=docs_data.license_expiration_date
                ))

            # SOAT
            if docs_data.soat_url or docs_data.soat_expiration_date:
                docs.append(DriverDocuments(
                    driver_info_id=driver_info.id,
                    vehicle_info_id=vehicle_info.id,
                    document_type_id=3,  # 3 = SOAT
                    document_front_url=docs_data.soat_url,
                    expiration_date=docs_data.soat_expiration_date
                ))

            # Tecnomecánica
            if docs_data.vehicle_technical_inspection_url or docs_data.vehicle_technical_inspection_expiration_date:
                docs.append(DriverDocuments(
                    driver_info_id=driver_info.id,
                    vehicle_info_id=vehicle_info.id,
                    document_type_id=4,  # 4 = Tecnomecánica
                    document_front_url=docs_data.vehicle_technical_inspection_url,
                    expiration_date=docs_data.vehicle_technical_inspection_expiration_date
                ))

            for doc in docs:
                session.add(doc)
            session.commit()

            # Convertir a DriverFullRead
            return DriverFullRead(
                user=UserRead.model_validate(user),
                driver_info=driver_info,
                vehicle_info=vehicle_info,
                driver_documents=docs
            )
