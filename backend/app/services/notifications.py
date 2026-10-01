import os
import psycopg

def db():
    return psycopg.connect(os.environ["DATABASE_URL"])

def create_notification(
    establishment_id: int,
    user_id: int | None,
    notification_type: str,
    message: str
):
    with db() as conn:
        conn.execute(
            """
            INSERT INTO notifications
            (user_id, establishment_id, type, message)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, establishment_id, notification_type, message)
        )
