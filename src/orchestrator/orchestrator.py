"""
AgentOrchestrator — координирует выполнение агентов в рамках одного обращения.

Порядок выполнения:
  AppealAnalysisAgent → RecommendationAgent + DealPredictionAgent → CommercialOfferAgent
  По завершении сделки: SelfLearningAgent
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.appeal_agent import AppealAnalysisAgent, AppealResult
from src.agents.offer_agent import CommercialOfferAgent, OfferResult
from src.agents.prediction_agent import DealPredictionAgent, PredictionResult
from src.agents.recommendation_agent import RecommendationAgent, RecommendationResult
from src.agents.self_learning_agent import SelfLearningAgent, LearningResult


class AgentOrchestrator:
    """Координирует агентов и управляет контекстом обращения."""

    def __init__(self) -> None:
        self.appeal_agent = AppealAnalysisAgent()
        self.recommendation_agent = RecommendationAgent()
        self.offer_agent = CommercialOfferAgent()
        self.prediction_agent = DealPredictionAgent()
        self.self_learning_agent = SelfLearningAgent()

    async def handle_new_appeal(
        self,
        db: AsyncSession,
        client_name: str,
        contact_info: dict,
        source_channel: str,
        appeal_text: str,
        manager_id: int,
    ) -> dict:
        """Full pipeline for a new client appeal."""
        # Step 1: Analyse appeal
        appeal_result: AppealResult = await self.appeal_agent.process(
            db, client_name, contact_info, source_channel, appeal_text
        )

        if appeal_result.clarification_needed:
            return {
                "status": "clarification_needed",
                "appeal_id": appeal_result.appeal_id,
                "message": appeal_result.clarification_message,
            }

        # Steps 2+3: Recommendations & Prediction (independent — could be parallelised)
        rec_result: RecommendationResult = await self.recommendation_agent.generate(
            db, appeal_result.appeal_id, manager_id
        )
        pred_result: PredictionResult = await self.prediction_agent.predict(
            db, appeal_result.appeal_id
        )

        # Step 4: Commercial offer
        offer_result: OfferResult = await self.offer_agent.generate(
            db, appeal_result.appeal_id
        )

        return {
            "status": "processed",
            "appeal_id": appeal_result.appeal_id,
            "client_id": appeal_result.client_id,
            "recommendation": {
                "id": rec_result.recommendation_id,
                "content": rec_result.content,
            },
            "deal": {
                "id": pred_result.deal_id,
                "probability": pred_result.probability,
                "status": pred_result.status,
            },
            "offer": {
                "id": offer_result.offer_id,
                "total_price": offer_result.total_price,
                "status": offer_result.status,
            },
        }

    async def close_deal_and_learn(
        self,
        db: AsyncSession,
        deal_id: int,
    ) -> LearningResult:
        """Trigger self-learning after a deal is closed."""
        return await self.self_learning_agent.learn(db, deal_id)


orchestrator = AgentOrchestrator()
