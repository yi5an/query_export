from pydantic import BaseModel
from typing import Optional


class AiConfigBase(BaseModel):
    provider: str  # openai/claude/ollama
    api_key: str
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    extra_params: Optional[dict] = None


class AiConfigUpdate(BaseModel):
    is_active: Optional[bool] = None


class AiConfig(AiConfigBase):
    id: int
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True