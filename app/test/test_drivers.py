from fastapi import status


def test_create_driver(client):
    response = client.post(
        "/drivers/",
        json={
            "user_id": 1,
            "first_name": "Carlos",
            "last_name": "Gómez",
            "birth_date": "1990-01-01",
            "email": "carlos@example.com",
            "vehicle_type": "motorcycle",
            "brand": "Yamaha",
            "model": "YZF-R3",
            "color": "Blue",
            "license_plate": "XYZ123"
        }
    )
    print("[CREATE] Response:", response.json())
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["first_name"] == "Carlos"


def test_get_all_drivers(client):
    response = client.get("/drivers/")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


def test_get_driver_by_id(client):
    # Create a driver first
    response = client.post(
        "/drivers/",
        json={
            "user_id": 2,
            "first_name": "Ana",
            "last_name": "Martínez",
            "birth_date": "1988-05-12"
        }
    )
    driver_id = response.json()["id"]

    # get driver by id
    get_response = client.get(f"/drivers/{driver_id}")
    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.json()["first_name"] == "Ana"


def test_update_driver(client):
    response = client.post(
        "/drivers/",
        json={
            "user_id": 3,
            "first_name": "Luis",
            "last_name": "Ramírez"
        }
    )
    driver_id = response.json()["id"]

    patch_response = client.patch(
        f"/drivers/{driver_id}", json={"last_name": "Rodríguez"})
    assert patch_response.status_code == status.HTTP_200_OK
    assert patch_response.json()["last_name"] == "Rodríguez"


def test_soft_delete_driver(client):
    response = client.post(
        "/drivers/",
        json={
            "user_id": 4,
            "first_name": "Mario",
            "last_name": "López"
        }
    )
    driver_id = response.json()["id"]

    # active driver
    patch_response = client.patch(
        f"/drivers/{driver_id}", json={"is_active": True})
    assert patch_response.status_code == 200

    delete_response = client.delete(f"/drivers/{driver_id}")
    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json() == {
        "message": "Driver deactivated (soft delete) successfully"}

    # verify that the driver is inactive
    get_response = client.get(f"/drivers/{driver_id}")
    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.json()["is_active"] is False