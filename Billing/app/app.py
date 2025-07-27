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

@app.route("/provider/<int:provider_id>", methods=["PUT"])
def update_provider(provider_id):
    data = request.get_json()
    name = data.get("name")
    if not name:
        return {"error": "Missing name"}, 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Provider SET name=%s WHERE id=%s", (name, provider_id))
    conn.commit()
    return {"message": "Updated"}

@app.route("/truck", methods=["POST"])
def create_truck():
    data = request.get_json()
    provider_id = data.get("provider")
    truck_id = data.get("id")

    if not provider_id or not truck_id:
        return {"error": "Missing data"}, 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)", (truck_id, provider_id))
    conn.commit()
    return jsonify({"id": truck_id})

@app.route("/truck/<string:truck_id>", methods=["PUT"])
def update_truck(truck_id):
    data = request.get_json()
    provider_id = data.get("provider")
    if not provider_id:
        return {"error": "Missing provider id"}, 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Trucks SET provider_id=%s WHERE id=%s", (provider_id, truck_id))
    conn.commit()
    return {"message": "Updated"}



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)