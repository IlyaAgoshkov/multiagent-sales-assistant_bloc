from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.db import get_db
from src.orchestrator.orchestrator import orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Multiagent Sales Assistant",
    description="Саморазвивающийся интеллектуальный помощник для отдела продаж",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ──────────────────────────────────────────────────────────────────

class NewAppealRequest(BaseModel):
    client_name: str
    contact_info: dict = {}
    source_channel: str = "web"
    appeal_text: str
    manager_id: int = 1


class CloseDealRequest(BaseModel):
    deal_id: int


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/appeals", summary="Обработать новое обращение клиента")
async def process_appeal(
    body: NewAppealRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await orchestrator.handle_new_appeal(
            db=db,
            client_name=body.client_name,
            contact_info=body.contact_info,
            source_channel=body.source_channel,
            appeal_text=body.appeal_text,
            manager_id=body.manager_id,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/deals/close", summary="Закрыть сделку и запустить самообучение")
async def close_deal(
    body: CloseDealRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await orchestrator.close_deal_and_learn(db=db, deal_id=body.deal_id)
        return {
            "updated": result.updated,
            "new_knowledge_id": result.new_knowledge_id,
            "message": result.message,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
