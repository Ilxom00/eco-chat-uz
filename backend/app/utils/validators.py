import re

def validate_phone(phone: str) -> str:
    cleaned = re.sub(r'\D', '', phone)
    if len(cleaned) == 9:
        return f"+998{cleaned}"
    elif len(cleaned) == 12 and cleaned.startswith("998"):
        return f"+{cleaned}"
    raise ValueError("Invalid phone format")

def validate_full_name(name: str) -> bool:
    if not name or len(name.strip()) < 3:
        return False
    if name.strip().isdigit():
        return False
    return True
