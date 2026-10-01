from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_admin
from app.services.subscriptions import create_trial_for_establishment

import os
import psycopg


router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"]
)


def db():
    return psycopg.connect(os.environ["DATABASE_URL"])


@router.get("/pending")
def pending_establishments(
    current_user=Depends(require_admin)
):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                name,
                category,
                email,
                phone,
                latitude,
                longitude,
                description,
                status,
                created_at
            FROM establishments
            WHERE status = 'pending'
            ORDER BY created_at ASC
            """
        ).fetchall()

    return {
        "establishments": [
            {
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "email": row[3],
                "phone": row[4],
                "latitude": row[5],
                "longitude": row[6],
                "description": row[7],
                "status": row[8],
                "created_at": row[9]
            }
            for row in rows
        ]
    }


@router.get("/establishments")
def all_establishments(
    current_user=Depends(require_admin)
):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT
                e.id,
                e.name,
                e.category,
                e.email,
                e.phone,
                e.status,
                e.created_at,
                e.accepted_at,
                u.name,
                u.email
            FROM establishments e
            LEFT JOIN users u
                ON u.id = e.owner_user_id
            ORDER BY e.created_at DESC
            """
        ).fetchall()

    return {
        "establishments": [
            {
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "email": row[3],
                "phone": row[4],
                "status": row[5],
                "created_at": row[6],
                "accepted_at": row[7],
                "owner_name": row[8],
                "owner_email": row[9]
            }
            for row in rows
        ]
    }


@router.get("/users")
def all_users(
    current_user=Depends(require_admin)
):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                name,
                email,
                phone,
                role,
                language,
                created_at
            FROM users
            ORDER BY created_at DESC
            """
        ).fetchall()

    return {
        "users": [
            {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "phone": row[3],
                "role": row[4],
                "language": row[5],
                "created_at": row[6]
            }
            for row in rows
        ]
    }


@router.get("/subscriptions")
def all_subscriptions(
    current_user=Depends(require_admin)
):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT
                s.id,
                s.user_id,
                s.establishment_id,
                s.plan,
                s.price_fcfa,
                s.started_at,
                s.expires_at,
                s.status,
                s.auto_renew,
                u.name,
                u.email,
                e.name
            FROM subscriptions s
            LEFT JOIN users u
                ON u.id = s.user_id
            LEFT JOIN establishments e
                ON e.id = s.establishment_id
            ORDER BY s.started_at DESC
            """
        ).fetchall()

    return {
        "subscriptions": [
            {
                "id": row[0],
                "user_id": row[1],
                "establishment_id": row[2],
                "plan": row[3],
                "price_fcfa": row[4],
                "started_at": row[5],
                "expires_at": row[6],
                "status": row[7],
                "auto_renew": row[8],
                "user_name": row[9],
                "user_email": row[10],
                "establishment_name": row[11]
            }
            for row in rows
        ]
    }


@router.get("/payments")
def all_payments(
    current_user=Depends(require_admin)
):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT
                p.id,
                p.user_id,
                p.role,
                p.period,
                p.amount_fcfa,
                p.reference,
                p.status,
                p.provider,
                p.provider_transaction_id,
                p.created_at,
                p.paid_at,
                u.name,
                u.email
            FROM payment_requests p
            LEFT JOIN users u
                ON u.id = p.user_id
            ORDER BY p.created_at DESC
            """
        ).fetchall()

    return {
        "payments": [
            {
                "id": row[0],
                "user_id": row[1],
                "role": row[2],
                "period": row[3],
                "amount_fcfa": row[4],
                "reference": row[5],
                "status": row[6],
                "provider": row[7],
                "provider_transaction_id": row[8],
                "created_at": row[9],
                "paid_at": row[10],
                "user_name": row[11],
                "user_email": row[12]
            }
            for row in rows
        ]
    }


@router.post("/establishments/{establishment_id}/accept")
def accept_establishment(
    establishment_id: int,
    current_user=Depends(require_admin)
):
    with db() as conn:
        row = conn.execute(
            """
            UPDATE establishments
            SET
                status = 'accepted',
                accepted_at = NOW()
            WHERE id = %s
              AND status = 'pending'
            RETURNING id, name, category, status
            """,
            (establishment_id,)
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Demande introuvable ou déjà traitée"
        )

    create_trial_for_establishment(row[0])

    return {
        "message": "Établissement accepté",
        "establishment": {
            "id": row[0],
            "name": row[1],
            "category": row[2],
            "status": row[3]
        },
        "subscription": {
            "status": "trial",
            "duration_days": 14
        }
    }


@router.post("/establishments/{establishment_id}/refuse")
def refuse_establishment(
    establishment_id: int,
    current_user=Depends(require_admin)
):
    with db() as conn:
        row = conn.execute(
            """
            UPDATE establishments
            SET status = 'refused'
            WHERE id = %s
              AND status = 'pending'
            RETURNING id, name, category, status
            """,
            (establishment_id,)
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Demande introuvable ou déjà traitée"
        )

    return {
        "message": "Établissement refusé",
        "establishment": {
            "id": row[0],
            "name": row[1],
            "category": row[2],
            "status": row[3]
        }
    }


@router.post("/establishments/{establishment_id}/reactivate")
def reactivate_establishment(
    establishment_id: int,
    current_user=Depends(require_admin)
):
    with db() as conn:
        row = conn.execute(
            """
            UPDATE establishments
            SET status = 'accepted'
            WHERE id = %s
              AND status = 'suspended'
            RETURNING id, name, category, status
            """,
            (establishment_id,)
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Établissement suspendu introuvable"
        )

    return {
        "message": "Établissement réactivé",
        "establishment": {
            "id": row[0],
            "name": row[1],
            "category": row[2],
            "status": row[3]
        }
    }
