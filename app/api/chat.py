import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.history_service import add_message, format_history
from app.core.rag_chain import rag_query_stream

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["问答"])


class ChatRequest(BaseModel):
    session_id: str = "default"
    question: str


@router.post("/stream")
async def stream_question(req: ChatRequest):
    add_message(req.session_id, "user", req.question)
    chat_history = format_history(req.session_id, limit=5)

    def generate():
        full_answer = ""
        try:
            for event in rag_query_stream(req.question, chat_history):
                if event["type"] == "done":
                    full_answer = event.get("answer", "")
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"流式问答异常: {e}", exc_info=True)
            err = {"type": "error", "content": f"服务异常：{str(e)}"}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"
        finally:
            if full_answer:
                add_message(req.session_id, "assistant", full_answer)

    return StreamingResponse(generate(), media_type="text/event-stream")
