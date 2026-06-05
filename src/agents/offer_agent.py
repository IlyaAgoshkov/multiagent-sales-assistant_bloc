"""
Агент подготовки коммерческого предложения (КП).

Алгоритм:
  1. Получить данные обращения и результаты анализа LLM.
  2. Выбрать шаблон КП из базы знаний.
  3. Извлечь прайс-лист на услуги из БД.
  4. Сгенерировать текст КП через LLM.
  5. Проверить корректность КП; при ошибках — повторная генерация.
  6. Сохранить КП в таблице commercial_offers.
  7. Отобразить КП менеджеру.
"""

import json
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Appeal, CommercialOffer
from src.db.knowledge_base_client import KnowledgeBaseClient
from src.llm.llm_client import llm_client

MAX_RETRIES = 2


@dataclass
class OfferResult:
    offer_id: int
    content: dict
    total_price: float
    status: str


class CommercialOfferAgent:
    """Автоматически формирует коммерческое предложение."""

    async def generate(
        self,
        db: AsyncSession,
        appeal_id: int,
    ) -> OfferResult:
        appeal = await db.get(Appeal, appeal_id)
        if appeal is None:
            raise ValueError(f"Appeal {appeal_id} not found")

        # Load price-list and template via shared KnowledgeBaseClient (no duplicate SQL)
        kb_client = KnowledgeBaseClient(db)
        price_items = await kb_client.get_price_list(limit=5)
        templates = await kb_client.get_offer_templates(limit=1)
        template_text = templates[0].content if templates else "Стандартный шаблон КП."

        price_text = "\n".join(f"- {p.content}" for p in price_items) or "Прайс-лист недоступен."

        system_prompt = (
            "Ты — менеджер по продажам ремонтной компании. "
            "Составь коммерческое предложение в формате JSON с полями: "
            "title (string), services (list of {name, price}), total (number), note (string). "
            "Используй только реальные услуги из прайс-листа."
        )
        user_prompt = (
            f"Обращение клиента: {appeal.text}\n\n"
            f"Шаблон: {template_text}\n\n"
            f"Прайс-лист:\n{price_text}"
        )

        offer_content: dict = {}
        total_price: float = 0.0

        for attempt in range(MAX_RETRIES + 1):
            raw = await llm_client.ask(system_prompt, user_prompt)
            import re
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    offer_content = json.loads(match.group())
                    total_price = float(offer_content.get("total", 0))
                    break
                except (json.JSONDecodeError, ValueError):
                    if attempt == MAX_RETRIES:
                        offer_content = {"raw": raw}

        offer = CommercialOffer(
            appeal_id=appeal_id,
            content=offer_content,
            total_price=total_price,
            status="ready",
        )
        db.add(offer)
        await db.commit()
        await db.refresh(offer)

        return OfferResult(
            offer_id=offer.id,
            content=offer_content,
            total_price=total_price,
            status=offer.status,
        )
