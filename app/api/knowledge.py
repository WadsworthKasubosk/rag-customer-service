import os
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.knowledge.loader import load_document
from app.knowledge.splitter import split_text
from app.core.vector_store import add_documents, delete_all, get_vector_store
from app.config import DOCS_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge", tags=["知识库管理"])


class UploadResponse(BaseModel):
    filename: str
    chunks_count: int
    message: str


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    try:
        os.makedirs(DOCS_DIR, exist_ok=True)
        safe_name = os.path.basename(file.filename)
        if not safe_name or safe_name.startswith('.'):
            raise ValueError("无效的文件名")
        file_path = os.path.join(DOCS_DIR, safe_name)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        text = load_document(file_path)
        if not text.strip():
            raise ValueError("文档内容为空，请检查文件")

        chunks = split_text(text)
        count = add_documents(chunks, metadata={"source": file.filename})

        return UploadResponse(
            filename=file.filename,
            chunks_count=count,
            message=f"成功导入 {count} 个文本块",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"文档上传异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.delete("/clear")
async def clear_knowledge_base():
    try:
        delete_all()
        return {"message": "知识库已清空"}
    except Exception as e:
        logger.error(f"清空知识库异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def knowledge_status():
    try:
        from app.config import MOCK_RETRIEVAL
        if MOCK_RETRIEVAL:
            from app.core.vector_store import _load_docs
            return {"status": "ready", "total_vectors": len(_load_docs())}
        vs = get_vector_store()
        if vs is None:
            return {"status": "empty", "total_vectors": 0}
        return {"status": "ready", "total_vectors": vs.index.ntotal}
    except Exception as e:
        logger.error(f"获取知识库状态异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
