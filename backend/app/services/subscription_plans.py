PLANS = {
    "client": {
        "monthly": 2000,
        "annual": 24000,
    },
    "restaurant": {
        "monthly": 3000,
        "annual": 36000,
    },
    "hotel": {
        "monthly": 3000,
        "annual": 36000,
    },
}


def get_plan_for_user(role: str, period: str):
    if role not in PLANS:
        raise ValueError("Type de compte invalide")

    if period not in ("monthly", "annual"):
        raise ValueError("Période invalide")

    return {
        "role": role,
        "period": period,
        "price_fcfa": PLANS[role][period],
    }
