"""Multilingual survey translation import/export and rendering helpers."""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Literal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.question import Question
from app.models.survey import Survey, SurveyPost
from app.models.translation import PostTranslation, QuestionTranslation, SurveyTranslation
from app.schemas.survey import CommentOut, PostOut, PublicSurveyOut, QuestionOut

DEFAULT_LANGUAGE_CODE = "en"
SUPPORTED_LANGUAGE_CODES = {"en", "zh", "zh-cn", "zh-tw", "ar"}
MORE_INFORMATION_LABEL = "More Information"

TranslationFormat = Literal["json", "csv"]

CSV_HEADERS = [
    "key",
    "entity_type",
    "entity_id",
    "parent_id",
    "field",
    "source",
    "language_code",
    "translation",
]


@dataclass(frozen=True)
class TranslationImportPlan:
    language_code: str
    survey_fields: dict[str, Any]
    post_fields_by_post_id: dict[int, dict[str, Any]]
    question_fields_by_question_id: dict[int, dict[str, Any]]
    imported_keys: list[str]


def validate_language_code(language_code: str | None) -> str:
    normalized = (language_code or "").strip().lower()
    if normalized not in SUPPORTED_LANGUAGE_CODES:
        allowed = ", ".join(sorted(SUPPORTED_LANGUAGE_CODES))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language code. Supported languages: {allowed}",
        )
    return normalized


def normalize_optional_language(language_code: str | None) -> str:
    if not language_code:
        return DEFAULT_LANGUAGE_CODE
    normalized = language_code.strip().lower()
    return normalized if normalized in SUPPORTED_LANGUAGE_CODES else DEFAULT_LANGUAGE_CODE


def get_translation_fields(translations: Iterable[Any], language_code: str) -> dict[str, Any]:
    for translation in translations or []:
        if (translation.language_code or "").lower() == language_code:
            return dict(translation.translated_fields or {})
    return {}


def translation_value(fields: dict[str, Any], field: str, default: Any = "") -> Any:
    value = fields.get(field, default)
    return default if value is None else value


def build_translation_export_payload(
    survey: Survey, language_code: str = "zh"
) -> dict[str, Any]:
    """Build a stable translation template for one target language."""
    language_code = validate_language_code(language_code)
    items = build_translation_items(survey, language_code)
    return {
        "survey_id": survey.id,
        "default_language": DEFAULT_LANGUAGE_CODE,
        "language_code": language_code,
        "supported_languages": sorted(SUPPORTED_LANGUAGE_CODES),
        "items": items,
    }


