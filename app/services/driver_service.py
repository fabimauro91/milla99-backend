from sqlmodel import Session, select
from fastapi import HTTPException, status
from app.models.driver import Driver, DriverCreate, DriverUpdate


class DriverService:
    def __init__(self, session: Session):
        self.session = session

    def create_driver(self, driver_data: DriverCreate) -> Driver:
        driver = Driver.model_validate(driver_data)
        self.session.add(driver)
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
