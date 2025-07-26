from flask import Blueprint, request, jsonify
from app.validators import validate_weight_payload

api = Blueprint("api", __name__)

@api.route("/weight", methods=["POST"])
def post_weight():
    data = request.get_json()

    is_valid, error = validate_weight_payload(data)
    if not is_valid:
        return jsonify({"error": error}), 400

    # All good – use the data
    return jsonify({
        "message": "Weight received",
        "payload": data
    }), 201
