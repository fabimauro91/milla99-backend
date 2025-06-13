from fastapi.testclient import TestClient
from app.main import app
from app.models.client_request import StatusEnum, ClientRequest
from app.models.transaction import Transaction, TransactionType
from app.models.verify_mount import VerifyMount
from app.models.driver_savings import DriverSavings
from app.models.company_account import CompanyAccount
from decimal import Decimal
from sqlmodel import Session, select
from app.core.db import engine
from app.services.earnings_service import distribute_earnings
from uuid import UUID
from datetime import date
import json
import io
from fastapi import status as http_status
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.test.test_drivers import create_and_approve_driver

client = TestClient(app)


def test_cash_payment_transaction_flow():
    """
    Prueba el flujo completo de pago en efectivo y verifica todas las transacciones:
    1. Verifica que el conductor recibe el 85% del valor del viaje
    2. Verifica que se descuenta el 10% de comisión
    3. Verifica que se guarda el 1% en ahorros
    4. Verifica que la empresa recibe su comisión
    """
    # 1. Crear y autenticar cliente
    phone_number = "3004444456"
    country_code = "+57"

    # Autenticar cliente
    send_resp = client.post(f"/auth/verify/{country_code}/{phone_number}/send")
    assert send_resp.status_code == 201
    code = send_resp.json()["message"].split()[-1]

    verify_resp = client.post(
        f"/auth/verify/{country_code}/{phone_number}/code",
        json={"code": code}
    )
    assert verify_resp.status_code == 200
    token = verify_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Crear solicitud con pago en efectivo
    request_data = {
        "fare_offered": 20000,
        "pickup_description": "Suba Bogotá",
        "destination_description": "Santa Rosita Engativa",
        "pickup_lat": 4.718136,
        "pickup_lng": -74.073170,
        "destination_lat": 4.702468,
        "destination_lng": -74.109776,
        "type_service_id": 1,  # Car
        "payment_method_id": 1  # Cash
    }
    create_resp = client.post(
        "/client-request/", json=request_data, headers=headers)
    assert create_resp.status_code == 201
    client_request_id = create_resp.json()["id"]

    # 3. Crear y aprobar conductor
    driver_phone = "3010000005"
    driver_country_code = "+57"
    driver_token, driver_id = create_and_approve_driver(
        client, driver_phone, driver_country_code)
    driver_headers = {"Authorization": f"Bearer {driver_token}"}

    # 4. Asignar conductor y completar viaje
    fare_assigned = 25000  # Valor final del viaje

    # Asignar conductor
    assign_data = {
        "id_client_request": client_request_id,
        "id_driver": driver_id,
        "fare_assigned": fare_assigned
    }
    assign_resp = client.patch(
        "/client-request/updateDriverAssigned",
        json=assign_data,
        headers=headers
    )
    assert assign_resp.status_code == 200

    # Completar flujo del viaje
    status_flow = ["ON_THE_WAY", "ARRIVED", "TRAVELLING", "FINISHED", "PAID"]
    for status in status_flow:
        status_data = {
            "id_client_request": client_request_id,
            "status": status
        }
        status_resp = client.patch(
            "/client-request/updateStatusByDriver",
            json=status_data,
            headers=driver_headers
        )
        assert status_resp.status_code == 200

    # 5. Verificar todas las transacciones
    with Session(engine) as session:
        # Verificar transacción de ingreso del conductor (85%)
        driver_income = session.exec(
            select(Transaction).where(
                Transaction.client_request_id == UUID(str(client_request_id)),
                Transaction.user_id == UUID(str(driver_id)),
                Transaction.type == TransactionType.SERVICE,
                Transaction.income != None
            )
        ).first()
        assert driver_income is not None
        expected_income = int(fare_assigned * Decimal('0.85'))
        assert driver_income.income == expected_income

        # Verificar transacción de comisión del conductor (10%)
        driver_commission = session.exec(
            select(Transaction).where(
                Transaction.client_request_id == UUID(str(client_request_id)),
                Transaction.user_id == UUID(str(driver_id)),
                Transaction.type == TransactionType.COMMISSION,
                Transaction.expense != None
            )
        ).first()
        assert driver_commission is not None
        expected_commission = int(fare_assigned * Decimal('0.10'))
        assert driver_commission.expense == expected_commission

        # Verificar ahorros del conductor (1%)
        driver_savings = session.exec(
            select(DriverSavings).where(
                DriverSavings.user_id == UUID(str(driver_id))
            )
        ).first()
        assert driver_savings is not None
        expected_savings = int(fare_assigned * Decimal('0.01'))
        assert driver_savings.mount == expected_savings

        # Verificar comisión de la empresa (4%)
        company_account = session.exec(
            select(CompanyAccount).where(
                CompanyAccount.client_request_id == UUID(
                    str(client_request_id)),
                CompanyAccount.type == "SERVICE"
            )
        ).first()
        assert company_account is not None
        expected_company_commission = int(fare_assigned * Decimal('0.04'))
        assert company_account.income == expected_company_commission


