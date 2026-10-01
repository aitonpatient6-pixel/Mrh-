from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
import psycopg

from app.auth import get_current_user

router = APIRouter(
    prefix="/api/establishments",
    tags=["Establishments"]
)


class EstablishmentCreate(BaseModel):
    name: str
    category: str
    email: str
    phone: str
    latitude: float
    longitude: float
    description: str = ""


def db():
    return psycopg.connect(os.environ["DATABASE_URL"])


@router.post("/request")
def create_request(
    data: EstablishmentCreate,
    current_user=Depends(get_current_user)
):
    category = data.category.lower()

    if category not in ("restaurant", "hotel"):
        raise HTTPException(
            status_code=400,
            detail="La catégorie doit être restaurant ou hotel"
        )

    if current_user["role"] not in ("restaurant", "hotel"):
        raise HTTPException(
            status_code=403,
            detail="Cette demande est réservée aux comptes Restaurant ou Hôtel"
        )

    if current_user["role"] != category:
        raise HTTPException(
            status_code=403,
            detail="Le rôle du compte ne correspond pas à la catégorie"
        )

    with db() as conn:
        row = conn.execute(
            """
            INSERT INTO establishments
            (owner_user_id, name, category, email, phone,
             latitude, longitude, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, category, status
            """,
            (
                current_user["id"],
                data.name,
                category,
                data.email,
                data.phone,
                data.latitude,
                data.longitude,
                data.description
            )
        ).fetchone()

    return {
        "status": "pending",
        "message": "Demande d'adhésion enregistrée",
        "establishment": {
            "id": row[0],
            "name": row[1],
            "category": row[2],
            "status": row[3]
        }
    }


@router.get("/public")
def public_establishments(category: str | None = None):
    with db() as conn:
        if category:
            rows = conn.execute(
                """
                SELECT id, name, category, latitude, longitude, description
                FROM establishments
                WHERE status = 'accepted' AND category = %s
                ORDER BY name
                """,
                (category.lower(),)
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, name, category, latitude, longitude, description
                FROM establishments
                WHERE status = 'accepted'
                ORDER BY category, name
                """
            ).fetchall()

    return [
        {
            "id": r[0],
            "name": r[1],
            "category": r[2],
            "latitude": r[3],
            "longitude": r[4],
            "description": r[5]
        }
        for r in rows
    ]


@router.get("/my")
def my_establishment(
    current_user=Depends(get_current_user)
):
    with db() as conn:
        row = conn.execute(
            """
            SELECT id, name, category, email, phone,
                   latitude, longitude, description, status,
                   created_at, accepted_at
            FROM establishments
            WHERE owner_user_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (current_user["id"],)
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Aucun établissement associé à ce compte"
        )

    return {
        "establishment": {
            "id": row[0],
            "name": row[1],
            "category": row[2],
            "email": row[3],
            "phone": row[4],
            "latitude": row[5],
            "longitude": row[6],
            "description": row[7],
            "status": row[8],
            "created_at": row[9],
            "accepted_at": row[10]
        }
    }


@router.get("/my/notifications")
def my_notifications(
    current_user=Depends(get_current_user)
):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT n.id, n.type, n.message, n.is_read, n.created_at
            FROM notifications n
            INNER JOIN establishments e
                ON e.id = n.establishment_id
            WHERE e.owner_user_id = %s
            ORDER BY n.created_at DESC
            """,
            (current_user["id"],)
        ).fetchall()

    return [
        {
            "id": r[0],
            "type": r[1],
            "message": r[2],
            "is_read": r[3],
            "created_at": r[4]
        }
        for r in rows
    ]


@router.get("/my/subscription")
def my_establishment_subscription(
    current_user=Depends(get_current_user)
):
    with db() as conn:
        row = conn.execute(
            """
            SELECT s.id, s.plan, s.price_fcfa,
                   s.started_at, s.expires_at,
                   s.status, s.auto_renew
            FROM subscriptions s
            INNER JOIN establishments e
                ON e.id = s.establishment_id
            WHERE e.owner_user_id = %s
            ORDER BY s.started_at DESC
            LIMIT 1
            """,
            (current_user["id"],)
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Aucun abonnement trouvé pour cet établissement"
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
