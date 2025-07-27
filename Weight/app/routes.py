from flask import Blueprint, request, jsonify
from app.db import get_db_connection
from app.validators import validate_weight_payload
from datetime import datetime

api = Blueprint('api', __name__)

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





@api.route("/weight", methods=["GET"], strict_slashes=False)
def get_weight():
    return jsonify({"message": "Not implemented yet"}), 200
