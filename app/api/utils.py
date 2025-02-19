def validate_input(data, required_fields):
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing or invalid field: {field}"
    return True, None
