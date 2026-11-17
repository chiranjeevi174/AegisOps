def calculate_total(price: float, quantity: int) -> float:
    return price * quantity


def calculate_discount(total: float, discount: float) -> float:
    return total - discount


def is_high_severity(severity: str) -> bool:
    return severity.lower() in {"critical", "high"}