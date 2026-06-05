"""
KnowledgeBaseClient — единая точка доступа к корпоративной базе знаний.

Рефакторинг:
- Вынесен отдельный метод search_by_category(category) вместо дублирующихся
  SELECT-запросов в RecommendationAgent и DealPredictionAgent.
- Все агенты теперь используют этот клиент — дублирование SQL устранено.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import KnowledgeBase


class KnowledgeBaseClient:
    """
    Клиент для работы с таблицей knowledge_base.

    Предоставляет переиспользуемые методы запросов, которые ранее
    дублировались в RecommendationAgent и DealPredictionAgent.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Public API ───────────────────────────────────────────────────────────

    async def search_by_category(
        self,
        category: str,
        limit: int = 10,
    ) -> list[KnowledgeBase]:
        """
        Вернуть записи базы знаний с указанной категорией.

        Заменяет дублирующиеся SELECT-запросы в:
          - RecommendationAgent.generate()
          - DealPredictionAgent.predict()
          - CommercialOfferAgent.generate()

        Parameters
        ----------
        category:
            Категория для фильтрации (например, 'price_list', 'offer_template',
            'learned_tips').
        limit:
            Максимальное количество возвращаемых записей.
        """
        q = (
            select(KnowledgeBase)
            .where(KnowledgeBase.category == category)
            .order_by(KnowledgeBase.updated_at.desc())
            .limit(limit)
        )
        result = await self._db.execute(q)
        return result.scalars().all()

    async def get_all(self, limit: int = 20) -> list[KnowledgeBase]:
        """Вернуть последние N записей базы знаний без фильтра по категории."""
        q = (
            select(KnowledgeBase)
            .order_by(KnowledgeBase.updated_at.desc())
            .limit(limit)
        )
        result = await self._db.execute(q)
        return result.scalars().all()

    async def get_price_list(self, limit: int = 10) -> list[KnowledgeBase]:
        """Удобный алиас для получения прайс-листа."""
        return await self.search_by_category("price_list", limit=limit)

    async def get_offer_templates(self, limit: int = 5) -> list[KnowledgeBase]:
        """Удобный алиас для получения шаблонов КП."""
        return await self.search_by_category("offer_template", limit=limit)

    async def get_learned_tips(self, limit: int = 10) -> list[KnowledgeBase]:
        """Удобный алиас для получения усвоенных советов из самообучения."""
        return await self.search_by_category("learned_tips", limit=limit)

    async def add_entry(
        self,
        category: str,
        content: str,
    ) -> KnowledgeBase:
        """Добавить новую запись в базу знаний и вернуть её."""
        from datetime import datetime

        entry = KnowledgeBase(
            category=category,
            content=content,
            updated_at=datetime.utcnow(),
        )
        self._db.add(entry)
        await self._db.flush()
        return entry
