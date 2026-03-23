import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.security import decrypt_password, encrypt_password
from app.models.ai_config import AiConfig as AiConfigModel
from app.services.ai_service import find_similar_saved_sqls

router = APIRouter(tags=["AI"])


def _extract_sql(content: str) -> str:
    text = content.strip()

    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    return text


class AiConfigPayload(BaseModel):
    provider: str
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    embedding_algorithm: Optional[str] = "local_hash"
    embedding_model: Optional[str] = None
    embedding_base_url: Optional[str] = None
    embedding_api_key: Optional[str] = None
    is_active: bool = True


class AiConfigResponse(BaseModel):
    id: int
    provider: str
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    embedding_algorithm: Optional[str] = "local_hash"
    embedding_model: Optional[str] = None
    embedding_base_url: Optional[str] = None
    is_active: bool = True
    has_api_key: bool = False
    has_embedding_api_key: bool = False


class GenerateRequest(BaseModel):
    datasource_id: int
    description: str


class GenerateResponse(BaseModel):
    sql: str
    matched_sql: Optional[dict] = None


def _to_response(config: AiConfigModel) -> AiConfigResponse:
    extra = config.extra_params or {}
    return AiConfigResponse(
        id=config.id,
        provider=config.provider,
        model_name=config.model_name,
        base_url=config.base_url,
        embedding_algorithm=extra.get("embedding_algorithm") or "local_hash",
        embedding_model=extra.get("embedding_model"),
        embedding_base_url=extra.get("embedding_base_url"),
        is_active=config.is_active,
        has_api_key=bool(config.api_key_encrypted),
        has_embedding_api_key=bool(extra.get("embedding_api_key_encrypted")),
    )


@router.get("/config", response_model=AiConfigResponse)
async def get_ai_config(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(AiConfigModel).where(AiConfigModel.is_active == True))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="No active AI configuration")
    return _to_response(config)


@router.put("/config", response_model=AiConfigResponse)
async def update_ai_config(payload: AiConfigPayload, db: AsyncSession = Depends(get_db_session)):
    await db.execute(update(AiConfigModel).values(is_active=False))

    result = await db.execute(select(AiConfigModel).where(AiConfigModel.provider == payload.provider))
    config = result.scalar_one_or_none()

    encrypted_key = encrypt_password(payload.api_key) if payload.api_key else None
    extra_params = {
        "embedding_algorithm": payload.embedding_algorithm or "local_hash",
        "embedding_model": payload.embedding_model,
        "embedding_base_url": payload.embedding_base_url,
    }
    if config and config.extra_params and config.extra_params.get("embedding_api_key_encrypted"):
        extra_params["embedding_api_key_encrypted"] = config.extra_params.get("embedding_api_key_encrypted")
    if payload.embedding_api_key:
        extra_params["embedding_api_key_encrypted"] = encrypt_password(payload.embedding_api_key)

    if config:
        config.model_name = payload.model_name
        config.base_url = payload.base_url
        config.is_active = payload.is_active
        config.extra_params = extra_params
        if encrypted_key:
            config.api_key_encrypted = encrypted_key
    else:
        config = AiConfigModel(
            provider=payload.provider,
            model_name=payload.model_name,
            base_url=payload.base_url,
            api_key_encrypted=encrypted_key,
            extra_params=extra_params,
            is_active=payload.is_active,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)
    return _to_response(config)


@router.post("/generate", response_model=GenerateResponse)
async def generate_sql(payload: GenerateRequest, db: AsyncSession = Depends(get_db_session)):
    import httpx

    result = await db.execute(select(AiConfigModel).where(AiConfigModel.is_active == True))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="No active AI configuration")

    if config.provider != "openai":
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {config.provider}")

    api_key = decrypt_password(config.api_key_encrypted) if config.api_key_encrypted else None

    base_url = (config.base_url or "https://api.openai.com/v1").rstrip("/")
    model = config.model_name or "gpt-4.1-mini"

    similar_sqls = await find_similar_saved_sqls(
        db=db,
        datasource_id=payload.datasource_id,
        description=payload.description,
        limit=3,
    )

    prompt_lines = [
        "You are a SQL assistant. Generate only SQL for the user's request.",
        "Do not add markdown fences, explanations, or comments.",
        "If reference SQL examples are provided, preserve the relevant table names, field names, and query structure where appropriate.",
        f"User request: {payload.description}",
    ]

    matched_sql = None
    if similar_sqls:
        reference_lines = ["Reference SQL examples:"]
        for index, item in enumerate(similar_sqls, start=1):
            reference_lines.extend(
                [
                    f"Example {index} Name: {item.name}",
                    f"Example {index} Comment: {item.comment or ''}",
                    f"Example {index} SQL:",
                    item.sql_text,
                ]
            )
        prompt_lines.extend(reference_lines)
        matched_sql = {
            "id": similar_sqls[0].id,
            "name": similar_sqls[0].name,
            "comment": similar_sqls[0].comment,
        }

    prompt = "\n".join(prompt_lines)

    try:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "Return only SQL."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            data = response.json()
            sql = _extract_sql(data["choices"][0]["message"]["content"])
            return GenerateResponse(sql=sql, matched_sql=matched_sql)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"AI request failed: {exc}") from exc
