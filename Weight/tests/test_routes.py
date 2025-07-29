import pytest
from app.main import create_app
import sys
import os
import io
import json
from datetime import datetime,timedelta
from app.main import get_db_connection

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Test GET /health endpoint"""
    response = client.get("/health")
    assert response.status_code in [200, 500]  # Depending on DB connection
    assert response.data in [b"OK", b"Failure"]

def test_post_batch_weight_no_file(client):
    """Test POST /batch-weight with no file"""
    response = client.post("/batch-weight")
    assert response.status_code == 400
    assert response.json == {"error": "No file part in the request"}


def test_post_batch_weight_valid_file(client):
    #Test POST /batch-weight with a valid CSV file containing KG unit

    # Create a valid CSV content (header: id,unit)
    csv_content = "id,kg\nc1,50.5\nc2,65.2"
    data = {'file': (io.BytesIO(csv_content.encode()), 'valid_test.csv', 'text/csv')}

    response = client.post("/batch-weight", data=data, content_type='multipart/form-data')

    assert response.status_code == 201
    json_data = response.get_json()
    assert "containers inserted" in json_data.get("message", "").lower()

def test_get_unknown_containers(client):
    """Test GET /unknown containers"""
    response = client.get("/unknown")
    assert response.status_code == 200 or response.status_code == 500
    if response.status_code == 200:
        assert "unknown_containers" in response.json
        assert isinstance(response.json["unknown_containers"], list)

@pytest.fixture
def setup_container(client):
    """Insert a test container into the DB before IN test"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO containers_registered (container_id, weight, unit)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE weight=VALUES(weight), unit=VALUES(unit)
    """, ("test-container", 50.0, "kg"))
    conn.commit()
    cursor.close()
    conn.close()

def test_post_weight_in(client, setup_container):
    """Test POST /weight with direction=in"""
    data = {
        "direction": "in",
        "truck": "truck123",
        "containers": ["test-container"],
        "produce": "tomatoes",
        "weight": 1000
    }
    response = client.post("/weight", json=data)

    assert response.status_code == 201
    resp_json = response.get_json()
    assert resp_json.get("bruto") == 1000
    assert resp_json.get("truck") == "truck123"
    assert "id" in resp_json


def test_post_weight_out(client):
    """Test POST /weight with direction=out (after IN exists and truck info is valid)"""

    # 1. Insert IN transaction
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (datetime, direction, truck, containers, bruto, produce)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (datetime.now(), 'in', 'truck123', 'test-container', 5000, 'tomatoes'))
    conn.commit()
    cursor.close()
    conn.close()

    # 2. Create trucks.json with truck123
    trucks_dir = os.path.join(os.path.dirname(__file__), '../app/in')
    os.makedirs(trucks_dir, exist_ok=True)
    trucks_file_path = os.path.join(trucks_dir, 'trucks.json')
    with open(trucks_file_path, 'w') as f:
        json.dump([{"id": "truck123", "weight": 2000, "unit": "kg"}], f)

    # 3. Send OUT request
    data = {
        "direction": "out",
        "truck": "truck123",
        "containers": ["test-container"],
        "produce": "tomatoes"
    }
    response = client.post("/weight", json=data)

    # 4. Assert
    assert response.status_code == 201
    assert "neto" in response.json

@pytest.fixture
def insert_transactions():
    """Insert one IN transaction and one OUT transaction for testing"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    in_time = datetime.now() - timedelta(minutes=10)  
    cursor.execute(""" INSERT INTO transactions (datetime, direction, truck, containers, bruto, produce)  
    VALUES (%s, %s, %s, %s, %s, %s)  """, (in_time, 'in', 'test-truck', 'c1', 5000, 'tomatoes'))  
    in_id = cursor.lastrowid

    # Insert OUT transaction  
    out_time = datetime.now()  
    cursor.execute("""  
        INSERT INTO transactions (datetime, direction, truck, containers, bruto, truckTara, neto, produce)  
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)  
    """, (out_time, 'out', 'test-truck', 'c1', 5000, 2000, 2800, 'tomatoes'))

    conn.commit()  
    cursor.close()  
    conn.close()  
    return in_id

