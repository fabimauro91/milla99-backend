from fastapi import FastAPI
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, create_engine, SQLModel
from .config import settings

engine = create_engine(settings.DATABASE_URL)

def create_all_tables(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)] 