def build_translation_items(survey: Survey, language_code: str) -> list[dict[str, Any]]:
    survey_fields = get_translation_fields(getattr(survey, "translations", []), language_code)
    items: list[dict[str, Any]] = [
        translation_item(
            key="survey.title",
            entity_type="survey",
            entity_id=survey.id,
            parent_id=None,
            field="title",
            source=survey.title,
            language_code=language_code,
            translation=translation_value(survey_fields, "title"),
        ),
        translation_item(
            key="survey.description",
            entity_type="survey",
            entity_id=survey.id,
            parent_id=None,
            field="description",
            source=survey.description or "",
            language_code=language_code,
            translation=translation_value(survey_fields, "description"),
        ),
    ]

    for question in sorted(getattr(survey, "questions", []) or [], key=lambda item: item.order):
        items.extend(build_question_translation_items(question, survey.id, None, language_code))

    for post in sorted(getattr(survey, "posts", []) or [], key=lambda item: item.order):
        post_fields = get_translation_fields(getattr(post, "translations", []), language_code)
        display_title_source = post.display_title or post.fetched_title or ""
        items.extend(
            [
                translation_item(
                    key=f"post.{post.id}.display_title",
                    entity_type="post",
                    entity_id=post.id,
                    parent_id=survey.id,
                    field="display_title",
                    source=display_title_source,
                    language_code=language_code,
                    translation=translation_value(post_fields, "display_title"),
                ),
                translation_item(
                    key=f"post.{post.id}.fetched_description",
                    entity_type="post",
                    entity_id=post.id,
                    parent_id=survey.id,
                    field="fetched_description",
                    source=post.display_description or post.fetched_description or "",
                    language_code=language_code,
                    translation=translation_value(
                        post_fields,
                        "display_description",
                        translation_value(post_fields, "fetched_description"),
                    ),
                ),
                translation_item(
                    key=f"post.{post.id}.fetched_source",
                    entity_type="post",
                    entity_id=post.id,
                    parent_id=survey.id,
                    field="fetched_source",
                    source=post.source_label or post.fetched_source or "",
                    language_code=language_code,
                    translation=translation_value(
                        post_fields,
                        "source_label",
                        translation_value(post_fields, "fetched_source"),
                    ),
                ),
                translation_item(
                    key=f"post.{post.id}.more_info_label",
                    entity_type="post",
                    entity_id=post.id,
                    parent_id=survey.id,
                    field="more_info_label",
                    source=MORE_INFORMATION_LABEL,
                    language_code=language_code,
                    translation=translation_value(post_fields, "more_info_label"),
                ),
            ]
        )

        comment_fields = post_fields.get("comments", {}) or {}
        for comment in sorted(getattr(post, "comments", []) or [], key=lambda item: item.order):
            stored_comment_fields = comment_fields.get(str(comment.id), {}) or {}
            items.extend(
                [
                    translation_item(
                        key=f"post_comment.{comment.id}.author_name",
                        entity_type="post_comment",
                        entity_id=comment.id,
                        parent_id=post.id,
                        field="author_name",
                        source=comment.author_name,
                        language_code=language_code,
                        translation=translation_value(stored_comment_fields, "author_name"),
                    ),
                    translation_item(
                        key=f"post_comment.{comment.id}.text",
                        entity_type="post_comment",
                        entity_id=comment.id,
                        parent_id=post.id,
                        field="text",
                        source=comment.text,
                        language_code=language_code,
                        translation=translation_value(stored_comment_fields, "text"),
                    ),
                ]
            )

        for question in sorted(getattr(post, "questions", []) or [], key=lambda item: item.order):
            items.extend(build_question_translation_items(question, survey.id, post.id, language_code))
    return items


def build_question_translation_items(
    question: Question,
    survey_id: int,
    parent_id: int | None,
    language_code: str,
) -> list[dict[str, Any]]:
    question_fields = get_translation_fields(getattr(question, "translations", []), language_code)
    return [
        translation_item(
            key=f"question.{question.id}.text",
            entity_type="question",
            entity_id=question.id,
            parent_id=parent_id or survey_id,
            field="text",
            source=question.text,
            language_code=language_code,
            translation=translation_value(question_fields, "text"),
        ),
        translation_item(
            key=f"question.{question.id}.config",
            entity_type="question",
            entity_id=question.id,
            parent_id=parent_id or survey_id,
            field="config",
            source=question.config or {},
            language_code=language_code,
            translation=translation_value(question_fields, "config", {}),
        ),
    ]


def translation_item(
    *,
    key: str,
    entity_type: str,
    entity_id: int,
    parent_id: int | None,
    field: str,
    source: Any,
    language_code: str,
    translation: Any,
) -> dict[str, Any]:
    return {
        "key": key,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "parent_id": parent_id,
        "field": field,
        "source": source,
        "language_code": language_code,
        "translation": translation,
    }


def translation_payload_to_csv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_HEADERS)
    writer.writeheader()
    for item in payload["items"]:
        writer.writerow(
            {
                "key": item["key"],
                "entity_type": item["entity_type"],
                "entity_id": item["entity_id"],
                "parent_id": item["parent_id"] or "",
                "field": item["field"],
                "source": encode_csv_value(item["source"]),
                "language_code": item.get("language_code") or payload["language_code"],
                "translation": encode_csv_value(item.get("translation", "")),
            }
        )
    return output.getvalue()


def encode_csv_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return ""
    return str(value)


def decode_import_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return ""
    if stripped[0] in "[{":
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return value
    return value


def parse_translation_import(
    raw_payload: Any,
    *,
    payload_format: TranslationFormat,
    language_override: str | None = None,
) -> tuple[str, dict[str, Any]]:
    if payload_format == "csv":
        return parse_csv_translation_import(str(raw_payload), language_override=language_override)
    return parse_json_translation_import(raw_payload, language_override=language_override)


