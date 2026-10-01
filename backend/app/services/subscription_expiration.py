import os
import psycopg


def expire_subscriptions():
    """
    Expire automatiquement les abonnements arrivés à échéance.
    Suspend les établissements Restaurant/Hôtel concernés
    et informe leur propriétaire.
    """

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:

        expired = conn.execute(
            """
            UPDATE subscriptions
            SET status = 'expired'
            WHERE status IN ('trial', 'active')
              AND expires_at IS NOT NULL
              AND expires_at <= NOW()
            RETURNING id, user_id, establishment_id
            """
        ).fetchall()

        suspended_establishments = 0
        notifications_created = 0

        for subscription_id, user_id, establishment_id in expired:

            if establishment_id is not None:

                owner = conn.execute(
                    """
                    SELECT owner_user_id
                    FROM establishments
                    WHERE id = %s
                    """,
                    (establishment_id,)
                ).fetchone()

                result = conn.execute(
                    """
                    UPDATE establishments
                    SET status = 'suspended'
                    WHERE id = %s
                      AND status = 'accepted'
                    """,
                    (establishment_id,)
                )

                suspended_establishments += result.rowcount

                if result.rowcount > 0 and owner:
                    owner_user_id = owner[0]

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
                            owner_user_id,
                            establishment_id,
                            "subscription_expired",
                            "Votre abonnement a expiré. Votre établissement est temporairement suspendu."
                        )
                    )

                    notifications_created += 1

        return {
            "expired_subscriptions": len(expired),
            "suspended_establishments": suspended_establishments,
            "notifications_created": notifications_created
        }
