"""Basic smoke tests for agent logic (no real DB / LLM calls)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_appeal_agent_recognized():
    from src.agents.appeal_agent import AppealAnalysisAgent

    agent = AppealAnalysisAgent()
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    fake_client = MagicMock()
    fake_client.id = 1
    fake_appeal = MagicMock()
    fake_appeal.id = 10

    mock_db.add = MagicMock()

    with patch("src.agents.appeal_agent.llm_client") as mock_llm:
        mock_llm.classify = AsyncMock(
            return_value={
                "intent": "renovation_quote",
                "urgency": "high",
                "category": "repair",
                "recognized": True,
            }
        )

        # Patch DB objects created inside the method
        with patch("src.agents.appeal_agent.Client", return_value=fake_client), \
             patch("src.agents.appeal_agent.Appeal", return_value=fake_appeal):
            result = await agent.process(
                db=mock_db,
                client_name="Иванова М.А.",
                contact_info={"phone": "+7 918 123-45"},
                source_channel="web",
                appeal_text="Хочу узнать стоимость ремонта кухни 15м²",
            )

    assert result.recognized is True
    assert result.clarification_needed is False
    assert result.intent == "renovation_quote"


@pytest.mark.asyncio
async def test_appeal_agent_unrecognized():
    from src.agents.appeal_agent import AppealAnalysisAgent

    agent = AppealAnalysisAgent()
    mock_db = AsyncMock()
    fake_client = MagicMock()
    fake_client.id = 2
    fake_appeal = MagicMock()
    fake_appeal.id = 20

    with patch("src.agents.appeal_agent.llm_client") as mock_llm:
        mock_llm.classify = AsyncMock(
            return_value={
                "intent": "unknown",
                "urgency": "medium",
                "category": "other",
                "recognized": False,
            }
        )
        mock_llm.ask = AsyncMock(return_value="Уточните, пожалуйста, ваш запрос.")

        with patch("src.agents.appeal_agent.Client", return_value=fake_client), \
             patch("src.agents.appeal_agent.Appeal", return_value=fake_appeal):
            result = await agent.process(
                db=mock_db,
                client_name="Неизвестный",
                contact_info={},
                source_channel="email",
                appeal_text="????",
            )

    assert result.recognized is False
    assert result.clarification_needed is True
    assert result.clarification_message is not None
