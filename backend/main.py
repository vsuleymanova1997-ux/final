from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from models import ChatRequest, ChatResponse
from team import DailyBudgetExceeded, MessageTooLong, Team

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="ECTC E-Board Assistant")
_team: Team | None = None


def get_team() -> Team:
    global _team
    if _team is None:
        _team = Team()
    return _team


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    session_id = req.session_id or uuid4().hex[:8]
    try:
        result = await get_team().answer(req.message)
    except MessageTooLong as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except DailyBudgetExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return ChatResponse(
        reply=result["reply"],
        agent="boss",
        session_id=session_id,
        cost_usd=result["cost_usd"],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        cache_hit=result["cache_hit"],
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
