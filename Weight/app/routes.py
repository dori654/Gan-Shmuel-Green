from flask import Blueprint, request, jsonify
from app.db import get_db_connection
from app.validators import validate_weight_payload

api = Blueprint('api', __name__)

@api.route("/weight", methods=["POST"])
def weight():
    data = request.get_json()
    is_valid, error = validate_weight_payload(data)
    if not is_valid:
        return jsonify({"error": error}), 400
    # Insert or process logic here...
    return jsonify({"message": "Weight data received"}), 200

@api.route("/weight", methods=["GET"], strict_slashes=False)
def get_weight():
    return jsonify({"message": "Not implemented yet"}), 200
