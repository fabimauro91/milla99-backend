from fastapi import APIRouter, File, UploadFile, HTTPException, status, Form, Request, Depends
from app.services.upload_service import parse_document_type, upload_service, DocumentType
from app.core.db import get_session
from sqlmodel import Session, select
from typing import Optional
from app.models.driver_info import DriverInfo
from app.models.driver_documents import DriverDocuments
from app.models.document_type import DocumentType as DocumentTypeDB
from datetime import datetime

router = APIRouter(prefix="/upload", tags=["uploads"])


@router.post("/driver-document")
async def upload_driver_document(
    request: Request,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    side: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    """
    Sube un documento del conductor y actualiza el campo correspondiente en la base de datos.

    Args:
        file: Archivo a subir
        document_type: Tipo de documento (debe ser uno de los DocumentType definidos)
        side: Variante del documento (opcional)
        description: Descripción opcional del documento
    """
    # Validar que document_type exista en la tabla documenttype
    doc_type_obj = session.exec(
        select(DocumentTypeDB).where(DocumentTypeDB.name == document_type)
    ).first()
    if not doc_type_obj:
        raise HTTPException(
            status_code=400, detail="Tipo de documento no válido")

    # Validar side según el tipo (puedes personalizar esto)
    allowed_sides = {
        "license": ["front", "back"],
        "property_card": ["front", "back"],
        "soat": [None],
        "technical_inspections": [None]
    }
    if allowed_sides.get(document_type) and side not in allowed_sides[document_type]:
        raise HTTPException(
            status_code=400, detail="Variante no permitida para este tipo de documento")

    # Obtener el ID del usuario autenticado
    user_id = request.state.user_id

    # Obtener el driver asociado al usuario
    driver_info = session.exec(select(DriverInfo).where(
        DriverInfo.user_id == user_id)).first()
    if not driver_info:
        raise HTTPException(status_code=404, detail="DriverInfo not found")

    # Buscar o crear DriverDocuments por driver_info_id y document_type_id
    driver_documents = session.exec(
        select(DriverDocuments).where(
            DriverDocuments.driver_info_id == driver_info.id,
            DriverDocuments.document_type_id == doc_type_obj.id
        )
    ).first()

    if not driver_documents:
        driver_documents = DriverDocuments(
            driver_info_id=driver_info.id,
            document_type_id=doc_type_obj.id
        )
        session.add(driver_documents)
        session.commit()
        session.refresh(driver_documents)

    # Guardar el documento
    document_info = await upload_service.save_document_dbtype(
        file=file,
        user_id=user_id,
        document_type=document_type,
        side=side,
        description=description
    )

    # Lógica especial para documentos únicos (SOAT, técnico-mecánica, antecedentes)
    if document_type in ("soat", "technical_inspections", "criminal_record"):
        driver_documents.document_front_url = document_info["url"]
        session.add(driver_documents)
        session.commit()
        session.refresh(driver_documents)
        return {"message": f"{document_type.replace('_', ' ').title()} subido correctamente", "document": document_info}

    # Lógica especial para licencia (front/back)
    if document_type == "license":
        if side not in ("front", "back"):
            raise HTTPException(
                status_code=400, detail="Debes especificar si es 'front' o 'back' para la licencia")
        if side == "front":
            driver_documents.document_front_url = document_info["url"]
        else:
            driver_documents.document_back_url = document_info["url"]
        session.add(driver_documents)
        session.commit()
        session.refresh(driver_documents)
        return {"message": f"{document_type.replace('_', ' ').title()} subido correctamente", "document": document_info}

    # Actualizar el campo correspondiente en el modelo para otros documentos
    field_name = f"{doc_type_obj.name}_url"
    if hasattr(driver_documents, field_name):
        setattr(driver_documents, field_name, document_info["url"])
        session.add(driver_documents)
        session.commit()
        session.refresh(driver_documents)
    else:
        # Si el campo no existe en DriverDocuments, intentar en DriverInfo
        driver_info = session.exec(
            select(DriverInfo).where(DriverInfo.id == driver_info.id)
        ).first()
        if driver_info and hasattr(driver_info, field_name):
            setattr(driver_info, field_name, document_info["url"])
            session.add(driver_info)
            session.commit()
            session.refresh(driver_info)
        else:
            # Si no se encontró el campo en ningún modelo, eliminar el archivo
            upload_service.delete_document(document_info["url"])
            raise HTTPException(
                status_code=400,
                detail=f"No se encontró un campo correspondiente para el tipo de documento {doc_type_obj}"
            )

    return {
        "message": f"Documento {doc_type_obj.name} actualizado exitosamente",
        "document": document_info
    }


@router.delete("/driver-document/{document_type}")
async def delete_driver_document(
    request: Request,
    document_type: str,
    session: Session = Depends(get_session)
):
    """
    Elimina un documento del conductor y actualiza la base de datos.

    Args:
        document_type: Tipo de documento a eliminar
    """
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de documento inválido. Debe ser uno de: {', '.join(DocumentType.__members__.keys())}"
        )

    # Obtener el ID del usuario autenticado
    user_id = request.state.user_id

    # Obtener el driver asociado al usuario
    driver_info = session.exec(select(DriverInfo).where(
        DriverInfo.user_id == user_id)).first()
    if not driver_info:
        raise HTTPException(status_code=404, detail="DriverInfo not found")

    # Buscar el documento en DriverDocuments
    driver_documents = session.exec(
        select(DriverDocuments).where(
            DriverDocuments.driver_info_id == driver_info.id)
    ).first()

    field_name = f"{doc_type.value}_url"
    url_to_delete = None

    if driver_documents and hasattr(driver_documents, field_name):
        url_to_delete = getattr(driver_documents, field_name)
        setattr(driver_documents, field_name, None)
        session.add(driver_documents)
    else:
        # Si no está en DriverDocuments, buscar en DriverInfo
        driver_info = session.exec(
            select(DriverInfo).where(DriverInfo.id == driver_info.id)
        ).first()
        if driver_info and hasattr(driver_info, field_name):
            url_to_delete = getattr(driver_info, field_name)
            setattr(driver_info, field_name, None)
            session.add(driver_info)

    if url_to_delete:
        # Eliminar el archivo físico
        upload_service.delete_document(url_to_delete)
        session.commit()
        return {"message": f"Documento {doc_type} eliminado exitosamente"}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró el documento {doc_type} para eliminar"
        )


