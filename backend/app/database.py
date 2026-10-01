import os
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL n'est pas configurée")
    return psycopg.connect(DATABASE_URL)
