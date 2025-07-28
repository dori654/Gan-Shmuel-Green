from flask import Blueprint, request, jsonify
from app.db import get_db_connection
from app.validators import validate_weight_payload
from datetime import datetime
import os
import csv
import json
from werkzeug.utils import secure_filename
UPLOAD_FOLDER = '/in'

api = Blueprint('api', __name__)
        
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@api.route("/weight", methods=["POST"])
def post_weight():
    data = request.get_json()
    is_valid, error = validate_weight_payload(data)
    if not is_valid:
        return jsonify({"error": error}), 400

    direction = data["direction"]
    truck = data["truck"]
    containers = data["containers"]
    bruto = data["weight"]
    unit = data["unit"]
    if unit.lower() in ["lbs", "lb"]:
        bruto = int(float(bruto) * 0.453592)  # Convert lbs to kg
    force = data["force"]
    produce = data["produce"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Look for previous session if direction is "out"
    if direction == "out":
        cursor.execute(
            "SELECT * FROM transactions WHERE truck = %s AND direction = 'in' ORDER BY datetime DESC LIMIT 1",
            (truck,)
        )
        in_session = cursor.fetchone()

        if not in_session:
            return jsonify({"error": "No prior 'in' session for this truck"}), 400

        if in_session and not force:
            # Check if already had an "out"
            cursor.execute(
                "SELECT * FROM transactions WHERE truck = %s AND direction = 'out' ORDER BY datetime DESC LIMIT 1",
                (truck,)
            )
            out_session = cursor.fetchone()
            if out_session and out_session["datetime"] > in_session["datetime"]:
                return jsonify({"error": "Truck already weighed 'out'"}), 400

        # Get truckTara (bruto - in_session['bruto'])
        truckTara = bruto
        neto = calculate_neto(in_session["containers"], conn, in_session["bruto"], truckTara)

        cursor.execute(
            "INSERT INTO transactions (datetime, direction, truck, containers, bruto, truckTara, neto, produce) VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s)",
            ("out", truck, in_session["containers"], bruto, truckTara, neto, produce)
        )
        conn.commit()
        session_id = cursor.lastrowid

        return jsonify({
            "id": session_id,
            "truck": truck,
            "bruto": bruto,
            "truckTara": truckTara,
            "neto": neto
        }), 201

    else:  # "in" or "none"
        # Check for repeated in
        if direction == "in":
            cursor.execute(
                "SELECT * FROM transactions WHERE truck = %s AND direction = 'in' ORDER BY datetime DESC LIMIT 1",
                (truck,)
            )
            in_session = cursor.fetchone()
            if in_session and not force:
                return jsonify({"error": "Truck already weighed 'in'"}), 400

        containers_str = containers  # Already comma-separated
        cursor.execute(
            "INSERT INTO transactions (datetime, direction, truck, containers, bruto, truckTara, neto, produce) VALUES (NOW(), %s, %s, %s, %s, NULL, NULL, %s)",
            (direction, truck, containers_str, bruto, produce)
        )
        conn.commit()
        session_id = cursor.lastrowid

        return jsonify({
            "message": f"Truck entered successfully",
            "id": session_id,
            "truck": truck,
            "bruto": bruto
        }), 201

@api.route('/batch-weight', methods=['POST'])
def upload_batch_weights():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    # Save file to /in folder
    file.save(filepath)
    containers = []
    try:
        if filename.endswith('.json'):
            with open(filepath, 'r') as f:
                containers = json.load(f)
        elif filename.endswith('.csv'):
            with open(filepath, newline='') as f:
                reader = csv.reader(f)
                headers = next(reader)
                unit = headers[1].strip().lower()  # kg or lbs
                if unit not in ['kg', 'lbs']:
                    return jsonify({'error': f'Invalid unit: {unit}'}), 400
                for row in reader:
                    cid, weight = row
                    weight = float(weight)
                    if unit == 'lbs':
                        weight = round(weight * 0.453592, 2)  # convert lbs to kg
                        containers.append({
                              'id': cid.strip(),
                              'weight': weight,
                              'unit': 'kg'
                                })
                    else:
                        containers.append({
                              'id': cid.strip(),
                              'weight': weight,
                              'unit': 'kg'
                                })

        else:
            return jsonify({'error': 'Unsupported file format'}), 400
         # Insert into DB
        conn = get_db_connection()
        cursor = conn.cursor()
        for c in containers:
            cursor.execute("""
                           INSERT INTO containers_registered (container_id, weight, unit)
                           VALUES (%s, %s, %s)
                           ON DUPLICATE KEY UPDATE weight=VALUES(weight), unit=VALUES(unit)
                            """, (c['id'], c['weight'], c['unit']))
        conn.commit()
        return jsonify({'message': f'{len(containers)} containers inserted'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500





@api.route("/weight", methods=["GET"], strict_slashes=False)
def get_weight():
    # Get query parameters
    from_param = request.args.get("from")
    to_param = request.args.get("to")
    filters = request.args.get("filter", "in,out,none").split(",")

    # Parse datetime strings (format: yyyymmddhhmmss)
    def parse_timestamp(ts, default):
        try:
            return datetime.strptime(ts, "%Y%m%d%H%M%S")
        except:
            return default

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    from_time = parse_timestamp(from_param, today_start)
    to_time = parse_timestamp(to_param, now)

    # Get DB connection
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Build SQL query dynamically
    placeholders = ",".join(["%s"] * len(filters))
    query = f"""
        SELECT id, direction, bruto, neto, produce, containers
        FROM transactions
        WHERE datetime BETWEEN %s AND %s
        AND direction IN ({placeholders})
        ORDER BY datetime DESC
    """
    cursor.execute(query, (from_time, to_time, *filters))
    results = cursor.fetchall()

    # Format containers field from CSV to list
    for row in results:
        row["containers"] = row["containers"].split(",") if row["containers"] else []
        if row["neto"] is None:
            row["neto"] = "na"

    return jsonify(results), 200
    

@api.route('/unknown', methods=['GET'])
def get_unknown_containers():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Step 1: Get known containers
        cursor.execute("SELECT container_id FROM containers_registered")
        known_containers = set(row[0] for row in cursor.fetchall())

        # Step 2: Get all containers mentioned in transactions
        cursor.execute("SELECT containers FROM transactions")
        unknown_containers = set()
        for (container_str,) in cursor.fetchall():
            if container_str:
                container_ids = [c.strip() for c in container_str.split(',')]
                for cid in container_ids:
                    if cid and cid not in known_containers:
                        unknown_containers.add(cid)

        return jsonify({"unknown_containers": sorted(list(unknown_containers))}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

