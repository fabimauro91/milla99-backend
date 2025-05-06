from sqlmodel import Session, select
from app.models import Transaction, TransactionCreate, Customer
from fastapi import HTTPException, status

class TransactionService:
    def __init__(self, session: Session):
        self.session = session

    def create_transaction(self, transaction_data: TransactionCreate) -> Transaction:
        # Verificar que el cliente existe
        customer = self.session.get(Customer, transaction_data.customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado"
            )
        
        transaction = Transaction.model_validate(transaction_data.model_dump())
        self.session.add(transaction)
        self.session.commit()
        self.session.refresh(transaction)
        return transaction

    def get_transactions(self, skip: int = 0, limit: int = 10) -> list[Transaction]:
        query = select(Transaction).offset(skip).limit(limit)
        return self.session.exec(query).all()

    def get_transaction(self, transaction_id: int) -> Transaction:
        transaction = self.session.get(Transaction, transaction_id)
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transacción no encontrada"
            )
        return transaction 