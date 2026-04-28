from langchain_huggingface import HuggingFaceEmbeddings
from app.config import EMBEDDING_MODEL_NAME

_embeddings = None


def get_embeddings():
    """获取 Embedding 单例"""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings
