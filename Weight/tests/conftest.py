import pytest
import mysql.connector
import os

@pytest.fixture(scope="session", autouse=True)
def clear_database_before_tests():
    """Clears all data from transactions and containers_registered tables before tests."""
    conn = mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "weight")
    )
    cursor = conn.cursor()

    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM containers_registered")

    conn.commit()
    cursor.close()
    conn.close()
    print("🔄 Database cleared before tests.")