def test_get_session_with_out(client, insert_transactions):
    """Test /session/<id> with valid IN and OUT transactions"""
    session_id = insert_transactions
    response = client.get(f"/session/{session_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == session_id
    assert data["truck"] == "test-truck"
    assert data["bruto"] == 5000
    assert data["truckTara"] == 2000
    assert data["neto"] == 2800

def test_get_session_without_out(client):
    """Test /session/<id> with only IN transaction (no OUT yet)"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    in_time = datetime.now()
    cursor.execute("""  
    INSERT INTO transactions (datetime, direction, truck, containers, bruto, produce)  
    VALUES (%s, %s, %s, %s, %s, %s)  
    """, (in_time, 'in', 'solo-truck', 'c1', 4700, 'lettuce'))  
    in_id = cursor.lastrowid  
    conn.commit()  
    cursor.close()  
    conn.close()

    response = client.get(f"/session/{in_id}")  
    assert response.status_code == 200  
    data = response.get_json()  
    assert data["truck"] == "solo-truck"  
    assert data["bruto"] == 4700  
    assert "truckTara" not in data  
    assert "neto" not in data

def test_get_session_not_found(client):
    """Test /session/<id> with nonexistent session ID"""
    response = client.get("/session/999999")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Session not found"

def insert_test_transactions():
    """Insert some test transactions for the /weight endpoint"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()  
    earlier = now - timedelta(hours=1)

    # Insert IN transaction (no neto)  
    cursor.execute("""  
        INSERT INTO transactions (datetime, direction, bruto, neto, produce, containers)  
        VALUES (%s, %s, %s, %s, %s, %s)  """, (earlier, 'in', 5100, None, 'apples', 'c1,c2'))

    # Insert OUT transaction  
    cursor.execute("""  
        INSERT INTO transactions (datetime, direction, bruto, neto, produce, containers)  
        VALUES (%s, %s, %s, %s, %s, %s)  """, (now, 'out', 5200, 3000, 'apples', 'c1'))

    conn.commit()  
    cursor.close()  
    conn.close()

    return earlier, now

def test_get_weight(client):
    """Test GET /weight with from/to filter and direction types"""
    from_time, to_time = insert_test_transactions()
    from_str = from_time.strftime("%Y%m%d%H%M%S")
    to_str = to_time.strftime("%Y%m%d%H%M%S")
    response = client.get(f"/weight?from={from_str}&to={to_str}&filter=in,out")  
    assert response.status_code == 200

    data = response.get_json()  
    assert isinstance(data, list)  
    assert len(data) >= 2  # We inserted 2 transactions

    directions = set([d["direction"] for d in data])  
    assert "in" in directions  
    assert "out" in directions

    for row in data:  
        assert "bruto" in row  
        assert "produce" in row  
        assert isinstance(row["containers"], list)  
        assert row["neto"] == "na" or isinstance(row["neto"], int)
    
def insert_test_data_for_item():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Clean existing test data if any
    cursor.execute("DELETE FROM transactions WHERE truck = 'truck123' OR containers = 'cont1'")
    cursor.execute("DELETE FROM containers_registered WHERE container_id = 'cont1'")
    conn.commit()

    # Insert a container registration for cont1
    cursor.execute(
        "INSERT INTO containers_registered (container_id, weight) VALUES (%s, %s)",
        ('cont1', 1200))

    # Insert a truck IN transaction
    now = datetime.now()
    cursor.execute(
        """
        INSERT INTO transactions (datetime, direction, truck, containers, bruto, truckTara, produce)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (now - timedelta(minutes=30), 'in', 'truck123', 'cont1', 4000, 1800, 'potatoes'))

    conn.commit()
    cursor.close()
    conn.close()

def test_get_item_truck(client):
    insert_test_data_for_item()
    now = datetime.now()
    from_ts = (now - timedelta(hours=1)).strftime("%Y%m%d%H%M%S")
    to_ts = now.strftime("%Y%m%d%H%M%S")

    response = client.get(f"/item/truck123?from={from_ts}&to={to_ts}")
    assert response.status_code == 200
    data = response.get_json()

    assert data["id"] == "truck123"
    assert isinstance(data["tara"], int)
    assert isinstance(data["sessions"], list)
    assert len(data["sessions"]) > 0

def test_get_item_container(client):
    insert_test_data_for_item()
    now = datetime.now()
    from_ts = (now - timedelta(hours=1)).strftime("%Y%m%d%H%M%S")
    to_ts = now.strftime("%Y%m%d%H%M%S")

    response = client.get(f"/item/cont1?from={from_ts}&to={to_ts}")
    assert response.status_code == 200
    data = response.get_json()

    assert data["id"] == "cont1"
    assert isinstance(data["tara"], list)
    assert isinstance(data["sessions"], list)
    assert len(data["tara"]) > 0

def test_get_item_not_found(client):
    now = datetime.now()
    from_ts = (now - timedelta(hours=1)).strftime("%Y%m%d%H%M%S")
    to_ts = now.strftime("%Y%m%d%H%M%S")
    response = client.get(f"/item/notexist999?from={from_ts}&to={to_ts}")
    assert response.status_code == 404

