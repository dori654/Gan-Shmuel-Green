from flask import Blueprint, jsonify, request, send_file
import mysql.connector
import os
import pandas as pd

from db import get_db_connection 

routes = Blueprint("routes", __name__)

@routes.route('/kobi', methods=['GET'])
def get_kobi():
    return jsonify({
        'kobi': 'Gan Shmuel Green',
        'version': '1.0.0',
        'description': 'API for managing truck weights and transactions'
    })

@routes.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM billdb')
    users = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(users)

@routes.route("/health")
def health():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return "OK", 200
    except Exception:
        return "Failure", 500

@routes.route("/provider", methods=["POST"])
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

@routes.route("/provider/<int:provider_id>", methods=["PUT"])
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

@routes.route("/truck", methods=["POST"])
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

@routes.route("/truck/<string:truck_id>", methods=["PUT"])
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

@routes.route("/rates", methods=["POST"])
def upload_rates():
    path = "./in/rates.xlsx"

    df = pd.read_excel(path)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Rates")

    for _, row in df.iterrows():
        product_id = row["Product"] 
        rate = int(row["Rate"])
        scope = row["Scope"]

        if pd.isna(scope) or str(scope).strip().lower() == "all":
            scope = "All"
        else:
            scope = str(scope).strip()

        cursor.execute(
            "INSERT INTO Rates (product_id, rate, scope) VALUES (%s, %s, %s)",
            (product_id, rate, scope)
        )
    conn.commit()
    return {"message": "Rates uploaded successfully"}

@routes.route("/rates", methods=["GET"])
def download_rates():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Rates")
    rates = cursor.fetchall()

    df = pd.DataFrame(rates)
    path = "./in/exported_rates.xlsx"
    df.to_excel(path, index=False)

    return send_file(
        path,
        as_attachment=True,
        download_name="rates.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )