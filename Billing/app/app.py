from flask import Flask, jsonify,request
import mysql.connector
import os

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM billdb')
    users = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(users)

@app.route("/health")
def health():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return "OK", 200
    except Exception as e:
        return "Failure", 500

@app.route("/provider", methods=["POST"])
def create_provider():
    data = request.get_json()
    name = data.get("name")
    if not name:
        return {"error": "Missing name"}, 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Provider (name) VALUES (%s)", (name,))
        conn.commit()
        return jsonify({"id": cursor.lastrowid})
    except mysql.connector.IntegrityError:
        return {"error": "Provider already exists"}, 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)