def parse_json_translation_import(
    payload: Any, *, language_override: str | None = None
) -> tuple[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Translation import must be a JSON object")

    language_code = validate_language_code(
        language_override
        or payload.get("language_code")
        or payload.get("language")
        or payload.get("target_language")
    )

    entries: dict[str, Any] = {}
    if isinstance(payload.get("translations"), dict):
        entries = {str(key): value for key, value in payload["translations"].items()}
    elif isinstance(payload.get("items"), list):
        for item in payload["items"]:
            if not isinstance(item, dict) or "key" not in item:
                raise HTTPException(status_code=400, detail="Every translation item needs a key")
            value = item.get("translation")
            if value in (None, "") and isinstance(item.get("translations"), dict):
                value = item["translations"].get(language_code)
            entries[str(item["key"])] = decode_import_value(value)
    else:
        raise HTTPException(
            status_code=400,
            detail="Translation JSON must include either items or translations",
        )

    return language_code, entries


def parse_csv_translation_import(
    csv_text: str, *, language_override: str | None = None
) -> tuple[str, dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames or "key" not in reader.fieldnames or "translation" not in reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="Translation CSV must include key and translation columns",
        )

    entries: dict[str, Any] = {}
    language_codes: set[str] = set()
    for row in reader:
        key = (row.get("key") or "").strip()
        if not key:
            continue
        row_language = (row.get("language_code") or language_override or "").strip()
        if row_language:
            language_codes.add(validate_language_code(row_language))
        entries[key] = decode_import_value(row.get("translation", ""))

    if language_override:
        language_code = validate_language_code(language_override)
    elif len(language_codes) == 1:
        language_code = next(iter(language_codes))
    else:
        raise HTTPException(
            status_code=400,
            detail="Translation CSV must contain exactly one language_code",
        )
    return language_code, entries


def validate_translation_import(
    survey: Survey,
    *,
    language_code: str,
    entries: dict[str, Any],
) -> TranslationImportPlan:
    language_code = validate_language_code(language_code)
    template_items = build_translation_items(survey, language_code)
    items_by_key = {item["key"]: item for item in template_items}

    unknown_keys = sorted(key for key in entries if key not in items_by_key)
    if unknown_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid translation keys: {', '.join(unknown_keys[:10])}",
        )

    missing_keys = [
        key
        for key, item in items_by_key.items()
        if requires_translation(item) and is_missing_translation(entries.get(key))
    ]
    if missing_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Missing translations: {', '.join(missing_keys[:10])}",
        )

    comment_to_post = {
        comment.id: post.id
        for post in getattr(survey, "posts", []) or []
        for comment in getattr(post, "comments", []) or []
    }
    survey_fields: dict[str, Any] = {}
    post_fields_by_post_id: dict[int, dict[str, Any]] = defaultdict(dict)
    question_fields_by_question_id: dict[int, dict[str, Any]] = defaultdict(dict)

    for key, item in items_by_key.items():
        if key not in entries:
            continue
        value = decode_import_value(entries[key])
        if is_missing_translation(value) and not requires_translation(item):
            continue

        entity_type = item["entity_type"]
        field = item["field"]
        entity_id = int(item["entity_id"])
        if entity_type == "survey":
            survey_fields[field] = value
        elif entity_type == "post":
            post_fields_by_post_id[entity_id][field] = value
        elif entity_type == "post_comment":
            post_id = comment_to_post[entity_id]
            comments = post_fields_by_post_id[post_id].setdefault("comments", {})
            comments.setdefault(str(entity_id), {})[field] = value
        elif entity_type == "question":
            question_fields_by_question_id[entity_id][field] = value

    return TranslationImportPlan(
        language_code=language_code,
        survey_fields=survey_fields,
        post_fields_by_post_id=dict(post_fields_by_post_id),
        question_fields_by_question_id=dict(question_fields_by_question_id),
        imported_keys=sorted(entries.keys()),
    )


