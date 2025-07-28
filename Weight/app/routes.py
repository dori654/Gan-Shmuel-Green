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

conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

@api.route('/weight', methods=['POST'])
def post_weight():
    data = request.get_json()

    direction = data.get('direction', '').lower()
    truck = data.get('truck')
    containers = data.get('containers', [])
    produce = data.get('produce')
    weight = data.get('weight')  # only for 'in'

    if not all([direction, truck, produce]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Convert containers to list if needed
    if isinstance(containers, str):
        container_ids = containers.split(",")
    else:
        container_ids = containers

    # === Connect to DB ===
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # === Lookup container weights ===
    format_strings = ','.join(['%s'] * len(container_ids))
    query = f"SELECT container_id, weight, unit FROM containers_registered WHERE container_id IN ({format_strings})"
    cursor.execute(query, tuple(container_ids))
    rows = cursor.fetchall()

    if len(rows) != len(container_ids):
        found_ids = [row['container_id'] for row in rows]
        missing = list(set(container_ids) - set(found_ids))
        return jsonify({'error': f'Missing containers in DB: {missing}'}), 400

    total_container_weight = 0
    for row in rows:
        if row['unit'] == 'lbs':
            total_container_weight += int(row['weight'] * 0.453592)
        else:
            total_container_weight += row['weight']

    containers_str = ",".join(container_ids)
    now = datetime.now()

    if direction == 'in':
        if weight is None:
            return jsonify({'error': 'Bruto weight must be provided for IN direction'}), 400

        cursor.execute("""
            INSERT INTO transactions (datetime, direction, truck, containers, bruto, produce)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (now, 'in', truck, containers_str, weight, produce))

        conn.commit()
        return jsonify({'message': 'Truck IN recorded', 'bruto': weight}), 201

    elif direction == 'out':
        # Find last unmatched 'in' transaction
        cursor.execute("""
            SELECT id, bruto FROM transactions
            WHERE truck = %s AND direction = 'in' AND truckTara IS NULL AND produce = %s
            ORDER BY datetime DESC LIMIT 1
        """, (truck, produce))
        in_entry = cursor.fetchone()

        if not in_entry:
            return jsonify({'error': 'No matching IN transaction found'}), 404

        # === Read truck weight from trucks.json ===
        try:
            trucks_path = os.path.join(os.path.dirname(__file__), 'in', 'trucks.json')
            with open(trucks_path, 'r') as f:
                truck_data = json.load(f)

            truck_match = next((t for t in truck_data if t['id'] == truck), None)
            if not truck_match:
                return jsonify({'error': f'Truck ID {truck} not found in trucks.json'}), 404

            truckTara = truck_match['weight']
            if truck_match.get('unit') == 'lbs':
                truckTara = int(truckTara * 0.453592)
        except Exception as e:
            return jsonify({'error': f'Error reading trucks.json: {str(e)}'}), 500

        bruto = in_entry['bruto']
        neto = bruto - truckTara - total_container_weight

        # Update IN transaction
        cursor.execute("""
            UPDATE transactions SET truckTara = %s, neto = %s WHERE id = %s
        """, (truckTara, neto, in_entry['id']))

        # Insert OUT transaction
        cursor.execute("""
            INSERT INTO transactions (datetime, direction, truck, containers, bruto, truckTara, neto, produce)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (now, 'out', truck, containers_str, bruto, truckTara, neto, produce))

        conn.commit()
        return jsonify({'message': 'Truck OUT recorded', 'neto': neto}), 201

    else:
        return jsonify({'error': 'Direction must be "in" or "out"'}), 400
    

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
    

