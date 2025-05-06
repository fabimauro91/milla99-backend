from app.models import Customer, CustomerCreate, CustomerUpdate
from app.core.db import SessionDep
from app.services.customer_service import CustomerService
from fastapi import APIRouter, status

router = APIRouter()

@router.post("/customers", response_model=Customer, status_code=status.HTTP_201_CREATED, tags=["customers"])
async def create_customer(customer_data: CustomerCreate, session: SessionDep):
    service = CustomerService(session)
    return service.create_customer(customer_data)

@router.get("/customers", response_model=list[Customer], tags=["customers"])
async def list_customers(session: SessionDep):
    service = CustomerService(session)
    return service.get_customers()

@router.get("/customers/{customer_id}", response_model=Customer, tags=["customers"])
async def get_customer(customer_id: int, session: SessionDep):
    service = CustomerService(session)
    return service.get_customer(customer_id)

@router.delete("/customers/{customer_id}", status_code=status.HTTP_200_OK, tags=["customers"])
async def delete_customer(customer_id: int, session: SessionDep):
    service = CustomerService(session)
    return service.delete_customer(customer_id)

@router.patch("/customers/{customer_id}", response_model=Customer, status_code=status.HTTP_200_OK, tags=["customers"])
async def update_customer(customer_id: int, customer_data: CustomerUpdate, session: SessionDep):
    service = CustomerService(session)
    return service.update_customer(customer_id, customer_data)