def requires_translation(item: dict[str, Any]) -> bool:
    if item["field"] == "more_info_label":
        return True
    source = item.get("source")
    return source not in (None, "", [], {})


def is_missing_translation(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (dict, list)):
        return not value
    return False


def apply_translation_plan_to_models(
    survey: Survey, plan: TranslationImportPlan
) -> list[SurveyTranslation | PostTranslation | QuestionTranslation]:
    rows: list[SurveyTranslation | PostTranslation | QuestionTranslation] = []
    if plan.survey_fields:
        rows.append(
            upsert_translation_row(
                owner=survey,
                relationship_name="translations",
                model=SurveyTranslation,
                language_code=plan.language_code,
                fields=plan.survey_fields,
                ids={"survey_id": survey.id},
            )
        )

    posts_by_id = {post.id: post for post in getattr(survey, "posts", []) or []}
    for post_id, fields in plan.post_fields_by_post_id.items():
        post = posts_by_id[post_id]
        rows.append(
            upsert_translation_row(
                owner=post,
                relationship_name="translations",
                model=PostTranslation,
                language_code=plan.language_code,
                fields=fields,
                ids={"survey_id": survey.id, "post_id": post_id},
            )
        )

    questions_by_id = {
        question.id: question
        for post in getattr(survey, "posts", []) or []
        for question in getattr(post, "questions", []) or []
    }
    for question_id, fields in plan.question_fields_by_question_id.items():
        question = questions_by_id[question_id]
        rows.append(
            upsert_translation_row(
                owner=question,
                relationship_name="translations",
                model=QuestionTranslation,
                language_code=plan.language_code,
                fields=fields,
                ids={"survey_id": survey.id, "question_id": question_id},
            )
        )
    return rows


def upsert_translation_row(
    *,
    owner: Any,
    relationship_name: str,
    model: type[SurveyTranslation] | type[PostTranslation] | type[QuestionTranslation],
    language_code: str,
    fields: dict[str, Any],
    ids: dict[str, int],
) -> SurveyTranslation | PostTranslation | QuestionTranslation:
    translations = getattr(owner, relationship_name, None)
    if translations is None:
        translations = []
        setattr(owner, relationship_name, translations)

    row = next(
        (
            translation
            for translation in translations
            if (translation.language_code or "").lower() == language_code
        ),
        None,
    )
    if row is None:
        row = model(language_code=language_code, translated_fields={}, **ids)
        translations.append(row)

    row.translated_fields = deep_merge_dicts(dict(row.translated_fields or {}), fields)
    row.updated_at = datetime.utcnow()
    return row


