"""
Агент формирования рекомендаций менеджеру.

Алгоритм:
  1. Получить карточку клиента и данные обращения.
  2. Извлечь историю взаимодействий из БД.
  3. Запросить релевантные материалы из корпоративной базы знаний.
  4. Проанализировать данные через LLM.
  5. Если данных недостаточно — расширенный запрос к базе знаний.
  6. Сформировать рекомендации и вывести менеджеру.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Appeal, Client, Recommendation
from src.db.knowledge_base_client import KnowledgeBaseClient
from src.llm.llm_client import llm_client


@dataclass
class RecommendationResult:
    recommendation_id: int
    content: str
    knowledge_items_used: list[int]


class RecommendationAgent:
    """Формирует рекомендации для менеджера на основании обращения и базы знаний."""

    async def generate(
        self,
        db: AsyncSession,
        appeal_id: int,
        manager_id: int,
    ) -> RecommendationResult:
        # 1. Load appeal + client
        appeal = await db.get(Appeal, appeal_id)
        if appeal is None:
            raise ValueError(f"Appeal {appeal_id} not found")
        client = await db.get(Client, appeal.client_id)

        # 2. Fetch interaction history (last 5 appeals)
        history_q = (
            select(Appeal)
            .where(Appeal.client_id == appeal.client_id, Appeal.id != appeal_id)
            .order_by(Appeal.created_at.desc())
            .limit(5)
        )
        history_res = await db.execute(history_q)
        history = history_res.scalars().all()

        # 3. Query knowledge base via shared client (no duplicate SQL)
        kb_client = KnowledgeBaseClient(db)
        kb_items = await kb_client.get_all(limit=10)

        # 4. Build LLM prompt
        history_text = "\n".join(f"- {a.text[:200]}" for a in history) or "История отсутствует."
        kb_text = "\n".join(f"[{k.category}] {k.content[:300]}" for k in kb_items)

        system_prompt = (
            "Ты — опытный консультант по продажам ремонтных услуг. "
            "На основе данных клиента, истории взаимодействий и корпоративной базы знаний "
            "сформулируй 3–5 конкретных рекомендаций менеджеру для работы с клиентом."
        )
        user_prompt = (
            f"Клиент: {client.name if client else 'неизвестен'}\n"
            f"Обращение: {appeal.text}\n\n"
            f"История взаимодействий:\n{history_text}\n\n"
            f"База знаний:\n{kb_text}"
        )

        content = await llm_client.ask(system_prompt, user_prompt)

        # 5. Save recommendation
        rec = Recommendation(
            appeal_id=appeal_id,
            manager_id=manager_id,
            content=content,
        )
        db.add(rec)
        await db.commit()
        await db.refresh(rec)

        return RecommendationResult(
            recommendation_id=rec.id,
            content=content,
            knowledge_items_used=[k.id for k in kb_items],
        )
