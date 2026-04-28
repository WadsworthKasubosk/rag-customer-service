import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.models.llm import update_llm_config, test_connection, get_current_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/config", tags=["模型配置"])


class LLMConfigRequest(BaseModel):
    api_key: str = Field(min_length=1)
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"


class LLMConfigResponse(BaseModel):
    model: str
    base_url: str
    api_key_preview: str


@router.post("/save")
async def save_config(req: LLMConfigRequest):
    try:
        update_llm_config(req.api_key, req.base_url, req.model)
        preview = req.api_key[:7] + "****" + req.api_key[-4:]
        return {"message": "配置已保存", "api_key_preview": preview}
    except Exception as e:
        logger.error(f"保存配置异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current", response_model=LLMConfigResponse)
async def current_config():
    return get_current_config()


@router.post("/test")
async def test_llm_connection():
    try:
        return test_connection()
    except Exception as e:
        logger.error(f"连接测试异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
