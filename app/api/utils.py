def validate_input(data, required_fields):
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing or invalid field: {field}"
    return True, None


def validate_active_field(active):
    if isinstance(active, bool):
        return active

    if isinstance(active, str):
        truthy_values = {"true", "1", "yes"}
        falsy_values = {"false", "0", "no"}

        active_value_lower = active.strip().lower()
        if active_value_lower in truthy_values:
            return True
        elif active_value_lower in falsy_values:
            return False
    
    return None
