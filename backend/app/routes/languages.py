import os
import psycopg

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from translations.languages import (
    LANGUAGES,
    DEFAULT_LANGUAGE,
    is_supported_language
)
from translations.catalog import get_translations

router = APIRouter(
    prefix="/api/languages",
    tags=["Languages"]
)


def db():
    return psycopg.connect(os.environ["DATABASE_URL"])


@router.get("")
def get_languages():
    return {
        "default": DEFAULT_LANGUAGE,
        "languages": [
            {
                "code": code,
                "name": name
            }
            for code, name in LANGUAGES.items()
        ]
    }


@router.put("/me")
def change_language(
    language: str,
    current_user=Depends(get_current_user)
):
    if not is_supported_language(language):
        raise HTTPException(
            status_code=400,
            detail="Langue non prise en charge"
        )

    with db() as conn:
        conn.execute(
            """
            UPDATE users
            SET language = %s
            WHERE id = %s
            """,
            (language, current_user["id"])
        )

    return {
        "message": "Langue mise à jour",
        "language": language
    }


@router.get("/me/translations")
def my_translations(
    current_user=Depends(get_current_user)
):
    language = current_user["language"]

    return {
        "language": language,
        "translations": get_translations(language)
    }
