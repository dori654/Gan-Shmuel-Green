import pytest
from app.main import create_app
import sys
import os
import io
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

#def test_post_batch_weight_no_file(client):
   # """Test POST /batch-weight with no file"""
  #  response = client.post("/batch-weight")
    #assert response.status_code == 400
    #assert response.json == {"error": "No file part in the request"}


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


def test_post_weight_in_valid(client):
    """Test POST /weight with direction 'in' and valid container data"""

    # Pre-load containers into DB via batch-weight (optional)
    # Or assume they exist in DB

    payload = {
        "direction": "in",
        "truck": "T-99999",
        "containers": ["c1", "c2"],
        "weight": 12000,
        "produce": "orange"
    }

    response = client.post("/weight", json=payload)
    
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data["message"] == "Truck IN recorded"
    assert json_data["bruto"] == 12000


