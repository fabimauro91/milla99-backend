from fastapi import Request, HTTPException, status, Path


def user_is_owner():
    def dependency(
        user_id: int = Path(...),  # FastAPI inyecta el parámetro de la ruta
        request: Request = None
    ):
        if request.state.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder a este recurso"
            )
    return dependency
