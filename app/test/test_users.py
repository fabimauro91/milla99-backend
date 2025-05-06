from fastapi import status

# test for create user


def test_create_user(client):
    response = client.post(
        "/users/",
        json={
            "full_name": "Daniel Vargas",
            "country_code": "+57",
            "phone_number": "3100000000",
            "role": "user",
            "user_type": "driver"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["full_name"] == "Daniel Vargas"
    assert data["role"] == "user"
    assert data["user_type"] == "driver"
    assert data["is_active"] is False
    assert data["is_verified"] is False

# test for get all users


def test_get_users(client):
    response = client.get("/users/")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

# test for get user by id


def test_get_user_by_id(client):
    response = client.post(
        "/users/",
        json={
            "full_name": "Laura Milla",
            "country_code": "+57",
            "phone_number": "3200000000",
            "role": "user",
            "user_type": "delivery"
        }
    )
    user_id = response.json()["id"]

    get_response = client.get(f"/users/{user_id}")
    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.json()["full_name"] == "Laura Milla"
    assert get_response.json()["user_type"] == "delivery"


def test_update_user(client):
    response = client.post(
        "/users/",
        json={
            "full_name": "Carlos",
            "country_code": "+57",
            "phone_number": "3001111111",
            "role": "user",
            "user_type": "driver"
        }
    )
    user_id = response.json()["id"]

    update_response = client.patch(
        f"/users/{user_id}",
        json={"full_name": "Carlos Editado"}
    )
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["full_name"] == "Carlos Editado"


def test_delete_user(client):
    response = client.post(
        "/users/",
        json={
            "full_name": "Para Borrar",
            "country_code": "+57",
            "phone_number": "3009999999",
            "role": "user",
            "user_type": "driver"
        }
    )
    user_id = response.json()["id"]

    delete_response = client.delete(f"/users/{user_id}")
    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json() == {"message": "User deleted successfully"}


def test_cannot_create_duplicate_user(client):
    user_data = {
        "full_name": "Daniel Vargas",
        "country_code": "+57",
        "phone_number": "3100000000",
        "role": "user",
        "user_type": "driver"
    }

    response_1 = client.post("/users/", json=user_data)
    assert response_1.status_code == status.HTTP_201_CREATED

    response_2 = client.post("/users/", json=user_data)
    assert response_2.status_code == status.HTTP_409_CONFLICT
    assert response_2.json()[
        "detail"] == "User with this phone number already exists."


def test_invalid_colombian_mobile(client):
    response = client.post(
        "/users/",
        json={
            "full_name": "Invalido",
            "country_code": "+57",
            "phone_number": "333333333",  # ❌ inválido
            "role": "user",
            "user_type": "driver"
        }
    )
    print("\nResponse JSON:", response.json())
    assert response.status_code == 422
    assert "Colombian mobile numbers must start with 3." in response.text