def test_multiple_trips_transaction_accumulation():
    """
    Prueba que las transacciones se acumulan correctamente cuando un conductor
    completa múltiples viajes:
    1. Verifica que los ingresos se acumulan
    2. Verifica que las comisiones se acumulan
    3. Verifica que los ahorros se acumulan
    4. Verifica que la comisión de la empresa se acumula
    """
    # 1. Crear y autenticar cliente
    phone_number = "3004444456"
    country_code = "+57"

    # Autenticar cliente
    send_resp = client.post(f"/auth/verify/{country_code}/{phone_number}/send")
    assert send_resp.status_code == 201
    code = send_resp.json()["message"].split()[-1]

    verify_resp = client.post(
        f"/auth/verify/{country_code}/{phone_number}/code",
        json={"code": code}
    )
    assert verify_resp.status_code == 200
    token = verify_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Crear y aprobar conductor
    driver_phone = "3010000005"
    driver_country_code = "+57"
    driver_token, driver_id = create_and_approve_driver(
        client, driver_phone, driver_country_code)
    driver_headers = {"Authorization": f"Bearer {driver_token}"}

    # 3. Completar múltiples viajes
    fares = [25000, 30000, 35000]  # Diferentes valores de viajes
    total_expected_income = 0
    total_expected_commission = 0
    total_expected_savings = 0
    total_expected_company_commission = 0

    for fare in fares:
        # Crear solicitud
        request_data = {
            "fare_offered": fare - 5000,  # Cliente ofrece menos
            "pickup_description": "Suba Bogotá",
            "destination_description": "Santa Rosita Engativa",
            "pickup_lat": 4.718136,
            "pickup_lng": -74.073170,
            "destination_lat": 4.702468,
            "destination_lng": -74.109776,
            "type_service_id": 1,
            "payment_method_id": 1
        }
        create_resp = client.post(
            "/client-request/", json=request_data, headers=headers)
        assert create_resp.status_code == 201
        client_request_id = create_resp.json()["id"]

        # Asignar conductor
        assign_data = {
            "id_client_request": client_request_id,
            "id_driver": driver_id,
            "fare_assigned": fare
        }
        assign_resp = client.patch(
            "/client-request/updateDriverAssigned",
            json=assign_data,
            headers=headers
        )
        assert assign_resp.status_code == 200

        # Completar viaje
        status_flow = ["ON_THE_WAY", "ARRIVED",
                       "TRAVELLING", "FINISHED", "PAID"]
        for status in status_flow:
            status_data = {
                "id_client_request": client_request_id,
                "status": status
            }
            status_resp = client.patch(
                "/client-request/updateStatusByDriver",
                json=status_data,
                headers=driver_headers
            )
            assert status_resp.status_code == 200

        # Acumular totales esperados
        total_expected_income += int(fare * Decimal('0.85'))
        total_expected_commission += int(fare * Decimal('0.10'))
        total_expected_savings += int(fare * Decimal('0.01'))
        total_expected_company_commission += int(fare * Decimal('0.04'))

    # 4. Verificar acumulación de transacciones
    with Session(engine) as session:
        # Verificar ingreso total del conductor
        total_driver_income = session.exec(
            select(func.sum(Transaction.income)).where(
                Transaction.user_id == UUID(str(driver_id)),
                Transaction.type == TransactionType.SERVICE,
                Transaction.income != None
            )
        ).first()
        assert total_driver_income == total_expected_income

        # Verificar comisión total del conductor
        total_driver_commission = session.exec(
            select(func.sum(Transaction.expense)).where(
                Transaction.user_id == UUID(str(driver_id)),
                Transaction.type == TransactionType.SERVICE,
                Transaction.expense != None
            )
        ).first()
        assert total_driver_commission == total_expected_commission

        # Verificar ahorros totales
        driver_savings = session.exec(
            select(DriverSavings).where(
                DriverSavings.user_id == UUID(str(driver_id))
            )
        ).first()
        assert driver_savings is not None
        assert driver_savings.mount == total_expected_savings

        # Verificar comisión total de la empresa
        total_company_commission = session.exec(
            select(func.sum(CompanyAccount.income)).where(
                CompanyAccount.type == "SERVICE"
            )
        ).first()
        assert total_company_commission == total_expected_company_commission


def test_transaction_rollback_on_error():
    """
    Prueba que las transacciones se revierten correctamente si hay un error
    durante el proceso de pago:
    1. Simula un error durante el pago
    2. Verifica que no se crean transacciones parciales
    3. Verifica que los balances no se modifican
    """
    # TODO: Implementar test de rollback
    pass


def test_transaction_with_referrals():
    """
    Prueba el flujo de transacciones con referidos:
    1. Verifica que los referidos reciben sus comisiones
    2. Verifica que la empresa recibe el resto de la comisión
    3. Verifica que los porcentajes son correctos por nivel
    """
    # TODO: Implementar test de referidos
    pass
