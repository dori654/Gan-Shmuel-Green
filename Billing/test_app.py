import pytest
from app import create_app


@pytest.fixture
def client():
    """Flask test client for functional requests."""
    test_app = create_app()
    test_app.config["TESTING"] = True
    with test_app.test_client() as client:
        yield client


def test_index_returns_json(client):
    """Ensure the root endpoint returns the expected payload and status."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json() == {"message": "Hello, Docker Compose!"}
