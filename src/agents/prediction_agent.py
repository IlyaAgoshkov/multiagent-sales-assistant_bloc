"""
Агент прогнозирования вероятности заключения сделки.

Алгоритм:
  1. Получить данные клиента и текущего обращения.
  2. Извлечь историю аналогичных сделок из БД.
  3. Вычислить признаки: канал, бюджет, стадия.
  4. Рассчитать вероятность заключения сделки.
  5. Если вероятность >= 70% — присвоить статус «Перспективный».
  6. Иначе — «Требует проработки».
  7. Сохранить прогноз в таблице deals.
  8. Отобразить прогноз менеджеру.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Appeal, Deal
from src.llm.llm_client import llm_client

PROBABILITY_THRESHOLD = 70.0


@dataclass
class PredictionResult:
    deal_id: int
    probability: float
    status: str
    rationale: str


class DealPredictionAgent:
    """Оценивает вероятность успешного завершения сделки."""

    async def predict(
        self,
        db: AsyncSession,
        appeal_id: int,
    ) -> PredictionResult:
        appeal = await db.get(Appeal, appeal_id)
        if appeal is None:
            raise ValueError(f"Appeal {appeal_id} not found")

        # Fetch similar closed deals (same channel)
        similar_q = (
            select(Deal)
            .join(Appeal, Deal.appeal_id == Appeal.id)
            .where(
                Appeal.source_channel == appeal.source_channel,
                Deal.actual_close_at.isnot(None),
            )
            .order_by(Deal.created_at.desc())
            .limit(20)
        )
        similar_res = await db.execute(similar_q)
        similar_deals = similar_res.scalars().all()

        won = sum(1 for d in similar_deals if d.status == "won")
        base_rate = (won / len(similar_deals) * 100) if similar_deals else 50.0

        # Ask LLM for refined estimate
        system_prompt = (
            "Ты — аналитик продаж ремонтной компании. "
            "На основе обращения клиента и базовой конверсии по каналу "
            "оцени вероятность (0–100) заключения сделки. "
            "Верни JSON: {probability: float, rationale: string}."
        )
        user_prompt = (
            f"Обращение: {appeal.text}\n"
            f"Канал: {appeal.source_channel}\n"
            f"Базовая конверсия по каналу: {base_rate:.1f}%"
        )

        import json, re
        raw = await llm_client.ask(system_prompt, user_prompt)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        probability = base_rate
        rationale = ""
        if match:
            try:
                data = json.loads(match.group())
                probability = float(data.get("probability", base_rate))
                rationale = data.get("rationale", "")
            except (json.JSONDecodeError, ValueError):
                pass

        status = "promising" if probability >= PROBABILITY_THRESHOLD else "needs_work"

        deal = Deal(
            appeal_id=appeal_id,
            probability=round(probability, 2),
            status=status,
        )
        db.add(deal)
        await db.commit()
        await db.refresh(deal)

        return PredictionResult(
            deal_id=deal.id,
            probability=probability,
            status=status,
            rationale=rationale,
        )
