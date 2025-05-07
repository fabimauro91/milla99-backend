from fastapi import APIRouter, File, UploadFile, HTTPException, status, Form
from app.services.upload_service import save_uploaded_file, UploadCategory

router = APIRouter(prefix="/upload", tags=["uploads"])


@router.post("/")
def upload_file(file: UploadFile = File(...), category: UploadCategory = Form(...)):
    try:
        url = save_uploaded_file(file, category)
        return {"message": "Upload successful", "url": url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
