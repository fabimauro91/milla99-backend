from fastapi.testclient import TestClient
from app.main import app
import traceback

client = TestClient(app)


def test_create_and_limit_bank_accounts():
    # Crear usuario (cliente)
    phone_number = "3005555555"
    country_code = "+57"
    full_name = "Cliente Bank Test"

    # Enviar código de verificación
    send_resp = client.post(f"/auth/verify/{country_code}/{phone_number}/send")
    assert send_resp.status_code == 201
    code = send_resp.json()["message"].split()[-1]

    # Verificar el código y obtener el token
    verify_resp = client.post(
        f"/auth/verify/{country_code}/{phone_number}/code",
        json={"code": code}
    )
    assert verify_resp.status_code == 200
    token = verify_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Datos de cuentas bancarias
    accounts = [
        {"bank_id": 1, "account_type": "savings", "account_holder_name": "John Doe",
            "type_identification": "CC", "account_number": "1234567890", "identification_number": "111111111"},
        {"bank_id": 2, "account_type": "checking", "account_holder_name": "John Doe",
            "type_identification": "CC", "account_number": "9876543210", "identification_number": "222222222"},
        {"bank_id": 3, "account_type": "savings", "account_holder_name": "John Doe",
            "type_identification": "CC", "account_number": "5555555555", "identification_number": "333333333"},
        {"bank_id": 4, "account_type": "savings", "account_holder_name": "John Doe",
            "type_identification": "CC", "account_number": "4444444444", "identification_number": "444444444"},
    ]

    # Crear las primeras 3 cuentas (deben ser exitosas)
    for i in range(3):
        resp = client.post("/bank-accounts/",
                           json=accounts[i], headers=headers)
        assert resp.status_code == 201, f"Error creando cuenta {i+1}: {resp.text}"
        assert "id" in resp.json()

    # Intentar crear la cuarta cuenta (debe fallar)
    resp = client.post("/bank-accounts/", json=accounts[3], headers=headers)
    assert resp.status_code == 400
    assert "Solo puede tener hasta 3 cuentas bancarias" in resp.json()[
        "detail"]


def test_bank_account_crud_flow():
    # Crear usuario (cliente)
    phone_number = "3010000011"
    country_code = "+57"
    full_name = "Cliente Bank Test CRUD"

    # Crear usuario antes de enviar código de verificación
    user_data = {
        "full_name": full_name,
        "country_code": country_code,
        "phone_number": phone_number
    }
    create_user_resp = client.post("/users/", json=user_data)
    assert create_user_resp.status_code == 201

    # Enviar código de verificación
    try:
        send_resp = client.post(
            f"/auth/verify/{country_code}/{phone_number}/send")
        assert send_resp.status_code == 201
    except Exception as e:
        traceback.print_exc()
        raise
    code = send_resp.json()["message"].split()[-1]

    # Verificar el código y obtener el token
    try:
        verify_resp = client.post(
            f"/auth/verify/{country_code}/{phone_number}/code",
            json={"code": code}
        )
        assert verify_resp.status_code == 200
    except Exception as e:
        traceback.print_exc()
        raise
    token = verify_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Crear cuenta bancaria
    create_data = {
        "bank_id": 1,
        "account_type": "savings",
        "account_holder_name": "John Doe",
        "type_identification": "CC",
        "account_number": "1234567890",
        "identification_number": "111111111"
    }
    create_resp = client.post(
        "/bank-accounts/", json=create_data, headers=headers)
    assert create_resp.status_code == 201, create_resp.text
    account = create_resp.json()
    account_id = account["id"]
    assert account["account_holder_name"] == "John Doe"

    # Listar cuentas bancarias
    list_resp = client.get("/bank-accounts/me", headers=headers)
    assert list_resp.status_code == 200
    accounts = list_resp.json()
    print(
        f"\n[DEBUG] List response before delete (is_active=True): {accounts}")
    assert any(acc["id"] == account_id for acc in accounts)

    # Actualizar la cuenta bancaria
    update_data = {"account_holder_name": "Jane Doe"}
    patch_resp = client.patch(
        f"/bank-accounts/{account_id}", json=update_data, headers=headers)
    assert patch_resp.status_code == 200
    updated_account = patch_resp.json()
    assert updated_account["account_holder_name"] == "Jane Doe"

    # Eliminar la cuenta bancaria
    delete_resp = client.delete(
        f"/bank-accounts/{account_id}", headers=headers)
    assert delete_resp.status_code == 200 or delete_resp.status_code == 204

    # Verificar que la cuenta está desactivada (is_active = False)
    list_resp_after = client.get("/bank-accounts/me", headers=headers)
    assert list_resp_after.status_code == 200
    accounts_after = list_resp_after.json()
    print(
        f"\n[DEBUG] List response after delete (is_active=False): {accounts_after}")

    deleted_account = next(
        (acc for acc in accounts_after if acc["id"] == account_id), None)
    print(f"\n[DEBUG] Deleted account data: {deleted_account}")
    assert deleted_account is not None, "La cuenta debería seguir existiendo pero desactivada"
    assert deleted_account[
        "is_active"] is False, "La cuenta debería estar desactivada (is_active = False)"
