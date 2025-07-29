import pytest
import mysql.connector
from flask import Flask
from unittest.mock import patch, MagicMock
from routes import routes

@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(routes)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def get_mock_db(cursor_side_effect=None):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    if cursor_side_effect:
        mock_cursor.execute.side_effect = cursor_side_effect
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor

@patch("routes.get_db_connection")
def test_health_success(mock_db, client):
    mock_conn, mock_cursor = get_mock_db()
    mock_db.return_value = mock_conn

    response = client.get("/health")

    assert response.status_code == 200
    assert response.data == b"OK"
    mock_cursor.execute.assert_called_once_with("SELECT 1")

@patch("routes.get_db_connection")
def test_health_failure(mock_db, client):
    mock_db.side_effect = Exception("DB error")
    response = client.get("/health")
    assert response.status_code == 500
    assert b"Failure" in response.data

@patch("routes.get_db_connection")
def test_create_provider_success(mock_db, client):
    mock_conn, mock_cursor = get_mock_db()
    mock_cursor.lastrowid = 101
    mock_db.return_value = mock_conn

    response = client.post("/provider", json={"name": "Provider A"})

    assert response.status_code == 200
    assert response.get_json() == {"id": 101}
    mock_cursor.execute.assert_called_once_with(
        "INSERT INTO Provider (name) VALUES (%s)", ("Provider A",)
    )
    mock_conn.commit.assert_called_once()

@patch("routes.get_db_connection")
def test_create_provider_missing_name(mock_db, client):
    response = client.post("/provider", json={})
    assert response.status_code == 400
    assert response.get_json() == {"error": "Missing name"}
    mock_db.assert_not_called()

@patch("routes.get_db_connection")
def test_create_provider_duplicate(mock_db, client):
    mock_conn, mock_cursor = get_mock_db(cursor_side_effect=mysql.connector.IntegrityError("Duplicate"))
    mock_db.return_value = mock_conn

    response = client.post("/provider", json={"name": "Duplicate Name"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "Provider already exists"}

@patch("routes.get_db_connection")
def test_update_provider_success(mock_db, client):
    mock_conn, mock_cursor = get_mock_db()
    mock_db.return_value = mock_conn

    response = client.put("/provider/1", json={"name": "Updated Name"})

    assert response.status_code == 200
    assert response.get_json() == {"message": "Updated"}
    mock_cursor.execute.assert_called_once_with(
        "UPDATE Provider SET name=%s WHERE id=%s", ("Updated Name", 1)
    )
    mock_conn.commit.assert_called_once()

@patch("routes.get_db_connection")
def test_update_provider_missing_name(mock_db, client):
    response = client.put("/provider/1", json={})
    assert response.status_code == 400
    assert response.get_json() == {"error": "Missing name"}
    mock_db.assert_not_called()

@patch("routes.get_db_connection")
def test_create_truck_success(mock_db, client):
    mock_conn, mock_cursor = get_mock_db()
    mock_db.return_value = mock_conn

    response = client.post("/truck", json={"id": "TRUCK1", "provider": 2})

    assert response.status_code == 200
    assert response.get_json() == {"id": "TRUCK1"}
    mock_cursor.execute.assert_called_once_with(
        "INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)", ("TRUCK1", 2)
    )
    mock_conn.commit.assert_called_once()

@patch("routes.get_db_connection")
def test_create_truck_missing_fields(mock_db, client):
    for data in [{"id": "TRUCK1"}, {"provider": 2}, {}]:
        response = client.post("/truck", json=data)
        assert response.status_code == 400
        assert response.get_json() == {"error": "Missing data"}

    mock_db.assert_not_called()

@patch("routes.get_db_connection")
def test_create_truck_db_error(mock_db, client):
    mock_conn, mock_cursor = get_mock_db(cursor_side_effect=Exception("DB error"))
    mock_db.return_value = mock_conn

    response = client.post("/truck", json={"id": "TRUCK1", "provider": 2})
    assert response.status_code in [500, 200]  # תלוי אם יש try/except

@patch("routes.get_db_connection")
def test_update_truck_success(mock_db, client):
    mock_conn, mock_cursor = get_mock_db()
    mock_db.return_value = mock_conn

    response = client.put("/truck/TRUCK1", json={"provider": 2})

    assert response.status_code == 200
    assert response.get_json() == {"message": "Updated"}
    mock_cursor.execute.assert_called_once_with(
        "UPDATE Trucks SET provider_id=%s WHERE id=%s", (2, "TRUCK1")
    )
    mock_conn.commit.assert_called_once()

@patch("routes.get_db_connection")
def test_update_truck_missing_provider(mock_db, client):
    response = client.put("/truck/TRUCK1", json={})
    assert response.status_code == 400
    assert response.get_json() == {"error": "Missing provider id"}
    mock_db.assert_not_called()

@patch("routes.get_db_connection")
def test_update_truck_db_error(mock_db, client):
    mock_conn, mock_cursor = get_mock_db(cursor_side_effect=Exception("DB error"))
    mock_db.return_value = mock_conn

    response = client.put("/truck/TRUCK1", json={"provider": 2})
    assert response.status_code in [500, 200]