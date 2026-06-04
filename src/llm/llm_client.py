from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from src.config import settings


class LLMClient:
    """Thin wrapper around LangChain ChatOpenAI."""

    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.2,
        )

    async def ask(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = await self._llm.ainvoke(messages)
        return response.content

    async def classify(self, text: str) -> dict:
        """Classify a client appeal: intent, urgency, category."""
        system = (
            "Ты — аналитик CRM-системы ремонтной компании. "
            "Классифицируй обращение клиента и верни JSON с полями: "
            "intent (string), urgency (low|medium|high), category (string), recognized (bool)."
        )
        raw = await self.ask(system, text)
        import json, re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"intent": "unknown", "urgency": "medium", "category": "other", "recognized": False}


llm_client = LLMClient()
