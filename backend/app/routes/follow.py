from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user, require_active_subscription
from app.services.notifications import create_notification

import os
import psycopg


router = APIRouter(
    prefix="/api/follow",
    tags=["Follow"]
)


def db():
    return psycopg.connect(os.environ["DATABASE_URL"])


class FollowRequest(BaseModel):
    establishment_id: int


@router.post("/start")
def start_follow(
    data: FollowRequest,
    current_user=Depends(require_active_subscription)
):
    establishment_id = data.establishment_id

    with db() as conn:
        establishment = conn.execute(
            """
            SELECT id, name, status
            FROM establishments
            WHERE id = %s
            """,
            (establishment_id,)
        ).fetchone()

        if not establishment:
            raise HTTPException(
                status_code=404,
                detail="Établissement introuvable"
            )

        if establishment[2] != "accepted":
            raise HTTPException(
                status_code=403,
                detail="Cet établissement n'est pas disponible"
            )

        existing = conn.execute(
            """
            SELECT id
            FROM location_follows
            WHERE user_id = %s
              AND establishment_id = %s
              AND status = 'active'
            LIMIT 1
            """,
            (current_user["id"], establishment_id)
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Un suivi est déjà actif"
            )

        follow = conn.execute(
            """
            INSERT INTO location_follows
            (
                user_id,
                establishment_id,
                status,
                started_at,
                expires_at
            )
            VALUES (
                %s,
                %s,
                'active',
                NOW(),
                NOW() + INTERVAL '30 minutes'
            )
            RETURNING id, started_at, expires_at
            """,
            (current_user["id"], establishment_id)
        ).fetchone()

    create_notification(
        establishment_id=establishment_id,
        user_id=None,
        notification_type="follow_started",
        message="Un client suit actuellement votre itinéraire."
    )

    return {
        "message": "Suivi démarré",
        "follow": {
            "id": follow[0],
            "establishment_id": establishment_id,
            "status": "active",
            "started_at": follow[1],
            "expires_at": follow[2]
        }
    }


@router.post("/stop")
def stop_follow(
    data: FollowRequest,
    current_user=Depends(require_active_subscription)
):
    establishment_id = data.establishment_id

    with db() as conn:
        follow = conn.execute(
            """
            UPDATE location_follows
            SET status = 'stopped',
                stopped_at = NOW()
            WHERE user_id = %s
              AND establishment_id = %s
              AND status = 'active'
            RETURNING id
            """,
            (current_user["id"], establishment_id)
        ).fetchone()

    if not follow:
        raise HTTPException(
            status_code=404,
            detail="Aucun suivi actif"
        )

    create_notification(
        establishment_id=establishment_id,
        user_id=None,
        notification_type="follow_stopped",
        message="Le suivi d'un client vient de s'arrêter."
    )

    return {
        "message": "Suivi arrêté",
        "follow_id": follow[0],
        "status": "stopped"
    }


@router.get("/me")
def my_follows(
    current_user=Depends(get_current_user)
):
    with db() as conn:
        rows = conn.execute(
            """
            SELECT
                lf.id,
                lf.establishment_id,
                e.name,
                e.category,
                e.latitude,
                e.longitude,
                lf.status,
                lf.started_at,
                lf.expires_at,
                lf.stopped_at
            FROM location_follows lf
            JOIN establishments e
              ON e.id = lf.establishment_id
            WHERE lf.user_id = %s
            ORDER BY lf.started_at DESC
            """,
            (current_user["id"],)
        ).fetchall()

    return {
        "follows": [
            {
                "id": row[0],
                "establishment_id": row[1],
                "name": row[2],
                "category": row[3],
                "latitude": row[4],
                "longitude": row[5],
                "status": row[6],
                "started_at": row[7],
                "expires_at": row[8],
                "stopped_at": row[9]
            }
            for row in rows
        ]
    }
