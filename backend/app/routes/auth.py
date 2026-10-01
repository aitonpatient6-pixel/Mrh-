from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
import psycopg

from app.auth import hash_password, verify_password, create_token, get_current_user
from app.services.subscriptions import create_trial_for_user

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

def db():
    return psycopg.connect(os.environ["DATABASE_URL"])


class RegisterData(BaseModel):
    name: str
    email: str
    phone: str = ""
    password: str
    role: str = "client"
    language: str = "fr"


class LoginData(BaseModel):
    email: str
    password: str


@router.post("/register")
def register(data: RegisterData):
    role = data.role.lower()

    if role not in ("client", "restaurant", "hotel"):
        raise HTTPException(
            status_code=400,
            detail="Rôle invalide"
        )

    if len(data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Le mot de passe doit contenir au moins 6 caractères"
        )

    with db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = %s",
            (data.email,)
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Cette adresse email existe déjà"
            )

        password_hash = hash_password(data.password)

        row = conn.execute(
            """
            INSERT INTO users
            (name, email, phone, role, language, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, email, role, language
            """,
            (
                data.name,
                data.email,
                data.phone,
                role,
                data.language,
                password_hash
            )
        ).fetchone()

    if row[3] == "client":
        create_trial_for_user(row[0])

    token = create_token(row[0], row[3])

    return {
        "message": "Compte créé",
        "token": token,
        "user": {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "role": row[3],
            "language": row[4]
        }
    }


@router.post("/login")
def login(data: LoginData):
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, name, email, role, language, password_hash
            FROM users
            WHERE email = %s
            """,
            (data.email,)
        ).fetchone()

    if not row or not row[5]:
        raise HTTPException(
            status_code=401,
            detail="Email ou mot de passe incorrect"
        )

    if not verify_password(data.password, row[5]):
        raise HTTPException(
            status_code=401,
            detail="Email ou mot de passe incorrect"
        )

    if row[3] == "client":
        create_trial_for_user(row[0])

    token = create_token(row[0], row[3])

    return {
        "message": "Connexion réussie",
        "token": token,
        "user": {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "role": row[3],
            "language": row[4]
        }
    }


@router.get("/subscription")
def my_subscription(
    current_user=Depends(get_current_user)
):
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, plan, price_fcfa, started_at,
                   expires_at, status, auto_renew
            FROM subscriptions
            WHERE user_id = %s
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (current_user["id"],)
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Aucun abonnement trouvé"
        )

    return {
        "subscription": {
            "id": row[0],
            "plan": row[1],
            "price_fcfa": row[2],
            "started_at": row[3],
            "expires_at": row[4],
            "status": row[5],
            "auto_renew": row[6]
        }
    }


@router.get("/notifications")
def my_notifications(
    current_user=Depends(get_current_user)
):
    import os
    import psycopg

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                type,
                message,
                is_read,
                created_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (current_user["id"],)
        ).fetchall()

    return {
        "notifications": [
            {
                "id": row[0],
                "type": row[1],
                "message": row[2],
                "is_read": row[3],
                "created_at": row[4]
            }
            for row in rows
        ]
    }
