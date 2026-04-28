import time
from langchain_openai import ChatOpenAI
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

_llm = None
_config = {
    "api_key": DEEPSEEK_API_KEY,
    "base_url": DEEPSEEK_BASE_URL,
    "model": DEEPSEEK_MODEL,
}


def get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=_config["model"],
            openai_api_key=_config["api_key"],
            openai_api_base=_config["base_url"],
            temperature=0.3,
            max_tokens=2048,
        )
    return _llm


def update_llm_config(api_key: str, base_url: str, model: str):
    global _llm, _config
    _config["api_key"] = api_key
    _config["base_url"] = base_url
    _config["model"] = model
    _llm = None  # 清除单例，下次调用时用新配置


def get_current_config() -> dict:
    key = _config["api_key"]
    preview = key[:7] + "****" + key[-4:] if len(key) > 11 else "未配置"
    return {
        "model": _config["model"],
        "base_url": _config["base_url"],
        "api_key_preview": preview,
    }


def test_connection() -> dict:
    """测试 LLM 连接，返回 token 用量和耗时"""
    llm = ChatOpenAI(
        model=_config["model"],
        openai_api_key=_config["api_key"],
        openai_api_base=_config["base_url"],
        temperature=0,
        max_tokens=10,
    )
    start = time.time()
    response = llm.invoke("你好")
    elapsed = round(time.time() - start, 2)

    token_usage = response.response_metadata.get("token_usage", {})
    return {
        "status": "success",
        "model": _config["model"],
        "base_url": _config["base_url"],
        "response": response.content,
        "elapsed_seconds": elapsed,
        "prompt_tokens": token_usage.get("prompt_tokens", 0),
        "completion_tokens": token_usage.get("completion_tokens", 0),
        "total_tokens": token_usage.get("total_tokens", 0),
    }
