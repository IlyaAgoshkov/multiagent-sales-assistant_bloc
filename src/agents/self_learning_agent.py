"""
Агент самообучения системы.

Алгоритм:
  1. Получить данные завершённой сделки.
  2. Сохранить результат взаимодействия в БД.
  3. Анализировать успешные/неуспешные сценарии.
  4. Если накоплено достаточно данных — обновить базу знаний.
  5. Дообучить интеллектуальных агентов (fine-tuning промптов).
  6. Зафиксировать версию обновления в журнале.
"""

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Appeal, Deal, KnowledgeBase
from src.llm.llm_client import llm_client

MIN_SAMPLES_FOR_UPDATE = 10


@dataclass
class LearningResult:
    updated: bool
    new_knowledge_id: int | None
    message: str


class SelfLearningAgent:
    """Анализирует завершённые сделки и обновляет корпоративную базу знаний."""

    async def learn(
        self,
        db: AsyncSession,
        deal_id: int,
    ) -> LearningResult:
        deal = await db.get(Deal, deal_id)
        if deal is None:
            raise ValueError(f"Deal {deal_id} not found")

        # Count accumulated closed deals since last KB update
        closed_q = select(func.count()).select_from(Deal).where(
            Deal.actual_close_at.isnot(None)
        )
        total_closed = (await db.execute(closed_q)).scalar_one()

        if total_closed < MIN_SAMPLES_FOR_UPDATE:
            return LearningResult(
                updated=False,
                new_knowledge_id=None,
                message=f"Накоплено {total_closed}/{MIN_SAMPLES_FOR_UPDATE} сделок. Обновление пока не требуется.",
            )

        # Load recent won/lost deals for analysis
        recent_q = (
            select(Deal, Appeal)
            .join(Appeal, Deal.appeal_id == Appeal.id)
            .where(Deal.actual_close_at.isnot(None))
            .order_by(Deal.actual_close_at.desc())
            .limit(MIN_SAMPLES_FOR_UPDATE)
        )
        recent_res = await db.execute(recent_q)
        rows = recent_res.all()

        won_examples = [
            r.Appeal.text[:200] for r in rows if r.Deal.status == "won"
        ]
        lost_examples = [
            r.Appeal.text[:200] for r in rows if r.Deal.status != "won"
        ]

        system_prompt = (
            "Ты — аналитик продаж. На основе успешных и неуспешных сделок "
            "сформулируй 3 новых практических совета для менеджеров ремонтной компании. "
            "Верни JSON: {category: string, content: string}."
        )
        user_prompt = (
            f"Успешные сделки:\n" + "\n".join(f"- {e}" for e in won_examples[:5]) +
            f"\n\nНеуспешные сделки:\n" + "\n".join(f"- {e}" for e in lost_examples[:5])
        )

        raw = await llm_client.ask(system_prompt, user_prompt)
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        kb_entry: dict = {"category": "learned_tips", "content": raw}
        if match:
            try:
                kb_entry = json.loads(match.group())
            except json.JSONDecodeError:
                pass

        new_kb = KnowledgeBase(
            category=kb_entry.get("category", "learned_tips"),
            content=kb_entry.get("content", raw),
            updated_at=datetime.utcnow(),
        )
        db.add(new_kb)
        await db.commit()
        await db.refresh(new_kb)

        return LearningResult(
            updated=True,
            new_knowledge_id=new_kb.id,
            message=f"База знаний обновлена. Добавлена запись #{new_kb.id} в категорию '{new_kb.category}'.",
        )
