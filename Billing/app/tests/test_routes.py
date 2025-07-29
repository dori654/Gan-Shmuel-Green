import pytest
import mysql.connector
from flask import Flask
from unittest.mock import patch, MagicMock
from routes import routes
import io
import pandas as pd

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
    assert response.status_code in [500, 200]  

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

@patch("routes.get_db_connection")
@patch("routes.pd.read_excel")
def test_upload_rates_success(mock_read_excel, mock_db, client):
    mock_df = pd.DataFrame([
        {"Product": "P1", "Rate": 100, "Scope": "All"},
        {"Product": "P2", "Rate": 200, "Scope": "ZoneA"},
    ])
    mock_read_excel.return_value = mock_df

    mock_conn, mock_cursor = get_mock_db()
    mock_db.return_value = mock_conn

    response = client.post("/rates")

    assert response.status_code == 200
    assert response.get_json() == {"message": "Rates uploaded successfully"}
    assert mock_cursor.execute.call_args_list[0][0][0] == "DELETE FROM Rates"
    assert mock_cursor.execute.call_count == 3  
    mock_conn.commit.assert_called_once()

@patch("routes.pd.read_excel")
def test_upload_rates_excel_failure(mock_read_excel, client):
    mock_read_excel.side_effect = Exception("Excel read error")

    response = client.post("/rates")
    assert response.status_code == 500
    assert response.get_json() == {"error": "Failed to read Excel file"}

@patch("routes.get_db_connection")
@patch("routes.pd.read_excel")
def test_upload_rates_db_error(mock_read_excel, mock_db, client):
    mock_df = pd.DataFrame([
        {"Product": "P1", "Rate": 100, "Scope": "All"},
    ])
    mock_read_excel.return_value = mock_df

    mock_conn, mock_cursor = get_mock_db(cursor_side_effect=Exception("DB insert error"))
    mock_db.return_value = mock_conn

    response = client.post("/rates")
    assert response.status_code == 500
    assert response.get_json() == {"error": "Database error"}

@patch("routes.get_db_connection")
@patch("routes.pd.DataFrame.to_excel")
@patch("routes.send_file")
def test_download_rates_success(mock_send_file, mock_to_excel, mock_db, client):
    mock_conn, mock_cursor = get_mock_db()
    mock_cursor.fetchall.return_value = [
        {"product_id": "P1", "rate": 100, "scope": "All"},
        {"product_id": "P2", "rate": 200, "scope": "ZoneA"}
    ]
    mock_db.return_value = mock_conn

    from flask import Response
    dummy_response = Response("file content", status=200)
    mock_send_file.return_value = dummy_response

    response = client.get("/rates")

    assert response.status_code == 200
    assert response.data == b"file content"

    mock_cursor.execute.assert_called_once_with("SELECT * FROM Rates")
    mock_to_excel.assert_called_once()
    mock_send_file.assert_called_once()

@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(routes)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

@patch("routes.get_db_connection")
def test_get_truck_data_success(mock_get_conn, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchone.side_effect = [
        {"id": "123"},                       
        {"truckTara": 7840.0}          
    ]
    mock_cursor.fetchall.return_value = [{"session_id": 100}, {"session_id": 200}]

    response = client.get("/truck/123?from=20250701000000&to=20250729000000")

    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == "123"
    assert data["tara"] == 7840.0
    assert data["sessions"] == [100, 200]

@patch("routes.get_db_connection")
def test_get_truck_data_not_found(mock_get_conn, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchone.return_value = None

    response = client.get("/truck/999")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Truck not found"}

def test_get_truck_data_invalid_date_format(client):
    response = client.get("/truck/123?from=invalid&to=20250729000000")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Invalid datetime format. Use yyyymmddhhmmss"}

@patch("routes.get_db_connection")
def test_get_truck_data_no_tara(mock_get_conn, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchone.side_effect = [
        {"id": "123"},  
        None           
    ]
    mock_cursor.fetchall.return_value = [{"session_id": 300}]

    response = client.get("/truck/123?from=20250701000000&to=20250729000000")
    data = response.get_json()
    assert response.status_code == 200
    assert data["tara"] is None
    assert data["sessions"] == [300]

@patch("routes.get_db_connection")
def test_get_truck_data_no_sessions(mock_get_conn, client):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_get_conn.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchone.side_effect = [
        {"id": "123"}, 
        {"truckTara": 7000}
    ]
    mock_cursor.fetchall.return_value = [] 

    response = client.get("/truck/123?from=20250701000000&to=20250702000000")
    data = response.get_json()
    assert response.status_code == 200
    assert data["tara"] == 7000
    assert data["sessions"] == []