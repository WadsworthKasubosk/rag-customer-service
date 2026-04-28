"""
运行时配置服务
优先级：运行时设置 > 环境变量（config.py）
"""
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

_runtime_config: dict = {
    "api_key": DEEPSEEK_API_KEY,
    "base_url": DEEPSEEK_BASE_URL,
    "model": DEEPSEEK_MODEL,
}


def get_config() -> dict:
    return dict(_runtime_config)


def update_config(api_key: str = None, base_url: str = None, model: str = None):
    """更新运行时配置，并重置 LLM 单例使新配置生效"""
    if api_key is not None:
        _runtime_config["api_key"] = api_key
    if base_url is not None:
        _runtime_config["base_url"] = base_url.rstrip("/")
    if model is not None:
        _runtime_config["model"] = model

    # 重置 LLM 单例，下次调用 get_llm() 时用新配置重建
    import app.models.llm as llm_module
    llm_module._llm = None
