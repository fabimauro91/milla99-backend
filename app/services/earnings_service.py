# app/services/earnings_service.py
from typing import List, Optional
from decimal import Decimal, ROUND_HALF_UP
from sqlmodel import select, SQLModel, Field, Session
from app.models.client_request import ClientRequest, StatusEnum
from app.models.penality_user import PenalityUser, statusEnum
from app.models.referral_chain import Referral
from app.models.transaction import Transaction
from app.models.project_settings import ProjectSettings
from app.models.user import User
from app.models.driver_savings import DriverSavings
from app.models.company_account import CompanyAccount
from app.core.config import settings
from uuid import UUID
from datetime import datetime
from app.services.transaction_service import TransactionService
from sqlalchemy.orm import Session as SQLAlchemySession
import traceback

# Id especial (o None) para la empresa
COMPANY_ID: int | None = None


def get_config_percentages(session: SQLAlchemySession):
    """
    Devuelve un diccionario con los porcentajes configurados en la tabla project_settings.
    Ahora busca la configuración con ID = 1.
    """
    config = session.query(ProjectSettings).get(
        1)  # Asume que la configuración está en la fila con ID 1
    if not config:
        raise ValueError(
            "No se encontró la configuración del proyecto con ID 1")

    config_dict = {
        "driver_dist": Decimal(config.driver_dist),
        "referral_1": Decimal(config.referral_1),
        "referral_2": Decimal(config.referral_2),
        "referral_3": Decimal(config.referral_3),
        "referral_4": Decimal(config.referral_4),
        "referral_5": Decimal(config.referral_5),
        "driver_saving": Decimal(config.driver_saving),
        "company": Decimal(config.company),
        "bonus": Decimal(config.bonus),
    }
    return config_dict


def _get_referral_chain(session: SQLAlchemySession, user_id: UUID, levels: int) -> List[UUID]:
    """
    Obtiene la cadena de referidos hasta el nivel especificado.
    """
    chain = []
    current_user_id = user_id

    for _ in range(levels):
        referral = session.query(Referral).filter(
            Referral.user_id == current_user_id).first()
        if referral and referral.referred_by_id:
            chain.append(referral.referred_by_id)
            current_user_id = referral.referred_by_id
        else:
            break

    return chain


