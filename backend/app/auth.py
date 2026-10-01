import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import psycopg
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = os.getenv("MRH_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("MRH_SECRET_KEY n'est pas configurée")

ALGORITHM = "HS256"

security = HTTPBearer()


def db():
    return psycopg.connect(os.environ["DATABASE_URL"])


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000
    ).hex()

    return f"pbkdf2_sha256$200000${salt}${password_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_hash = stored_hash.split("$")

        if algorithm != "pbkdf2_sha256":
            return False

        calculated_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations)
        ).hex()

        return secrets.compare_digest(
            calculated_hash,
            expected_hash
        )

    except (ValueError, TypeError):
        return False


def create_token(user_id: int, role: str):
    expires = datetime.now(timezone.utc) + timedelta(days=7)

    return jwt.encode(
        {
            "sub": str(user_id),
            "role": role,
            "exp": expires
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = int(payload["sub"])

    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Token invalide ou expiré"
        )

    with db() as conn:
        user = conn.execute(
            """
            SELECT id, name, email, role, language
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        ).fetchone()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Utilisateur introuvable"
        )

    return {
        "id": user[0],
        "name": user[1],
        "email": user[2],
        "role": user[3],
        "language": user[4]
    }


def require_admin(current_user=Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Accès réservé au PDG"
        )

    return current_user


def require_active_subscription(current_user=Depends(get_current_user)):
    """
    Vérifie que l'utilisateur possède un abonnement
    actuellement actif ou en période d'essai.
    """
    import psycopg
    import os

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute(
            """
            SELECT status, expires_at
            FROM subscriptions
            WHERE user_id = %s
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (current_user["id"],)
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=403,
            detail="Aucun abonnement actif"
        )

    status, expires_at = row

    if status not in ("trial", "active"):
        raise HTTPException(
            status_code=403,
            detail="Abonnement inactif"
        )

    if expires_at is not None:
        from datetime import datetime, timezone
        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=403,
                detail="Abonnement expiré"
            )

    return current_user
