import os
import uuid
from datetime import datetime, timedelta, timezone

import psycopg


def db():
    return psycopg.connect(os.environ["DATABASE_URL"])


def create_payment_request(
    user_id: int,
    role: str,
    period: str,
    price_fcfa: int
):
    reference = f"MRH-{uuid.uuid4().hex[:16].upper()}"

    with db() as conn:
        row = conn.execute(
            """
            INSERT INTO payment_requests
            (
                user_id,
                role,
                period,
                amount_fcfa,
                reference,
                status
            )
            VALUES (%s, %s, %s, %s, %s, 'pending')
            RETURNING id, reference, status
            """,
            (
                user_id,
                role,
                period,
                price_fcfa,
                reference
            )
        ).fetchone()

    return {
        "id": row[0],
        "reference": row[1],
        "status": row[2],
        "amount_fcfa": price_fcfa,
        "period": period
    }


def activate_subscription_after_payment(
    payment_request_id: int,
    provider_transaction_id: str | None = None
):
    """
    Confirme un paiement et réactive automatiquement
    l'abonnement correspondant.

    Cette fonction est volontairement indépendante de FedaPay.
    FedaPay pourra l'appeler plus tard via son webhook.
    """

    with db() as conn:

        payment = conn.execute(
            """
            SELECT
                id,
                user_id,
                role,
                period,
                amount_fcfa,
                status
            FROM payment_requests
            WHERE id = %s
            FOR UPDATE
            """,
            (payment_request_id,)
        ).fetchone()

        if not payment:
            raise ValueError("Demande de paiement introuvable")

        (
            payment_id,
            user_id,
            role,
            period,
            amount_fcfa,
            status
        ) = payment

        if status != "pending":
            raise ValueError(
                f"Paiement déjà traité : {status}"
            )

        now = datetime.now(timezone.utc)

        if period == "monthly":
            expires_at = now + timedelta(days=30)
        elif period == "annual":
            expires_at = now + timedelta(days=365)
        else:
            raise ValueError("Période de paiement invalide")

        if role in ("restaurant", "hotel"):

            establishment = conn.execute(
                """
                SELECT id
                FROM establishments
                WHERE owner_user_id = %s
                  AND category = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, role)
            ).fetchone()

            if not establishment:
                raise ValueError(
                    "Établissement du compte introuvable"
                )

            establishment_id = establishment[0]

            subscription = conn.execute(
                """
                SELECT id
                FROM subscriptions
                WHERE establishment_id = %s
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (establishment_id,)
            ).fetchone()

            if subscription:
                subscription_id = subscription[0]

                conn.execute(
                    """
                    UPDATE subscriptions
                    SET
                        plan = %s,
                        price_fcfa = %s,
                        started_at = %s,
                        expires_at = %s,
                        status = 'active',
                        auto_renew = FALSE
                    WHERE id = %s
                    """,
                    (
                        period,
                        amount_fcfa,
                        now,
                        expires_at,
                        subscription_id
                    )
                )
            else:
                conn.execute(
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
                    VALUES (%s, %s, %s, %s, %s, 'active', FALSE)
                    """,
                    (
                        establishment_id,
                        period,
                        amount_fcfa,
                        now,
                        expires_at
                    )
                )

            conn.execute(
                """
                UPDATE establishments
                SET status = 'accepted'
                WHERE id = %s
                """,
                (establishment_id,)
            )

            conn.execute(
                """
                INSERT INTO notifications
                (
                    user_id,
                    establishment_id,
                    type,
                    message
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    user_id,
                    establishment_id,
                    "subscription_reactivated",
                    "Votre abonnement a été réactivé avec succès."
                )
            )

        elif role == "client":

            subscription = conn.execute(
                """
                SELECT id
                FROM subscriptions
                WHERE user_id = %s
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (user_id,)
            ).fetchone()

            if subscription:
                conn.execute(
                    """
                    UPDATE subscriptions
                    SET
                        plan = %s,
                        price_fcfa = %s,
                        started_at = %s,
                        expires_at = %s,
                        status = 'active',
                        auto_renew = FALSE
                    WHERE id = %s
                    """,
                    (
                        period,
                        amount_fcfa,
                        now,
                        expires_at,
                        subscription[0]
                    )
                )
            else:
                conn.execute(
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
                    VALUES (%s, %s, %s, %s, %s, 'active', FALSE)
                    """,
                    (
                        user_id,
                        period,
                        amount_fcfa,
                        now,
                        expires_at
                    )
                )

            conn.execute(
                """
                INSERT INTO notifications
                (
                    user_id,
                    establishment_id,
                    type,
                    message
                )
                VALUES (%s, NULL, %s, %s)
                """,
                (
                    user_id,
                    "subscription_reactivated",
                    "Votre abonnement a été activé avec succès."
                )
            )

        else:
            raise ValueError("Type de compte invalide")

        conn.execute(
            """
            UPDATE payment_requests
            SET
                status = 'paid',
                provider_transaction_id = %s,
                paid_at = %s
            WHERE id = %s
            """,
            (
                provider_transaction_id,
                now,
                payment_id
            )
        )

    return {
        "payment_request_id": payment_id,
        "status": "paid",
        "subscription_status": "active",
        "period": period,
        "expires_at": expires_at.isoformat()
    }
