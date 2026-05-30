"""Locale overhaul (#60): drop ar, split zh into zh-CN/zh-TW, add ja/ko/es.

Migrates existing data so legacy 'zh' and 'ar' values don't leave the app
broken after the supported-locales swap:

- surveys.supported_languages JSON: drop 'ar', map 'zh' -> 'zh-CN'.
  Append the new default set to any survey that is left with an empty list
  so participant start can still pick a valid language.
- surveys.default_language: 'zh' -> 'zh-CN', 'ar' -> 'en'.
- survey_responses.language: 'zh' -> 'zh-CN', 'ar' -> 'en' (preserves the
  row; the user just picked a now-unsupported locale).
- {survey,post,question}_translations.language_code: 'zh' -> 'zh-CN'.
  'ar' rows are deleted (Arabic translations no longer reachable from the UI).

Revision ID: 20260531_0001
Revises: 20260529_0001
Create Date: 2026-05-31 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260531_0001"
down_revision: str | None = "20260529_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TRANSLATION_TABLES = ("survey_translations", "post_translations", "question_translations")
NEW_DEFAULT_LANGUAGES = ["en", "zh-CN", "zh-TW", "ja", "ko", "es"]


def _table_exists(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()

    if _table_exists("surveys"):
        # Migrate the JSON array column in PostgreSQL. We filter out 'ar' and
        # map 'zh' -> 'zh-CN' via jsonb_array_elements_text + jsonb_agg.
        bind.execute(
            sa.text(
                """
                UPDATE surveys SET supported_languages = (
                    SELECT COALESCE(
                        jsonb_agg(DISTINCT
                            CASE element WHEN 'zh' THEN 'zh-CN' ELSE element END
                        ) FILTER (WHERE element <> 'ar'),
                        '[]'::jsonb
                    )::json
                    FROM jsonb_array_elements_text(supported_languages::jsonb) AS element
                )
                WHERE supported_languages IS NOT NULL
                """
            )
        )
        # Any survey left with an empty supported_languages (e.g. it had only
        # ['ar']) gets the new default set so participant start works.
        bind.execute(
            sa.text(
                """
                UPDATE surveys SET supported_languages = CAST(:defaults AS json)
                WHERE supported_languages IS NULL OR supported_languages::text IN ('[]', 'null')
                """
            ),
            {"defaults": '["en", "zh-CN", "zh-TW", "ja", "ko", "es"]'},
        )
        bind.execute(
            sa.text("UPDATE surveys SET default_language = 'zh-CN' WHERE default_language = 'zh'")
        )
        bind.execute(
            sa.text("UPDATE surveys SET default_language = 'en' WHERE default_language = 'ar'")
        )

    if _table_exists("survey_responses"):
        bind.execute(
            sa.text("UPDATE survey_responses SET language = 'zh-CN' WHERE language = 'zh'")
        )
        bind.execute(sa.text("UPDATE survey_responses SET language = 'en' WHERE language = 'ar'"))

    for tbl in TRANSLATION_TABLES:
        if not _table_exists(tbl):
            continue
        bind.execute(
            sa.text(f"UPDATE {tbl} SET language_code = 'zh-CN' WHERE language_code = 'zh'")
        )
        bind.execute(sa.text(f"DELETE FROM {tbl} WHERE language_code = 'ar'"))


def downgrade() -> None:
    bind = op.get_bind()

    if _table_exists("surveys"):
        # Best-effort reversal: map zh-CN back to zh and append ar to
        # supported_languages so the old defaults reappear. zh-TW / ja / ko /
        # es rows have no legacy equivalent so they remain (they were never
        # there pre-#60 so a true reverse is not possible without loss).
        bind.execute(
            sa.text(
                """
                UPDATE surveys SET supported_languages = (
                    SELECT jsonb_agg(DISTINCT
                        CASE element WHEN 'zh-CN' THEN 'zh' ELSE element END
                    )::json
                    FROM jsonb_array_elements_text(supported_languages::jsonb) AS element
                )
                WHERE supported_languages IS NOT NULL
                """
            )
        )
        bind.execute(
            sa.text("UPDATE surveys SET default_language = 'zh' WHERE default_language = 'zh-CN'")
        )

    if _table_exists("survey_responses"):
        bind.execute(
            sa.text("UPDATE survey_responses SET language = 'zh' WHERE language = 'zh-CN'")
        )

    for tbl in TRANSLATION_TABLES:
        if not _table_exists(tbl):
            continue
        bind.execute(
            sa.text(f"UPDATE {tbl} SET language_code = 'zh' WHERE language_code = 'zh-CN'")
        )
