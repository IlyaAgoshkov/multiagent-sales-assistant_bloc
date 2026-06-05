"""Pydantic schemas for the FastAPI layer."""

from typing import Optional

from pydantic import BaseModel, Field


class AppealCreateRequest(BaseModel):
    client_name: str = Field(..., description="Имя клиента")
    contact_info: dict = Field(default_factory=dict, description="Контактные данные")
    source_channel: Optional[str] = Field(None, description="Канал обращения")
    appeal_text: str = Field(..., description="Текст обращения")
    manager_id: int = Field(1, description="ID менеджера")
    urgency_level: int = Field(2, description="Уровень срочности: 1 (низкий) – 3 (высокий)")


class AppealResponse(BaseModel):
    appeal_id: int
    client_id: int
    status: str


class CloseDealRequest(BaseModel):
    deal_id: int = Field(..., description="ID сделки для закрытия")
