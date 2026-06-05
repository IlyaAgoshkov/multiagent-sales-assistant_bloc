"""
Unit tests for DealPredictionAgent probability scoring.

Covers three scenarios:
  - High probability  (>70%)  → status "promising"
  - Medium probability (40–70%) → status "needs_work"
  - Low probability   (<40%)  → status "needs_work"
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_mock_db(appeal_text: str = "Хочу отремонтировать кухню", channel: str = "web"):
    """Return a mock AsyncSession pre-configured with a fake Appeal."""
    mock_db = AsyncMock()

    fake_appeal = MagicMock()
    fake_appeal.id = 42
    fake_appeal.text = appeal_text
    fake_appeal.source_channel = channel
    fake_appeal.client_id = 1

    # db.get(Appeal, 42) → fake_appeal
    mock_db.get = AsyncMock(return_value=fake_appeal)

    # db.execute(...) → empty similar deals (so base_rate = 50%)
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=empty_result)

    fake_deal = MagicMock()
    fake_deal.id = 99

    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda obj: None)

    return mock_db, fake_deal


# ── High probability (>70%) ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_high_probability_status_promising():
    """LLM returns probability=85 → status should be 'promising'."""
    from src.agents.prediction_agent import DealPredictionAgent, PROBABILITY_THRESHOLD

    agent = DealPredictionAgent()
    mock_db, fake_deal = _make_mock_db()

    llm_response = '{"probability": 85.0, "rationale": "Клиент чётко сформулировал запрос."}'

    with patch("src.agents.prediction_agent.llm_client") as mock_llm, \
         patch("src.agents.prediction_agent.Deal", return_value=fake_deal):
        mock_llm.ask = AsyncMock(return_value=llm_response)
        result = await agent.predict(db=mock_db, appeal_id=42)

    assert result.probability > PROBABILITY_THRESHOLD
    assert result.status == "promising"
    assert result.rationale != ""


@pytest.mark.asyncio
async def test_high_probability_exact_threshold():
    """Probability exactly at threshold (70.0) → 'promising'."""
    from src.agents.prediction_agent import DealPredictionAgent, PROBABILITY_THRESHOLD

    agent = DealPredictionAgent()
    mock_db, fake_deal = _make_mock_db()

    llm_response = '{"probability": 70.0, "rationale": "На границе."}'

    with patch("src.agents.prediction_agent.llm_client") as mock_llm, \
         patch("src.agents.prediction_agent.Deal", return_value=fake_deal):
        mock_llm.ask = AsyncMock(return_value=llm_response)
        result = await agent.predict(db=mock_db, appeal_id=42)

    assert result.probability >= PROBABILITY_THRESHOLD
    assert result.status == "promising"


# ── Medium probability (40–70%) ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_medium_probability_status_needs_work():
    """LLM returns probability=55 → status should be 'needs_work'."""
    from src.agents.prediction_agent import DealPredictionAgent

    agent = DealPredictionAgent()
    mock_db, fake_deal = _make_mock_db()

    llm_response = '{"probability": 55.0, "rationale": "Клиент неуверен в бюджете."}'

    with patch("src.agents.prediction_agent.llm_client") as mock_llm, \
         patch("src.agents.prediction_agent.Deal", return_value=fake_deal):
        mock_llm.ask = AsyncMock(return_value=llm_response)
        result = await agent.predict(db=mock_db, appeal_id=42)

    assert 40.0 <= result.probability < 70.0
    assert result.status == "needs_work"


@pytest.mark.asyncio
async def test_medium_probability_lower_bound():
    """Probability=40.0 → still 'needs_work'."""
    from src.agents.prediction_agent import DealPredictionAgent

    agent = DealPredictionAgent()
    mock_db, fake_deal = _make_mock_db()

    llm_response = '{"probability": 40.0, "rationale": "Слабый интерес."}'

    with patch("src.agents.prediction_agent.llm_client") as mock_llm, \
         patch("src.agents.prediction_agent.Deal", return_value=fake_deal):
        mock_llm.ask = AsyncMock(return_value=llm_response)
        result = await agent.predict(db=mock_db, appeal_id=42)

    assert result.probability == pytest.approx(40.0)
    assert result.status == "needs_work"


# ── Low probability (<40%) ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_low_probability_status_needs_work():
    """LLM returns probability=15 → status 'needs_work', probability recorded correctly."""
    from src.agents.prediction_agent import DealPredictionAgent

    agent = DealPredictionAgent()
    mock_db, fake_deal = _make_mock_db()

    llm_response = '{"probability": 15.0, "rationale": "Клиент скорее всего откажется."}'

    with patch("src.agents.prediction_agent.llm_client") as mock_llm, \
         patch("src.agents.prediction_agent.Deal", return_value=fake_deal):
        mock_llm.ask = AsyncMock(return_value=llm_response)
        result = await agent.predict(db=mock_db, appeal_id=42)

    assert result.probability < 40.0
    assert result.status == "needs_work"


@pytest.mark.asyncio
async def test_low_probability_zero():
    """Edge case: probability=0 → 'needs_work'."""
    from src.agents.prediction_agent import DealPredictionAgent

    agent = DealPredictionAgent()
    mock_db, fake_deal = _make_mock_db()

    llm_response = '{"probability": 0.0, "rationale": "Нет шансов."}'

    with patch("src.agents.prediction_agent.llm_client") as mock_llm, \
         patch("src.agents.prediction_agent.Deal", return_value=fake_deal):
        mock_llm.ask = AsyncMock(return_value=llm_response)
        result = await agent.predict(db=mock_db, appeal_id=42)

    assert result.probability == pytest.approx(0.0)
    assert result.status == "needs_work"


# ── Fallback: malformed LLM response ────────────────────────────────────────

@pytest.mark.asyncio
async def test_malformed_llm_response_uses_base_rate():
    """If LLM returns non-JSON, base_rate (50%) is used → 'needs_work'."""
    from src.agents.prediction_agent import DealPredictionAgent

    agent = DealPredictionAgent()
    mock_db, fake_deal = _make_mock_db()

    with patch("src.agents.prediction_agent.llm_client") as mock_llm, \
         patch("src.agents.prediction_agent.Deal", return_value=fake_deal):
        mock_llm.ask = AsyncMock(return_value="Не могу ответить в JSON формате.")
        result = await agent.predict(db=mock_db, appeal_id=42)

    # base_rate = 50% (no historical deals), below threshold
    assert result.probability == pytest.approx(50.0)
    assert result.status == "needs_work"
