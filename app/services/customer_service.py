from sqlmodel import Session, select
from app.models import Customer, CustomerCreate, CustomerUpdate
from fastapi import HTTPException, status

class CustomerService:
    def __init__(self, session: Session):
        self.session = session

    def create_customer(self, customer_data: CustomerCreate) -> Customer:
        customer = Customer.model_validate(customer_data.model_dump())
        self.session.add(customer)
        self.session.commit()
        self.session.refresh(customer)
        return customer

    def get_customers(self) -> list[Customer]:
        return self.session.exec(select(Customer)).all()

    def get_customer(self, customer_id: int) -> Customer:
        customer = self.session.get(Customer, customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado"
            )
        return customer

    def update_customer(self, customer_id: int, customer_data: CustomerUpdate) -> Customer:
        customer = self.get_customer(customer_id)
        
        # Actualizar los campos
        customer_data_dict = customer_data.model_dump(exclude_unset=True)
        customer.sqlmodel_update(customer_data_dict)
        
        self.session.add(customer)
        self.session.commit()
        self.session.refresh(customer)
        return customer

    def delete_customer(self, customer_id: int) -> dict:
        customer = self.get_customer(customer_id)
        self.session.delete(customer)
        self.session.commit()
        return {"message": "Cliente eliminado correctamente"} 