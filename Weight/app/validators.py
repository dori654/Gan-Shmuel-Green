def validate_weight_payload(data):
    required_fields = ['direction', 'truck', 'containers', 'weight', 'unit', 'force', 'produce']
    missing = [field for field in required_fields if field not in data]
    if missing:
        return False, f"Missing fields: {', '.join(missing)}"
    
    # Optionally: validate values
    if data["direction"] not in ("in", "out", "none"):
        return False, "Invalid direction value"
    
    if data["unit"].lower() not in ["kg", "lbs", "lb"]:
        return False, "Invalid unit (only 'kg' or 'lbs' are supported)"

    if not isinstance(data["weight"], (int, float)):
        return False, "Weight must be a number"

    return True, None
