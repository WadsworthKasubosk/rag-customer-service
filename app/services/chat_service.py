from app.core.rag_chain import rag_query
from app.services.history_service import add_message, format_history


def chat(session_id: str, question: str) -> dict:
    add_message(session_id, "user", question)
    chat_history = format_history(session_id, limit=5)
    result = rag_query(question, chat_history)
    add_message(session_id, "assistant", result["answer"])
    return result
