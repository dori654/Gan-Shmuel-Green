import os
import mysql.connector
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        port=os.environ.get("DB_PORT"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
    )

def init_app(app):
    # This function exists for symmetry — no-op unless needed
    pass