def distribute_earnings(session: SQLAlchemySession, request: ClientRequest) -> None:
    try:
        if request.status != StatusEnum.PAID:
            return

        fare = Decimal(str(request.fare_assigned or 0))
        if fare <= 0:
            return

        config = get_config_percentages(session)
        driver_saving_pct = config["driver_saving"]
        company_pct = config["company"]
        referral_pcts = [
            config["referral_1"],
            config["referral_2"],
            config["referral_3"],
            config["referral_4"],
            config["referral_5"],
        ]

        transaction_service = TransactionService(session)

        # Calcular el ingreso del conductor (85% del valor del viaje)
        driver_income_pct = Decimal("0.85")  # 85%
        driver_income = (
            fare * driver_income_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        print(
            f"[DEBUG] Creando transacción SERVICE ingreso para conductor: user_id={request.id_driver_assigned}, income={int(driver_income)}")
        transaction_service.create_transaction(
            user_id=request.id_driver_assigned,
            income=int(driver_income),
            type="SERVICE",
            client_request_id=request.id,
            description=f"Ingreso por servicio del viaje {request.id}"
        )

        driver_expense_pct = Decimal("0.10")  # 10%
        driver_expense = (
            fare * driver_expense_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        print(
            f"[DEBUG] Creando transacción COMMISSION egreso para conductor: user_id={request.id_driver_assigned}, expense={int(driver_expense)}")
        transaction_service.create_transaction(
            user_id=request.id_driver_assigned,
            expense=int(driver_expense),
            type="COMMISSION",
            client_request_id=request.id,
            description=f"Comisión por uso de la plataforma para el viaje {request.id}"
        )

        # Calcular el ahorro (1% del valor del viaje)
        driver_saving = (
            fare * driver_saving_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Buscar el registro de ahorro existente
        driver_savings = session.query(DriverSavings).filter(
            DriverSavings.user_id == request.id_driver_assigned
        ).first()

        if driver_savings:
            driver_savings.mount += driver_saving
        else:
            driver_savings = DriverSavings(
                user_id=request.id_driver_assigned,
                mount=driver_saving,
                type="SAVING",
                client_request_id=request.id
            )
            session.add(driver_savings)

        earnings = []

        chain_ids = _get_referral_chain(session, request.id_client, levels=5)

        company_share = (
            fare * company_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        earnings.append(CompanyAccount(
            client_request_id=request.id,
            income=company_share,
            type="SERVICE"
        ))

        company_share = Decimal("0.00")
        for idx, pct in enumerate(referral_pcts):
            if idx < len(chain_ids):
                ref_amount = (fare * pct).quantize(Decimal("0.01"),
                                                   rounding=ROUND_HALF_UP)
                transaction_service.create_transaction(
                    user_id=chain_ids[idx],
                    income=int(ref_amount),
                    type=f"REFERRAL_{idx+1}",
                    client_request_id=request.id
                )
            else:
                company_share += (fare * pct).quantize(Decimal("0.01"),
                                                       rounding=ROUND_HALF_UP)

        if company_share > 0:
            earnings.append(CompanyAccount(
                client_request_id=request.id,
                income=company_share,
                type="ADDITIONAL"
            ))

        if request.penality > 0:
            penality = pay_penality_user(session, request.id_client)

        session.add_all(earnings)
        session.commit()
    except Exception as e:
        raise


def get_referral_earnings_structured(session, user_id: UUID):

    user = session.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()
    if not user:
        return None

    stmt = select(Referral.user_id, Referral.referred_by_id)
    rows = session.execute(stmt).all()
    children_map = {}
    for child_id, parent_id in rows:
        if parent_id is not None:
            children_map.setdefault(parent_id, []).append(child_id)

    levels = 5
    level_users = [[] for _ in range(levels)]
    current_level = children_map.get(user_id, [])
    for lvl in range(levels):
        if not current_level:
            break
        level_users[lvl].extend(current_level)
        next_level = []
        for uid in current_level:
            next_level.extend(children_map.get(uid, []))
        current_level = next_level

    if not any(level_users):
        return {
            "user_id": user.id,
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "levels": [],
            "message": "El usuario no tiene referidos."
        }

    config = get_config_percentages(session)
    referral_pcts = [
        config.get("referral_1", 0),
        config.get("referral_2", 0),
        config.get("referral_3", 0),
        config.get("referral_4", 0),
        config.get("referral_5", 0),
    ]

    user_info_map = {}
    all_user_ids = [uid for level in level_users for uid in level]
    if all_user_ids:
        users = session.execute(
            select(User).where(User.id.in_(all_user_ids))
        ).scalars().all()
        for u in users:
            user_info_map[u.id] = u

    levels_structured = []
    for i, users_in_level in enumerate(level_users):
        if not users_in_level:
            continue
        pct = referral_pcts[i] * 100
        users_list = []
        for uid in users_in_level:
            u = user_info_map.get(uid)
            users_list.append({
                "id": uid,
                "full_name": u.full_name if u else None,
                "phone_number": u.phone_number if u else None
            })
        levels_structured.append({
            "level": i + 1,
            "percentage": pct,
            "users": users_list
        })

    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "levels": levels_structured
    }


def pay_penality_user(session: SQLAlchemySession, request: ClientRequest) -> None:
    """
    Paga una penalidad de usuario y actualiza su estado a PAID.
    """
    try:
        penalties = session.query(PenalityUser).filter(
            PenalityUser.user_id == request.id_client,
            PenalityUser.status == statusEnum.PENDING
        ).all()

        if not penalties:
            return None

        transaction_service = TransactionService(session)

        for penality in penalties:
            if penality.amount <= 0:
                continue

            # Crear transacción de pago de penalidad

            transaction_service.create_transaction(
                user_id=penality.id_driver_assigned,
                income=int(penality.amount),
                type="PENALITY_COMPENSATION",
                client_request_id=request.id,
                description=f"Pago de penalidad por solicitud {request.id}"
            )
            penality.status = statusEnum.PAID
            penality.id_driver_get_money = request.id_driver_assigned
            penality.updated_at = datetime.utcnow()

        transaction_service.create_transaction(
            user_id=request.id_driver_assigned,
            expense=request.penality,
            type="PENALITY_DEDUCTION",
            client_request_id=request.id,
            description=f"Pago de penalidades por solicitud {request.id}"
        )
        session.commit()
        return penality
    except Exception as e:
        session.rollback()
        traceback.print_exc()
        raise Exception(f"Error al pagar penalidades: {str(e)}")
