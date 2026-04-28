from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.history_service import add_feedback, get_feedback_stats, get_history

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/feedback", tags=["反馈与统计"])


class FeedbackRequest(BaseModel):
    session_id: str
    rating: int = Field(ge=1, le=5, description="1-5分")
    comment: str = ""
    resolved: Optional[bool] = None


@router.post("/submit")
async def submit_feedback(req: FeedbackRequest):
    try:
        add_feedback(req.session_id, req.rating, req.comment, req.resolved)
        return {"message": "反馈已提交"}
    except Exception as e:
        logger.error(f"提交反馈异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def feedback_stats():
    return get_feedback_stats()


@router.get("/history/{session_id}")
async def chat_history(session_id: str):
    return get_history(session_id)