def deep_merge_dicts(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


async def load_owned_survey_for_translations(
    db: AsyncSession, *, survey_id: int, researcher_id: int
) -> Survey:
    result = await db.execute(
        select(Survey)
        .options(*translation_load_options())
        .where(Survey.id == survey_id, Survey.researcher_id == researcher_id)
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return survey


def translation_load_options() -> tuple[Any, ...]:
    return (
        selectinload(Survey.translations),
        selectinload(Survey.questions).selectinload(Question.translations),
        selectinload(Survey.posts).selectinload(SurveyPost.translations),
        selectinload(Survey.posts).selectinload(SurveyPost.comments),
        selectinload(Survey.posts)
        .selectinload(SurveyPost.questions)
        .selectinload(Question.translations),
    )


async def import_translation_payload(
    db: AsyncSession,
    survey: Survey,
    raw_payload: Any,
    *,
    payload_format: TranslationFormat,
    language_override: str | None = None,
) -> dict[str, Any]:
    language_code, entries = parse_translation_import(
        raw_payload, payload_format=payload_format, language_override=language_override
    )
    plan = validate_translation_import(survey, language_code=language_code, entries=entries)
    rows = apply_translation_plan_to_models(survey, plan)
    for row in rows:
        db.add(row)
    await db.flush()
    return {
        "survey_id": survey.id,
        "language_code": plan.language_code,
        "imported_keys": plan.imported_keys,
        "translation_rows": len(rows),
    }


def apply_translations_to_public_survey(
    survey: Survey, language_code: str | None
) -> PublicSurveyOut:
    language_code = normalize_optional_language(language_code)
    if language_code == DEFAULT_LANGUAGE_CODE:
        return PublicSurveyOut(
            title=survey.title,
            description=survey.description,
            status=survey.status,
            language=language_code,
            fallback_language=DEFAULT_LANGUAGE_CODE,
        )

    fallbacks: list[str] = []
    fields = get_translation_fields(getattr(survey, "translations", []), language_code)
    title = translated_or_fallback(fields, "title", survey.title, fallbacks)
    description = translated_or_fallback(fields, "description", survey.description, fallbacks)
    return PublicSurveyOut(
        title=title,
        description=description,
        status=survey.status,
        language=language_code,
        fallback_language=DEFAULT_LANGUAGE_CODE,
        translation_fallbacks=fallbacks,
    )


def apply_translations_to_post(
    post: PostOut, source_post: SurveyPost, language_code: str | None
) -> PostOut:
    language_code = normalize_optional_language(language_code)
    if language_code == DEFAULT_LANGUAGE_CODE:
        post.language = language_code
        post.fallback_language = DEFAULT_LANGUAGE_CODE
        return post

    fallbacks: list[str] = []
    fields = get_translation_fields(getattr(source_post, "translations", []), language_code)
    post.display_title = translated_or_fallback(
        fields, "display_title", post.display_title or post.fetched_title, fallbacks
    )
    translated_description = translated_or_fallback(
        fields,
        "display_description" if fields.get("display_description") else "fetched_description",
        post.display_description or post.fetched_description,
        fallbacks,
    )
    post.display_description = translated_description
    post.fetched_description = translated_description
    translated_source = translated_or_fallback(
        fields,
        "source_label" if fields.get("source_label") else "fetched_source",
        post.source_label or post.fetched_source,
        fallbacks,
    )
    post.source_label = translated_source
    post.fetched_source = translated_source
    post.more_info_label = translated_or_fallback(
        fields, "more_info_label", MORE_INFORMATION_LABEL, fallbacks
    )

    comment_fields = fields.get("comments", {}) or {}
    translated_comments: list[CommentOut] = []
    for comment in post.comments:
        stored_comment = comment_fields.get(str(comment.id), {}) or {}
        comment_fallbacks: list[str] = []
        comment.author_name = translated_or_fallback(
            stored_comment, "author_name", comment.author_name, comment_fallbacks
        )
        comment.text = translated_or_fallback(stored_comment, "text", comment.text, comment_fallbacks)
        comment.language = language_code
        comment.fallback_language = DEFAULT_LANGUAGE_CODE
        comment.translation_fallbacks = comment_fallbacks
        translated_comments.append(comment)
    post.comments = translated_comments

    translated_questions: list[QuestionOut] = []
    source_questions = {question.id: question for question in getattr(source_post, "questions", []) or []}
    for question in post.questions:
        source_question = source_questions.get(question.id)
        translated_questions.append(apply_translations_to_question(question, source_question, language_code))
    post.questions = translated_questions
    post.language = language_code
    post.fallback_language = DEFAULT_LANGUAGE_CODE
    post.translation_fallbacks = fallbacks
    return post


def apply_translations_to_question(
    question: QuestionOut,
    source_question: Question | None,
    language_code: str | None,
) -> QuestionOut:
    language_code = normalize_optional_language(language_code)
    question.language = language_code
    question.fallback_language = DEFAULT_LANGUAGE_CODE
    if language_code == DEFAULT_LANGUAGE_CODE:
        return question

    question_fields = get_translation_fields(
        getattr(source_question, "translations", []) if source_question else [], language_code
    )
    question_fallbacks: list[str] = []
    question.text = translated_or_fallback(question_fields, "text", question.text, question_fallbacks)
    question.config = translated_or_fallback(
        question_fields, "config", question.config, question_fallbacks
    )
    question.translation_fallbacks = question_fallbacks
    return question


def translated_or_fallback(
    fields: dict[str, Any], field: str, fallback: Any, fallbacks: list[str]
) -> Any:
    value = fields.get(field)
    if value is None or value == "" or value == {}:
        fallbacks.append(field)
        return fallback
    return value
