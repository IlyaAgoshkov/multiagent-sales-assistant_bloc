"""
Агент обработки обращений клиента.

Алгоритм:
  1. Принять обращение (текст + канал связи).
  2. Сохранить/обновить данные клиента в таблице clients.
  3. Проанализировать обращение через LLM-агент.
  4. Если обращение не распознано — запросить уточнение.
  5. Сформировать карточку клиента в БД.
  6. Передать данные агенту рекомендаций.
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Appeal, Client
from src.llm.llm_client import llm_client


@dataclass
class AppealResult:
    appeal_id: int
    client_id: int
    recognized: bool
    intent: str
    urgency: str
    category: str
    clarification_needed: bool
    clarification_message: Optional[str] = None


class AppealAnalysisAgent:
    """Принимает и классифицирует обращение клиента."""

    async def process(
        self,
        db: AsyncSession,
        client_name: str,
        contact_info: dict,
        source_channel: str,
        appeal_text: str,
    ) -> AppealResult:
        # 1. Upsert client
        client = Client(
            name=client_name,
            contact_info=contact_info,
            source_channel=source_channel,
        )
        db.add(client)
        await db.flush()

        # 2. Classify appeal via LLM
        classification = await llm_client.classify(appeal_text)
        recognized: bool = classification.get("recognized", False)

        # 3. Create appeal record
        appeal = Appeal(
            client_id=client.id,
            text=appeal_text,
            status="new",
            source_channel=source_channel,
        )
        db.add(appeal)
        await db.flush()

        # 4. Generate clarification message if not recognized
        clarification_message: Optional[str] = None
        if not recognized:
            clarification_message = await llm_client.ask(
                system_prompt=(
                    "Ты — вежливый менеджер отдела продаж ремонтной компании. "
                    "Клиент прислал непонятное обращение. Напиши короткое уточняющее сообщение (1–2 предложения)."
                ),
                user_prompt=f"Обращение клиента: {appeal_text}",
            )

        await db.commit()
        await db.refresh(appeal)

        return AppealResult(
            appeal_id=appeal.id,
            client_id=client.id,
            recognized=recognized,
            intent=classification.get("intent", "unknown"),
            urgency=classification.get("urgency", "medium"),
            category=classification.get("category", "other"),
            clarification_needed=not recognized,
            clarification_message=clarification_message,
        )
