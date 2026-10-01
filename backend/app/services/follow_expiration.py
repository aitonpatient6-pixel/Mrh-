import os
import psycopg

from app.services.notifications import create_notification


def lock_expired_follows():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        rows = conn.execute(
            """
            UPDATE location_follows
            SET status = 'locked',
                stopped_at = COALESCE(stopped_at, NOW())
            WHERE status = 'active'
              AND expires_at IS NOT NULL
              AND expires_at <= NOW()
            RETURNING id, user_id, establishment_id
            """
        ).fetchall()

    for follow_id, user_id, establishment_id in rows:
        create_notification(
            establishment_id,
            user_id,
            "follow_locked",
            "Le suivi de localisation a été automatiquement verrouillé."
        )

    return len(rows)
