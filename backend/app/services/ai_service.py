import hashlib
import logging
import math
import re
from typing import Iterable, List

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_password
from app.models.ai_config import AiConfig as AiConfigModel
from app.models.saved_sql import SavedSql as SavedSqlModel

EMBEDDING_DIMENSION = 1536
logger = logging.getLogger(__name__)


def build_saved_sql_embedding_text(
    name: str,
    sql_text: str,
    comment: str | None = None,
    tags: list[str] | None = None,
) -> str:
    parts = [name.strip()]
    if comment:
        parts.append(comment.strip())
    if tags:
        parts.append(" ".join(tag.strip() for tag in tags if tag and tag.strip()))
    parts.append(sql_text.strip())
    return "\n".join(part for part in parts if part)


def _tokenize(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    if not normalized:
        return []

    raw_tokens = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", normalized)
    tokens: list[str] = []

    for token in raw_tokens:
        tokens.append(token)
        if "_" in token:
            tokens.extend(part for part in token.split("_") if part)

        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            chars = list(token)
            tokens.extend(chars)
            for n in (2, 3):
                tokens.extend("".join(chars[i : i + n]) for i in range(len(chars) - n + 1))

    return tokens or [normalized]


def generate_embedding(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    tokens = _tokenize(text)

    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % EMBEDDING_DIMENSION
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        weight = 1.0 + min(len(token), 12) / 12.0
        vector[index] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector

    return [value / norm for value in vector]


def normalize_embedding_dimensions(values: list[float], dimension: int = EMBEDDING_DIMENSION) -> list[float]:
    if len(values) == dimension:
        return values

    if len(values) > dimension:
        normalized = values[:dimension]
    else:
        normalized = values + [0.0] * (dimension - len(values))

    norm = math.sqrt(sum(value * value for value in normalized))
    if norm == 0:
        return normalized
    return [value / norm for value in normalized]


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    left_values = list(left)
    right_values = list(right)
    if len(left_values) != len(right_values):
        return 0.0
    return sum(a * b for a, b in zip(left_values, right_values))


async def get_active_ai_config(db: AsyncSession) -> AiConfigModel | None:
    result = await db.execute(select(AiConfigModel).where(AiConfigModel.is_active == True))
    return result.scalar_one_or_none()


def get_embedding_settings(config: AiConfigModel | None) -> dict:
    extra = config.extra_params or {} if config else {}
    algorithm = extra.get("embedding_algorithm") or "local_hash"

    return {
        "algorithm": algorithm,
        "model": extra.get("embedding_model"),
        "base_url": extra.get("embedding_base_url") or config.base_url if config else None,
        "api_key": decrypt_password(config.api_key_encrypted) if config and config.api_key_encrypted else None,
        "embedding_api_key": decrypt_password(extra["embedding_api_key_encrypted"])
        if extra.get("embedding_api_key_encrypted")
        else None,
    }


async def generate_embedding_with_settings(text: str, settings: dict) -> list[float]:
    algorithm = settings.get("algorithm") or "local_hash"

    if algorithm == "local_hash":
        return generate_embedding(text)

    if algorithm != "openai_compatible":
        raise ValueError(f"Unsupported embedding algorithm: {algorithm}")

    base_url = (settings.get("base_url") or "").rstrip("/")
    model = settings.get("model")
    if not base_url:
        raise ValueError("Embedding base URL is required for openai_compatible")
    if not model:
        raise ValueError("Embedding model is required for openai_compatible")

    endpoint = base_url if base_url.endswith("/embeddings") else f"{base_url}/embeddings"
    headers = {"Content-Type": "application/json"}
    api_key = settings.get("embedding_api_key") or settings.get("api_key")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                endpoint,
                headers=headers,
                json={
                    "model": model,
                    "input": text,
                },
            )
            response.raise_for_status()
            data = response.json()
            return normalize_embedding_dimensions(list(data["data"][0]["embedding"]))
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning("Embedding generation failed, fallback to local_hash: %s", exc)
        return generate_embedding(text)


async def ensure_saved_sql_embedding(db: AsyncSession, saved_sql: SavedSqlModel, settings: dict | None = None) -> None:
    if saved_sql.embedding is not None:
        return

    saved_sql.embedding = await generate_embedding_with_settings(
        build_saved_sql_embedding_text(
            name=saved_sql.name,
            sql_text=saved_sql.sql_text,
            comment=saved_sql.comment,
            tags=saved_sql.tags or [],
        )
        ,
        settings or {"algorithm": "local_hash"},
    )


async def find_similar_saved_sqls(
    db: AsyncSession,
    datasource_id: int,
    description: str,
    limit: int = 3,
    threshold: float = 0.12,
) -> list[SavedSqlModel]:
    config = await get_active_ai_config(db)
    settings = get_embedding_settings(config)

    result = await db.execute(
        select(SavedSqlModel)
        .where(SavedSqlModel.datasource_id == datasource_id)
        .order_by(SavedSqlModel.updated_at.desc(), SavedSqlModel.id.desc())
    )
    saved_sqls = result.scalars().all()

    if not saved_sqls:
        return []

    updated = False
    for item in saved_sqls:
        if item.embedding is None:
            await ensure_saved_sql_embedding(db, item, settings)
            updated = True

    if updated:
        await db.commit()

    description_embedding = await generate_embedding_with_settings(description, settings)
    scored_items: list[tuple[float, SavedSqlModel]] = []

    for item in saved_sqls:
        if item.embedding is None:
            continue
        score = cosine_similarity(description_embedding, item.embedding)
        if score >= threshold:
            scored_items.append((score, item))

    scored_items.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in scored_items[:limit]]
