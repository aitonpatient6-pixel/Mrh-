import os
from datetime import datetime, timedelta, timezone

import psycopg


TRIAL_DAYS = 14


def db():
    return psycopg.connect(os.environ["DATABASE_URL"])


def create_trial_for_user(user_id: int):
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=TRIAL_DAYS)

    with db() as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM subscriptions
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,)
        ).fetchone()

        if existing:
            return existing[0]

        row = conn.execute(
            """
            INSERT INTO subscriptions
            (
                user_id,
                plan,
                price_fcfa,
                started_at,
                expires_at,
                status,
                auto_renew
            )
            VALUES (%s, %s, %s, %s, %s, 'trial', FALSE)
            RETURNING id
            """,
            (
                user_id,
                "trial_14_days",
                0,
                now,
                expires_at
            )
        ).fetchone()

    return row[0]


def create_trial_for_establishment(establishment_id: int):
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=TRIAL_DAYS)

    with db() as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM subscriptions
            WHERE establishment_id = %s
            LIMIT 1
            """,
            (establishment_id,)
        ).fetchone()

        if existing:
            return existing[0]

        row = conn.execute(
            """
            INSERT INTO subscriptions
            (
                establishment_id,
                plan,
                price_fcfa,
                started_at,
                expires_at,
                status,
                auto_renew
            )
            VALUES (%s, %s, %s, %s, %s, 'trial', FALSE)
            RETURNING id
            """,
            (
                establishment_id,
                "trial_14_days",
                0,
                now,
                expires_at
            )
        ).fetchone()

    return row[0]
