from sqlmodel import Session, select
from fastapi import HTTPException, status
from app.models.driver import Driver, DriverCreate, DriverUpdate
from app.models.user import User
from app.models.role import Role
import os


class DriverService:
    def __init__(self, session: Session):
        self.session = session

    def create_driver(self, driver_data: DriverCreate) -> Driver:
        driver = Driver.model_validate(driver_data)
        self.session.add(driver)
        self.session.flush()  # Para obtener driver.id antes de commit

        # Obtener el usuario asociado
        user = self.session.get(User, driver.user_id)

        # Asignar el rol DRIVER si no lo tiene aún
        driver_role = self.session.exec(
            select(Role).where(Role.id == "DRIVER")).first()
        if not driver_role:
            raise HTTPException(status_code=500, detail="Rol DRIVER no existe")

        if driver_role not in user.roles:
            user.roles.append(driver_role)
            self.session.add(user)

        self.session.commit()
        self.session.refresh(driver)
        return driver

    def get_all_drivers(self) -> list[Driver]:
        return self.session.exec(
            select(Driver).where(Driver.is_active == True)
        ).all()

    def get_driver_by_id(self, driver_id: int) -> Driver:
        driver = self.session.get(Driver, driver_id)
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
        return driver

    def update_driver(self, driver_id: int, driver_data: DriverUpdate) -> Driver:
        driver = self.get_driver_by_id(driver_id)
        driver_data_dict = driver_data.model_dump(exclude_unset=True)

        for key, value in driver_data_dict.items():
            setattr(driver, key, value)

        self.session.add(driver)
        self.session.commit()
        self.session.refresh(driver)
        return driver

    def soft_delete_driver(self, driver_id: int) -> dict:
        driver = self.get_driver_by_id(driver_id)

        if not driver.is_active:
            raise HTTPException(
                status_code=400, detail="Driver is already inactive")

        driver.is_active = False
        self.session.add(driver)
        self.session.commit()
        return {"message": "Driver deactivated (soft delete) successfully"}

    def update_driver_document(self, driver_id: int, field: str, url: str) -> Driver:
        driver = self.get_driver_by_id(driver_id)
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
        if not hasattr(driver, field):
            raise HTTPException(
                status_code=400, detail=f"El campo '{field}' no existe en Driver")

        # Eliminar archivo anterior si existe
        old_url = getattr(driver, field)
        if old_url:
            # Convierte la URL relativa a ruta absoluta
            old_path = old_url.lstrip("/")
            if os.path.exists(old_path):
                os.remove(old_path)

        # Actualizar con la nueva URL
        setattr(driver, field, url)
        self.session.add(driver)
        self.session.commit()
        self.session.refresh(driver)
        return driver
