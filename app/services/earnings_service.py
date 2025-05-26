# app/services/earnings_service.py
from typing import List, Optional 
from decimal import Decimal, ROUND_HALF_UP
from sqlmodel import select
from app.models.client_request import ClientRequest, StatusEnum
from app.models.referral_chain import Referral
from app.models.transaction import Transaction
from app.models.project_settings import ProjectSettings
from app.models.user import User
from app.models.driver_savings import DriverSavings
from app.models.company_account import CompanyAccount
from app.core.config import settings

# Id especial (o None) para la empresa
COMPANY_ID: int | None = None

def _get_referral_chain(session, user_id: int, levels: int = 3) -> list[int]:
    chain = []
    current_id = user_id

    for _ in range(levels):
        stmt = select(Referral).where(Referral.user_id == current_id)
        result = session.execute(stmt)
        rel = result.scalar_one_or_none()
        if not rel or not rel.referred_by_id:
            break
        chain.append(rel.referred_by_id)
        current_id = rel.referred_by_id

    return chain


def get_config_percentages(session):
    """
    Devuelve un diccionario con los porcentajes configurados en la tabla de configuración.
    """
    config = session.query(ProjectSettings).all()  # Ajusta el nombre de tu modelo
    config_dict = {row.description: Decimal(str(row.value)) for row in config}
    return config_dict



def distribute_earnings(session, request: ClientRequest) -> None:
    if request.status != StatusEnum.FINISHED:
        return

    fare = Decimal(str(request.fare_assigned or 0))
    if fare <= 0:
        return

    # Obtener los porcentajes desde la tabla de configuración
    # Sin valores por defecto - lanzará error si falta algún valor
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

    # Obtener la cadena de referidos
    chain_ids = _get_referral_chain(session, request.id_client, levels=5)

    earnings = []

    # Ganancia del conductor
    driver_saving = (fare * driver_saving_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    earnings.append(DriverSavings(
        user_id=request.id_driver_assigned,
        income=driver_saving, 
        expense= 0,   
        type="SERVICE",
        client_request_id=request.id
    ))

    # Ganancias de referidos
    company_share = (fare * company_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    earnings.append(CompanyAccount(
        client_request_id=request.id,
        income=company_share,
        type="SERVICE"
    ))
    company_share = 0
    for idx, pct in enumerate(referral_pcts):
        if idx < len(chain_ids):
            ref_amount = (fare * pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            earnings.append(Transaction(
                client_request_id=request.id,
                user_id=chain_ids[idx],
                income=ref_amount,
                expense= 0,
                type=f"REFERRAL_{idx+1}"
            ))
        else:
            # Si no hay referido, ese porcentaje se suma a la compañía
            company_share += (fare * pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Ganancia de la compañía
    if company_share > 0:
        earnings.append(CompanyAccount(
            client_request_id=request.id,
            income=company_share,
            type="ADDITIONAL"
        ))

    session.add_all(earnings)
    session.commit()


def get_referral_earnings_structured(session, user_id: int):

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