@router.post("/driver-info-selfie")
async def upload_driver_info_selfie(
    request: Request,
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """
    Sube o actualiza la selfie del conductor.
    Si el usuario ya tiene un conductor, actualiza la selfie existente.
    Si no tiene conductor, guarda la selfie para su posterior uso.
    """
    # Obtener el ID del usuario autenticado
    user_id = request.state.user_id

    # Verificar si el usuario tiene un conductor
    existing_driver = session.exec(
        select(DriverInfo).where(DriverInfo.user_id == user_id)
    ).first()

    # Guardar la selfie usando el servicio de uploads
    document_info = await upload_service.save_document(
        file=file,
        user_id=user_id,
        document_type=DocumentType.DRIVER_SELFIE,
        description="Selfie del conductor"
    )

    # Si el usuario ya tiene un conductor, actualizar la selfie en DriverInfo
    if existing_driver:
        driver_info = session.exec(
            select(DriverInfo).where(DriverInfo.id ==
                                     existing_driver.id)
        ).first()

        if driver_info:
            # Si hay una selfie anterior, eliminarla
            if driver_info.selfie_url:
                upload_service.delete_document(driver_info.selfie_url)

            # Actualizar con la nueva selfie
            driver_info.selfie_url = document_info["url"]
            session.add(driver_info)
            session.commit()
            session.refresh(driver_info)

            return {
                "message": "Selfie actualizada exitosamente",
                "document": document_info
            }

    return {
        "message": "Selfie guardada exitosamente",
        "document": document_info
    }
