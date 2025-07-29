from flask import Blueprint, jsonify, request, send_file
import mysql.connector
import os
import pandas as pd
from datetime import datetime
from db import get_db_connection 

routes = Blueprint("routes", __name__)

@routes.route('/')
def index():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM billdb')
        users = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify(users)
    except Exception:
        return {"error": "Database error"}, 500

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

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Provider (name) VALUES (%s)", (name,))
        conn.commit()
        return jsonify({"id": cursor.lastrowid})
    except mysql.connector.IntegrityError:
        return {"error": "Provider already exists"}, 400
    except Exception:
        return {"error": "Database error"}, 500

@routes.route("/provider/<int:provider_id>", methods=["PUT"])
def update_provider(provider_id):
    data = request.get_json()
    name = data.get("name")
    if not name:
        return {"error": "Missing name"}, 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Provider SET name=%s WHERE id=%s", (name, provider_id))
        conn.commit()
        return {"message": "Updated"}
    except Exception:
        return {"error": "Database error"}, 500

@routes.route("/truck", methods=["POST"])
def create_truck():
    data = request.get_json()
    provider_id = data.get("provider")
    truck_id = data.get("id")

    if not provider_id or not truck_id:
        return {"error": "Missing data"}, 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Trucks (id, provider_id) VALUES (%s, %s)", (truck_id, provider_id))
        conn.commit()
        return jsonify({"id": truck_id})
    except mysql.connector.IntegrityError:
        return {"error": "Truck already exists"}, 400
    except Exception:
        return {"error": "Database error"}, 500

@routes.route("/truck/<string:truck_id>", methods=["PUT"])
def update_truck(truck_id):
    data = request.get_json()
    provider_id = data.get("provider")
    if not provider_id:
        return {"error": "Missing provider id"}, 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Trucks SET provider_id=%s WHERE id=%s", (provider_id, truck_id))
        conn.commit()
        return {"message": "Updated"}
    except Exception:
        return {"error": "Database error"}, 500

@routes.route("/rates", methods=["POST"])
def upload_rates():
    path = "./in/rates.xlsx"
    try:
        df = pd.read_excel(path)
    except Exception:
        return {"error": "Failed to read Excel file"}, 500

    try:
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
    except Exception:
        return {"error": "Database error"}, 500

@routes.route("/rates", methods=["GET"])
def download_rates():
    try:
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
    except Exception:
        return {"error": "Failed to generate rates file"}, 500
    

######GET BILL#####
@app.route('/bills/<provider_id>/')
def totalbill(provider_id):
    # 1) Parse & validate time‐window
    t1_raw = request.args.get('from', '')
    t2_raw = request.args.get('to', '')
    now = datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def parse_ts(ts, default):
        try:
            return datetime.strptime(ts, "%Y%m%d%H%M%S")
        except:
            return default

    t1 = parse_ts(t1_raw, start_of_month)
    t2 = parse_ts(t2_raw, now)

    # 2) Fetch provider name
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM Provider WHERE id=%s", (provider_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close(); conn.close()
        return jsonify({"error": f"Provider {provider_id} not found"}), 404
    provider_name = row[0]
    cursor.close(); conn.close()

    # 3) Fetch truck IDs
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Trucks WHERE provider_id=%s", (provider_id,))
    trucks = [r[0] for r in cursor.fetchall()]
    cursor.close(); conn.close()

    # 4) Call Weight service
    payload = {
        "from":   t1.strftime("%Y%m%d%H%M%S"),
        "to":     t2.strftime("%Y%m%d%H%M%S"),
        "filter": "out"
    }
    product_summary = {}
    session_count  = 0

    for truck_id in trucks:
        res = requests.get("http://weight-app:5000/weight", params={**payload, "truck": truck_id})
        if res.status_code != 200:
            continue
        for rec in res.json():
            if rec.get("direction") != "out":
                continue
            session_count += 1
            prod = rec["produce"]
            neto = int(rec["neto"] or 0)
            if prod not in product_summary:
                product_summary[prod] = {"product": prod, "count": 0, "amount": 0}
            product_summary[prod]["count"]  += 1
            product_summary[prod]["amount"] += neto

    # 5) Look up rates and compute pay
    conn   = get_db_connection()
    cursor = conn.cursor()
    total_pay = 0
    products  = []

    for prod, data in product_summary.items():
        # scoped rate
        cursor.execute(
            "SELECT rate FROM Rates WHERE scope=%s AND product_id=%s",
            (provider_id, prod)
        )
        row = cursor.fetchone()
        if row:
            rate = row[0]
        else:
            cursor.execute(
                "SELECT rate FROM Rates WHERE scope='ALL' AND product_id=%s",
                (prod,)
            )
            row = cursor.fetchone()
            rate = row[0] if row else 0

        pay = data["amount"] * rate
        total_pay += pay

        products.append({
            "product": prod,
            "count":   data["count"],
            "amount":  data["amount"],
            "rate":    rate,
            "pay":     pay
        })

    cursor.close(); conn.close()

    # 6) Build and return the bill JSON
    bill = {
        "id":           provider_id,
        "name":         provider_name,
        "from":         t1.strftime("%Y%m%d%H%M%S"),
        "to":           t2.strftime("%Y%m%d%H%M%S"),
        "truckCount":   len(trucks),
        "sessionCount": session_count,
        "products":     products,
        "total":        total_pay
    }
    return jsonify(bill), 200

@routes.route("/truck/<string:truck_id>", methods=["GET"])
def get_truck_data(truck_id):
    t1 = request.args.get("from")
    t2 = request.args.get("to")

    now = datetime.now().strftime("%Y%m%d%H%M%S")
    first_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime("%Y%m%d%H%M%S")

    if not t1:
        t1 = first_of_month
    if not t2:
        t2 = now

    try:
        dt_from = datetime.strptime(t1, "%Y%m%d%H%M%S")
        dt_to = datetime.strptime(t2, "%Y%m%d%H%M%S")
    except ValueError:
        return {"error": "Invalid datetime format. Use yyyymmddhhmmss"}, 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM Trucks WHERE id = %s", (truck_id,))

    truck = cursor.fetchone()
    if not truck:
        return {"error": "Truck not found"}, 404

    cursor.execute("""
        SELECT truckTara FROM Transactions
        WHERE truck = %s AND truckTara IS NOT NULL
        ORDER BY datetime DESC
        LIMIT 1
    """, (truck_id,))
    tara_row = cursor.fetchone()
    tara = tara_row["truckTara"] if tara_row else None

    cursor.execute("""
        SELECT DISTINCT session_id FROM Transactions
        WHERE truck = %s AND datetime BETWEEN %s AND %s
        ORDER BY session_id ASC
    """, (truck_id, dt_from, dt_to))
    sessions = [row["session_id"] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return jsonify({
        "id": truck_id,
        "tara": tara,
        "sessions": sessions
    })
