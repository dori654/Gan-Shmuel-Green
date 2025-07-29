import os
import pytest
from unittest.mock import patch, MagicMock
from app.db import get_db_connection

@patch("app.db.mysql.connector.connect")
def test_get_db_connection(mock_connect):
    os.environ["DB_HOST"] = "myhost"
    os.environ["DB_USER"] = "myuser"
    os.environ["DB_PASSWORD"] = "mypassword"
    os.environ["DB_NAME"] = "mydatabase"

    mock_connection = MagicMock()
    mock_connect.return_value = mock_connection

    conn = get_db_connection()

    assert conn == mock_connection

    mock_connect.assert_called_once_with(
        host="myhost",
        user="myuser",
        password="mypassword",
        database="mydatabase"
    )