from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlmodel import Session
from typing import List, Optional
from fastapi.responses import JSONResponse
import json

from app.models.driver import Driver, DriverCreate, DriverDocumentsInput, DriverFullCreate, DriverFullRead
from app.core.db import get_session
from app.models.user import UserRead
from app.services.driver_service import DriverService
from app.models.driver_full_read import DriverFullRead
from app.models.driver_response import DriverFullResponse, UserResponse, DriverInfoResponse, VehicleInfoResponse, DriverDocumentsResponse

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.post("/", response_model=DriverFullResponse, status_code=status.HTTP_201_CREATED)
async def create_driver(
    user: str = Form(...),
    driver_info: str = Form(...),
    vehicle_info: str = Form(...),
    driver_documents: str = Form(...),
    selfie: Optional[UploadFile] = File(None),
    property_card_front: Optional[UploadFile] = File(None),
    property_card_back: Optional[UploadFile] = File(None),
    license_front: Optional[UploadFile] = File(None),
    license_back: Optional[UploadFile] = File(None),
    soat: Optional[UploadFile] = File(None),
    vehicle_technical_inspection: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session)
):
    """
    Crea un nuevo conductor con sus documentos.

    Los datos se pueden enviar de dos formas:
    1. Como JSON en los campos user, driver_info, vehicle_info y driver_documents
    2. Como archivos individuales para cada documento

    Args:
        user: JSON string con los datos del usuario
        driver_info: JSON string con los datos del conductor
        vehicle_info: JSON string con los datos del vehículo
        driver_documents: JSON string con las fechas de vencimiento de los documentos
        selfie: Archivo de la selfie del conductor
        property_card_front: Frente de la tarjeta de propiedad
        property_card_back: Reverso de la tarjeta de propiedad
        license_front: Frente de la licencia de conducir
        license_back: Reverso de la licencia de conducir
        soat: SOAT
        vehicle_technical_inspection: Revisión técnico mecánica
    """
    try:
        user_data = json.loads(user)
        driver_info_data = json.loads(driver_info)
        vehicle_info_data = json.loads(vehicle_info)
        driver_documents_data = json.loads(driver_documents)

        driver_docs = DriverDocumentsInput(
            property_card_front=property_card_front,
            property_card_back=property_card_back,
            license_front=license_front,
            license_back=license_back,
            license_expiration_date=driver_documents_data.get(
                "license_expiration_date"),
            soat=soat,
            soat_expiration_date=driver_documents_data.get(
                "soat_expiration_date"),
            vehicle_technical_inspection=vehicle_technical_inspection,
            vehicle_technical_inspection_expiration_date=driver_documents_data.get(
                "vehicle_technical_inspection_expiration_date"),
            property_card_front_url=driver_documents_data.get(
                "property_card_front_url"),
            property_card_back_url=driver_documents_data.get(
                "property_card_back_url"),
            license_front_url=driver_documents_data.get("license_front_url"),
            license_back_url=driver_documents_data.get("license_back_url"),
            soat_url=driver_documents_data.get("soat_url"),
            vehicle_technical_inspection_url=driver_documents_data.get(
                "vehicle_technical_inspection_url")
        )

        driver_data = DriverFullCreate(
            user=user_data,
            driver_info=driver_info_data,
            vehicle_info=vehicle_info_data,
            driver_documents=driver_docs,
            selfie=selfie
        )

        service = DriverService(session)
        result = await service.create_driver(
            user_data=driver_data.user,
            driver_info_data=driver_data.driver_info,
            vehicle_info_data=driver_data.vehicle_info,
            driver_documents_data=driver_data.driver_documents,
            selfie=driver_data.selfie
        )

        # Construir respuesta personalizada
        return DriverFullResponse(
            user=UserResponse(
                full_name=result.user.full_name,
                country_code=result.user.country_code,
                phone_number=result.user.phone_number
            ),
            driver_info=DriverInfoResponse(
                first_name=result.driver_info.first_name,
                last_name=result.driver_info.last_name,
                birth_date=str(result.driver_info.birth_date),
                email=result.driver_info.email,
                selfie_url=result.driver_info.selfie_url
            ),
            vehicle_info=VehicleInfoResponse(
                brand=result.vehicle_info.brand,
                model=result.vehicle_info.model,
                model_year=result.vehicle_info.model_year,
                color=result.vehicle_info.color,
                plate=result.vehicle_info.plate,
                vehicle_type_id=result.vehicle_info.vehicle_type_id
            ),
            driver_documents=result.driver_documents
        )

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al decodificar JSON: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el conductor: {str(e)}"
        )
