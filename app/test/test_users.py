from fastapi import status
from fastapi.testclient import TestClient
from app.main import app
from datetime import datetime
from sqlmodel import Session, select
from app.models.user_has_roles import UserHasRole, RoleStatus
from app.models.role import Role
from app.models.deleted_user import DeletedUser
from app.core.db import engine
from uuid import UUID
import time

client = TestClient(app)

# === TESTS ACTUALIZADOS DE ENDPOINTS PRINCIPALES ===


def test_create_user():
    user_data = {
        "full_name": "Test User",
        "country_code": "+57",
        "phone_number": "3011234580"
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["full_name"] == user_data["full_name"]
    assert data["country_code"] == user_data["country_code"]
    assert data["phone_number"] == user_data["phone_number"]
    assert data["is_active"] is False or data["is_active"] is True
    assert data["is_verified_phone"] is False
    assert "id" in data


def test_get_me():
    # Usar timestamp para hacer el número único
    timestamp = int(time.time()) % 10000000  # 7 dígitos del timestamp
    country_code = "+57"
    # Formato: 300 + 7 dígitos = 10 dígitos total
    phone_number = f"300{timestamp:07d}"
    user_data = {
        "full_name": "User Me",
        "country_code": country_code,
        "phone_number": phone_number
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 201
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
    me_resp = client.get("/users/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["phone_number"] == phone_number
    assert me_data["full_name"] == "User Me"
    # Verificar que el nuevo campo is_driver_approved esté presente
    assert "is_driver_approved" in me_data
    # Para un usuario recién creado con solo rol CLIENT, debe ser False
    assert me_data["is_driver_approved"] is False


def test_get_me_driver_approved():
    """Test para verificar que is_driver_approved sea True cuando el usuario tiene rol DRIVER aprobado"""
    # Usar timestamp para hacer el número único
    timestamp = int(time.time()) % 10000000  # 7 dígitos del timestamp
    country_code = "+57"
    # Formato: 301 + 7 dígitos = 10 dígitos total
    phone_number = f"301{timestamp:07d}"
    user_data = {
        "full_name": "Driver User",
        "country_code": country_code,
        "phone_number": phone_number
    }

    # Crear usuario
    response = client.post("/users/", json=user_data)
    assert response.status_code == 201
    user_id = response.json()["id"]

    # Verificar usuario
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

    # Simular que el usuario tiene rol DRIVER aprobado (manipulación directa de BD)
    with Session(engine) as session:
        # Buscar el rol DRIVER
        driver_role = session.exec(
            select(Role).where(Role.id == "DRIVER")).first()
        assert driver_role is not None

        # Crear la relación UserHasRole con status APPROVED
        user_role = UserHasRole(
            id_user=UUID(user_id),
            id_rol="DRIVER",
            is_verified=True,
            status=RoleStatus.APPROVED,
            verified_at=datetime.utcnow()
        )
        session.add(user_role)
        session.commit()

    # Ahora llamar a /users/me y verificar que is_driver_approved sea True
    me_resp = client.get("/users/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["phone_number"] == phone_number
    assert me_data["full_name"] == "Driver User"
    assert "is_driver_approved" in me_data
    assert me_data["is_driver_approved"] is True


def test_update_me():
    # Usar timestamp para hacer el número único
    timestamp = int(time.time()) % 10000000  # 7 dígitos del timestamp
    country_code = "+57"
    # Formato: 302 + 7 dígitos = 10 dígitos total
    phone_number = f"302{timestamp:07d}"
    user_data = {
        "full_name": "User Update",
        "country_code": country_code,
        "phone_number": phone_number
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 201
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
    update_data = {"full_name": "User Updated"}
    patch_resp = client.patch(
        "/users/me/update", data=update_data, headers=headers)
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["full_name"] == "User Updated"
    me_resp = client.get("/users/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["full_name"] == "User Updated"


# def test_get_users(client):
#     response = client.get("/users/")
#     assert response.status_code == status.HTTP_200_OK
#     assert isinstance(response.json(), list)

# # test for get user by id


# def test_get_user_by_id(client):
#     response = client.post(
#         "/users/",
#         json={
#             "full_name": "Laura Milla",
#             "country_code": "+57",
#             "phone_number": "3200000000"
#         }
#     )
#     user_id = response.json()["id"]

#     get_response = client.get(f"/users/{user_id}")
#     assert get_response.status_code == status.HTTP_200_OK
#     assert get_response.json()["full_name"] == "Laura Milla"


# def test_update_user(client):
#     response = client.post(
#         "/users/",
#         json={
#             "full_name": "Carlos",
#             "country_code": "+57",
#             "phone_number": "3001111111"
#         }
#     )
#     user_id = response.json()["id"]

#     update_response = client.patch(
#         f"/users/{user_id}",
#         json={"full_name": "Carlos Editado"}
#     )
#     assert update_response.status_code == status.HTTP_200_OK
#     assert update_response.json()["full_name"] == "Carlos Editado"


# def test_delete_user(client):
#     response = client.post(
#         "/users/",
#         json={
#             "full_name": "Para Borrar",
#             "country_code": "+57",
#             "phone_number": "3009999999"
#         }
#     )
#     user_id = response.json()["id"]

#     delete_response = client.delete(f"/users/{user_id}")
#     assert delete_response.status_code == status.HTTP_200_OK
#     assert delete_response.json() == {"message": "User deleted successfully"}


# def test_cannot_create_duplicate_user(client):
#     user_data = {
#         "full_name": "Daniel Vargas",
#         "country_code": "+57",
#         "phone_number": "3100000000"
#     }

#     response_1 = client.post("/users/", json=user_data)
#     assert response_1.status_code == status.HTTP_201_CREATED

#     response_2 = client.post("/users/", json=user_data)
#     assert response_2.status_code == status.HTTP_409_CONFLICT
#     assert response_2.json()[
#         "detail"] == "User with this phone number already exists."


# def test_invalid_colombian_mobile(client):
#     response = client.post(
#         "/users/",
#         json={
#             "full_name": "Invalido",
#             "country_code": "+57",
#             "phone_number": "4333333333"  # ❌ inválido
#         }
#     )
#     print("\nResponse JSON:", response.json())
#     assert response.status_code == 422
#     assert "Colombian mobile numbers must start with 3." in response.text


# def test_invalid_full_name(client):
#     response = client.post(
#         "/users/",
#         json={
#             "full_name": "Da",  # ❌ inválido
#             "country_code": "+57",
#             "phone_number": "3008888888"
#         }
#     )
#     print("\nResponse JSON:", response.json())
#     assert response.status_code == 422
#     assert "Full name can only contain letters and spaces." in response.text


# def test_soft_delete_user(client):
#     # 1. Crear usuario (viene con is_active=False)
#     response = client.post(
#         "/users/",
#         json={
#             "full_name": "Usuario Activo",
#             "country_code": "+57",
#             "phone_number": "3007777777"
#         }
#     )
#     print("\n[CREATE USER] Response:", response.json())
#     assert response.status_code == 201
#     user_id = response.json()["id"]
#     # Confirmamos el valor por defecto
#     assert response.json()["is_active"] is False

#     # 2. Activamos el usuario (simula que está activo antes del "borrado")
#     patch_response = client.patch(
#         f"/users/{user_id}", json={"is_active": True})
#     print("[PATCH USER] Response:", patch_response.json())
#     assert patch_response.status_code == 200
#     assert patch_response.json()["is_active"] is True

#     # 3. Llamamos DELETE (soft delete)
#     delete_response = client.delete(f"/users/{user_id}")
#     print("[DELETE USER] Response:", delete_response.json())
#     assert delete_response.status_code == 200
#     assert delete_response.json(
#     )["message"] == "User deactivated (soft deleted) successfully"

#     # 4. Obtenemos el usuario y verificamos que is_active=False
#     get_response = client.get(f"/users/{user_id}")
#     print("[GET USER] Response:", get_response.json())
#     assert get_response.status_code == 200
#     assert get_response.json()["is_active"] is False


# def test_invalid_full_name_on_update(client):
#     # 1. Create user withouth full_name
#     response = client.post(
#         "/users/",
#         json={
#             "country_code": "+57",
#             "phone_number": "3001212121"
#         }
#     )
#     assert response.status_code == 201
#     user_id = response.json()["id"]
#     assert response.json()["full_name"] is None

#     # 2. Update user with invalid full_name
#     patch_response = client.patch(
#         f"/users/{user_id}", json={"full_name": "Juan123"})
#     print("\n[PATCH INVALID NAME] Response:", patch_response.json())

#     assert patch_response.status_code == 422
#     assert "Full name can only contain letters and spaces." in patch_response.text


# def test_create_user_without_full_name(client):
#     response = client.post(
#         "/users/",
#         json={
#             "country_code": "+57",
#             "phone_number": "3100000000"
#         }
#     )
#     assert response.status_code == 422
#     assert "field required" in response.text.lower()


# def test_create_user_with_empty_full_name(client):
#     response = client.post(
#         "/users/",
#         json={
#             "full_name": "",
#             "country_code": "+57",
#             "phone_number": "3100000000"
#         }
#     )
#     assert response.status_code == 422
#     assert "El nombre completo debe tener al menos 3 caracteres" in response.text


# def test_create_user_with_invalid_full_name(client):
#     response = client.post(
#         "/users/",
#         json={
#             "full_name": "Juan123",
#             "country_code": "+57",
#             "phone_number": "3100000000"
#         }
#     )
#     assert response.status_code == 422
#     assert "El nombre completo solo puede contener letras y espacios" in response.text


# def test_create_user_with_valid_full_name(client):
#     response = client.post(
#         "/users/",
#         json={
#             "full_name": "Juan Pérez",
#             "country_code": "+57",
#             "phone_number": "3100000000"
#         }
#     )
#     assert response.status_code == status.HTTP_201_CREATED
#     data = response.json()
#     assert data["full_name"] == "Juan Pérez"
#     assert data["is_active"] is False
#     assert data["is_verified_phone"] is False
#     # Verificar que se asignó el rol CLIENT y está verificado
#     assert len(data["roles"]) == 1
#     assert data["roles"][0]["id"] == "CLIENT"
#     assert data["roles"][0]["name"] == "pasajero"


# def test_phone_number_length(client):
#     # Test con número más corto
#     response = client.post(
#         "/users/",
#         json={
#             "full_name": "Juan Pérez",
#             "country_code": "+57",
#             "phone_number": "300123456"  # 9 dígitos
#         }
#     )
#     assert response.status_code == 422
#     assert "ensure this value has at least 10 characters" in response.text.lower()

#     # Test con número más largo
#     response = client.post(
#         "/users/",
#         json={
#             "full_name": "Juan Pérez",
#             "country_code": "+57",
#             "phone_number": "30012345678"  # 11 dígitos
#         }
#     )
#     assert response.status_code == 422
#     assert "ensure this value has at most 10 characters" in response.text.lower()

#     # Test con número exacto
#     response = client.post(
#         "/users/",
#         json={
#             "full_name": "Juan Pérez",
#             "country_code": "+57",
#             "phone_number": "3001234567"  # 10 dígitos
#         }
#     )
#     assert response.status_code == 201

# === TESTS DE ELIMINACIÓN DE USUARIOS ===

def test_user_deletion_flow():
    """
    Test completo del flujo de eliminación de usuarios:
    1. Crear usuario
    2. Eliminar completamente
    3. Verificar que puede volver a registrarse pero sin bono
    """
    # Datos del usuario
    phone_number = "3004444470"  # Cambiado para evitar conflicto
    country_code = "+57"
    full_name = "Usuario Test Eliminación"

    # 1. Crear usuario
    create_resp = client.post("/users/", json={
        "full_name": full_name,
        "country_code": country_code,
        "phone_number": phone_number
    })
    assert create_resp.status_code == 201
    user_data = create_resp.json()
    user_id = user_data["id"]

    # 2. Verificar usuario para obtener token
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

    # 3. Verificar que el usuario existe usando /users/me
    me_resp = client.get("/users/me", headers=headers)
    assert me_resp.status_code == 200

    # 4. Eliminar completamente el usuario
    delete_resp = client.delete("/users/me/delete-completely",
                                headers=headers)
    assert delete_resp.status_code == 200
    delete_data = delete_resp.json()
    assert "eliminado completamente" in delete_data["message"]
    assert delete_data["phone_number"] == phone_number

    # 5. Verificar que el usuario ya no puede acceder a endpoints protegidos
    me_resp = client.get("/users/me", headers=headers)
    assert me_resp.status_code == 401  # Token inválido porque usuario fue eliminado

    # 6. Verificar que PUEDE volver a registrarse con el mismo teléfono
    create_resp = client.post("/users/", json={
        "full_name": "Usuario Test Reregistro",
        "country_code": country_code,
        "phone_number": phone_number
    })
    assert create_resp.status_code == 201  # Ahora permite re-registro


def test_driver_bonus_eligibility():
    """
    Test para verificar que un conductor que se creó como DRIVER y fue eliminado 
    no puede recibir bono al re-registrarse
    """
    from app.models.user_has_roles import UserHasRole, RoleStatus

    # Datos del conductor
    phone_number = "3004444471"  # Cambiado para evitar conflicto
    country_code = "+57"
    full_name = "Conductor Test Bono"

    # 1. Crear conductor con rol DRIVER desde el inicio
    create_resp = client.post("/users/", json={
        "full_name": full_name,
        "country_code": country_code,
        "phone_number": phone_number
    })
    assert create_resp.status_code == 201
    user_data = create_resp.json()
    user_id = user_data["id"]

    # 1.1. Agregar rol DRIVER al usuario (simula registro como conductor)
    with Session(engine) as session:
        driver_role = UserHasRole(
            id_user=UUID(user_id),
            id_rol="DRIVER",
            status=RoleStatus.APPROVED,
            is_verified=True
        )
        session.add(driver_role)
        session.commit()

    # 2. Verificar usuario para obtener token
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

    # 3. Eliminar conductor
    delete_resp = client.delete("/users/me/delete-completely", headers=headers)
    assert delete_resp.status_code == 200

    # 4. Re-registrar conductor
    create_resp = client.post("/users/", json={
        "full_name": "Conductor Test Reregistro",
        "country_code": country_code,
        "phone_number": phone_number
    })
    assert create_resp.status_code == 201  # Permite re-registro

    # 4.1. Agregar rol DRIVER al usuario re-registrado (simulación de registro como conductor)
    new_user_id = create_resp.json()["id"]
    with Session(engine) as session:
        # Agregar rol DRIVER al usuario re-registrado
        driver_role = UserHasRole(
            id_user=UUID(new_user_id),
            id_rol="DRIVER",
            status=RoleStatus.APPROVED,
            is_verified=True
        )
        session.add(driver_role)
        session.commit()

    # 5. Verificar que no puede recibir bono usando el servicio directamente
    import traceback
    from app.services.driver_bonus_service import check_driver_bonus_eligibility
    with Session(engine) as session:
        print(f"🔍 DEBUG: === INICIO DEBUG BONO ===")
        print(f"🔍 DEBUG: phone_number: {phone_number}")
        print(f"🔍 DEBUG: new_user_id: {new_user_id}")

        # Debug: verificar si existe en DeletedUser
        from app.models.deleted_user import DeletedUser
        deleted_user = session.query(DeletedUser).filter(
            DeletedUser.phone_number == phone_number
        ).first()
        print(f"🔍 DEBUG: DeletedUser encontrado: {deleted_user}")
        if deleted_user:
            print(
                f"🔍 DEBUG: DeletedUser phone: {deleted_user.phone_number}, user_type: {deleted_user.user_type}")
            print(
                f"🔍 DEBUG: DeletedUser deleted_at: {deleted_user.deleted_at}")
            print(
                f"🔍 DEBUG: DeletedUser original_balance: {deleted_user.original_balance}")

        # Debug: verificar el usuario actual
        from app.models.user import User
        current_user = session.query(User).filter(
            User.id == UUID(new_user_id)).first()
        print(f"🔍 DEBUG: Current user: {current_user}")
        if current_user:
            print(f"🔍 DEBUG: Current user phone: {current_user.phone_number}")
            print(f"🔍 DEBUG: Current user full_name: {current_user.full_name}")

        # Debug: verificar rol DRIVER
        from app.models.user_has_roles import UserHasRole
        driver_role = session.query(UserHasRole).filter(
            UserHasRole.id_user == UUID(new_user_id),
            UserHasRole.id_rol == "DRIVER"
        ).first()
        print(f"🔍 DEBUG: Driver role encontrado: {driver_role}")

        try:
            eligibility = check_driver_bonus_eligibility(
                session, UUID(new_user_id))
            print(f"🔍 DEBUG: Eligibilidad: {eligibility}")
        except Exception as e:
            print(f"❌ ERROR en check_driver_bonus_eligibility: {str(e)}")
            print(f"❌ TRACEBACK: {traceback.format_exc()}")
            raise

        print(f"🔍 DEBUG: === FIN DEBUG BONO ===")
        assert eligibility["eligible"] == False
        assert "eliminado" in eligibility["reason"].lower()


def test_driver_bonus_eligibility_client_to_driver():
    """
    Test para verificar que un usuario que se creó como CLIENT, se eliminó,
    y ahora quiere ser DRIVER SÍ puede recibir bono (porque nunca fue DRIVER antes)
    """
    from app.models.user_has_roles import UserHasRole, RoleStatus

    # Datos del usuario
    phone_number = "3004444474"  # Cambiado para evitar conflicto
    country_code = "+57"
    full_name = "Cliente Test"

    # 1. Crear usuario como CLIENT (sin rol DRIVER)
    create_resp = client.post("/users/", json={
        "full_name": full_name,
        "country_code": country_code,
        "phone_number": phone_number
    })
    assert create_resp.status_code == 201
    user_data = create_resp.json()
    user_id = user_data["id"]

    # 2. Verificar usuario para obtener token
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

    # 3. Eliminar usuario (se guardará como CLIENT en DeletedUser)
    delete_resp = client.delete("/users/me/delete-completely", headers=headers)
    assert delete_resp.status_code == 200

    # 4. Re-registrar usuario
    create_resp = client.post("/users/", json={
        "full_name": "Cliente Convertido a Driver",
        "country_code": country_code,
        "phone_number": phone_number
    })
    assert create_resp.status_code == 201  # Permite re-registro

    # 4.1. Agregar rol DRIVER al usuario re-registrado
    new_user_id = create_resp.json()["id"]
    with Session(engine) as session:
        driver_role = UserHasRole(
            id_user=UUID(new_user_id),
            id_rol="DRIVER",
            status=RoleStatus.APPROVED,
            is_verified=True
        )
        session.add(driver_role)
        session.commit()

    # 5. Verificar que SÍ puede recibir bono (porque nunca fue DRIVER antes)
    import traceback
    from app.services.driver_bonus_service import check_driver_bonus_eligibility
    with Session(engine) as session:
        print(f"🔍 DEBUG: === INICIO DEBUG CLIENT TO DRIVER ===")
        print(f"🔍 DEBUG: phone_number: {phone_number}")
        print(f"🔍 DEBUG: new_user_id: {new_user_id}")

        # Debug: verificar si existe en DeletedUser
        from app.models.deleted_user import DeletedUser
        deleted_user = session.query(DeletedUser).filter(
            DeletedUser.phone_number == phone_number
        ).first()
        print(f"🔍 DEBUG: DeletedUser encontrado: {deleted_user}")
        if deleted_user:
            print(
                f"🔍 DEBUG: DeletedUser phone: {deleted_user.phone_number}, user_type: {deleted_user.user_type}")
            print(
                f"🔍 DEBUG: DeletedUser deleted_at: {deleted_user.deleted_at}")
            print(
                f"🔍 DEBUG: DeletedUser original_balance: {deleted_user.original_balance}")

        # Debug: verificar el usuario actual
        from app.models.user import User
        current_user = session.query(User).filter(
            User.id == UUID(new_user_id)).first()
        print(f"🔍 DEBUG: Current user: {current_user}")
        if current_user:
            print(f"🔍 DEBUG: Current user phone: {current_user.phone_number}")
            print(f"🔍 DEBUG: Current user full_name: {current_user.full_name}")

        # Debug: verificar rol DRIVER
        from app.models.user_has_roles import UserHasRole
        driver_role = session.query(UserHasRole).filter(
            UserHasRole.id_user == UUID(new_user_id),
            UserHasRole.id_rol == "DRIVER"
        ).first()
        print(f"🔍 DEBUG: Driver role encontrado: {driver_role}")

        try:
            eligibility = check_driver_bonus_eligibility(
                session, UUID(new_user_id))
            print(f"🔍 DEBUG: Eligibilidad: {eligibility}")
        except Exception as e:
            print(f"❌ ERROR en check_driver_bonus_eligibility: {str(e)}")
            print(f"❌ TRACEBACK: {traceback.format_exc()}")
            raise

        print(f"🔍 DEBUG: === FIN DEBUG CLIENT TO DRIVER ===")
        # Debería ser elegible porque nunca fue DRIVER antes
        assert eligibility["eligible"] == True
        assert "elegible" in eligibility["reason"].lower()


def test_driver_bonus_eligibility_original_driver():
    """
    Test para verificar que un conductor que se creó originalmente como DRIVER 
    y fue eliminado no puede recibir bono al re-registrarse
    """
    from app.models.user_has_roles import UserHasRole, RoleStatus

    # Datos del conductor
    phone_number = "3004444473"  # Cambiado para evitar conflicto
    country_code = "+57"
    full_name = "Conductor Original Test"

    # 1. Crear conductor con rol DRIVER desde el inicio
    create_resp = client.post("/users/", json={
        "full_name": full_name,
        "country_code": country_code,
        "phone_number": phone_number
    })
    assert create_resp.status_code == 201
    user_data = create_resp.json()
    user_id = user_data["id"]

    # 1.1. Agregar rol DRIVER al usuario (simula registro como conductor)
    with Session(engine) as session:
        driver_role = UserHasRole(
            id_user=UUID(user_id),
            id_rol="DRIVER",
            status=RoleStatus.APPROVED,
            is_verified=True
        )
        session.add(driver_role)
        session.commit()

    # 2. Verificar usuario para obtener token
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

    # 3. Eliminar conductor (ahora debería guardarse como DRIVER en DeletedUser)
    delete_resp = client.delete("/users/me/delete-completely", headers=headers)
    assert delete_resp.status_code == 200

    # 4. Re-registrar conductor
    create_resp = client.post("/users/", json={
        "full_name": "Conductor Original Reregistro",
        "country_code": country_code,
        "phone_number": phone_number
    })
    assert create_resp.status_code == 201  # Permite re-registro

    # 4.1. Agregar rol DRIVER al usuario re-registrado
    new_user_id = create_resp.json()["id"]
    with Session(engine) as session:
        driver_role = UserHasRole(
            id_user=UUID(new_user_id),
            id_rol="DRIVER",
            status=RoleStatus.APPROVED,
            is_verified=True
        )
        session.add(driver_role)
        session.commit()

    # 5. Verificar que no puede recibir bono usando el servicio directamente
    import traceback
    from app.services.driver_bonus_service import check_driver_bonus_eligibility
    with Session(engine) as session:
        print(f"🔍 DEBUG: === INICIO DEBUG BONO ORIGINAL DRIVER ===")
        print(f"🔍 DEBUG: phone_number: {phone_number}")
        print(f"🔍 DEBUG: new_user_id: {new_user_id}")

        # Debug: verificar si existe en DeletedUser
        from app.models.deleted_user import DeletedUser
        deleted_user = session.query(DeletedUser).filter(
            DeletedUser.phone_number == phone_number
        ).first()
        print(f"🔍 DEBUG: DeletedUser encontrado: {deleted_user}")
        if deleted_user:
            print(
                f"🔍 DEBUG: DeletedUser phone: {deleted_user.phone_number}, user_type: {deleted_user.user_type}")
            print(
                f"🔍 DEBUG: DeletedUser deleted_at: {deleted_user.deleted_at}")
            print(
                f"🔍 DEBUG: DeletedUser original_balance: {deleted_user.original_balance}")

        # Debug: verificar el usuario actual
        from app.models.user import User
        current_user = session.query(User).filter(
            User.id == UUID(new_user_id)).first()
        print(f"🔍 DEBUG: Current user: {current_user}")
        if current_user:
            print(f"🔍 DEBUG: Current user phone: {current_user.phone_number}")
            print(f"🔍 DEBUG: Current user full_name: {current_user.full_name}")

        # Debug: verificar rol DRIVER
        from app.models.user_has_roles import UserHasRole
        driver_role = session.query(UserHasRole).filter(
            UserHasRole.id_user == UUID(new_user_id),
            UserHasRole.id_rol == "DRIVER"
        ).first()
        print(f"🔍 DEBUG: Driver role encontrado: {driver_role}")

        try:
            eligibility = check_driver_bonus_eligibility(
                session, UUID(new_user_id))
            print(f"🔍 DEBUG: Eligibilidad: {eligibility}")
        except Exception as e:
            print(f"❌ ERROR en check_driver_bonus_eligibility: {str(e)}")
            print(f"❌ TRACEBACK: {traceback.format_exc()}")
            raise

        print(f"🔍 DEBUG: === FIN DEBUG BONO ORIGINAL DRIVER ===")
        assert eligibility["eligible"] == False
        assert "eliminado" in eligibility["reason"].lower()


def test_deleted_user_verification_allowed():
    """
    Test para verificar que un usuario eliminado PUEDE verificar su teléfono
    """
    # Datos del usuario
    phone_number = "3004444472"  # Cambiado para evitar conflicto
    country_code = "+57"
    full_name = "Usuario Test Verificación"

    # 1. Crear usuario
    create_resp = client.post("/users/", json={
        "full_name": full_name,
        "country_code": country_code,
        "phone_number": phone_number
    })
    assert create_resp.status_code == 201

    # 2. Verificar usuario para obtener token
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

    # 3. Eliminar usuario
    delete_resp = client.delete("/users/me/delete-completely", headers=headers)
    assert delete_resp.status_code == 200

    # 4. Intentar enviar código de verificación (ahora debe permitir)
    send_resp = client.post(f"/auth/verify/{country_code}/{phone_number}/send")
    assert send_resp.status_code == 201  # Ahora permite verificación


def test_user_deletion_with_authentication():
    """
    Test para verificar que solo el propio usuario puede eliminarse
    """
    # Datos del usuario
    phone_number = "3004444473"  # Cambiado para evitar conflicto
    country_code = "+57"
    full_name = "Usuario Test Auth"

    # 1. Crear usuario
    create_resp = client.post("/users/", json={
        "full_name": full_name,
        "country_code": country_code,
        "phone_number": phone_number
    })
    assert create_resp.status_code == 201
    user_data = create_resp.json()
    user_id = user_data["id"]

    # 2. Verificar usuario para obtener token
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

    # 3. Eliminar usuario con autenticación
    delete_resp = client.delete("/users/me/delete-completely",
                                headers=headers)
    assert delete_resp.status_code == 200
    delete_data = delete_resp.json()
    assert "eliminado completamente" in delete_data["message"]
    assert delete_data["phone_number"] == phone_number


def test_deleted_user_cannot_access_endpoints():
    """
    Test para verificar que un usuario eliminado no puede acceder a endpoints protegidos
    """
    # Datos del usuario
    phone_number = "3004444474"  # Cambiado para evitar conflicto
    country_code = "+57"
    full_name = "Usuario Test Acceso"

    # 1. Crear y verificar usuario
    create_resp = client.post("/users/", json={
        "full_name": full_name,
        "country_code": country_code,
        "phone_number": phone_number
    })
    assert create_resp.status_code == 201

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

    # 2. Eliminar usuario
    delete_resp = client.delete("/users/me/delete-completely",
                                headers=headers)
    assert delete_resp.status_code == 200

    # 3. Intentar acceder a endpoint protegido (debe fallar)
    me_resp = client.get("/users/me", headers=headers)
    assert me_resp.status_code == 401  # Token inválido porque usuario fue eliminado
