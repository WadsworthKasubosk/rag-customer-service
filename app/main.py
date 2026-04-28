import logging
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.api import chat, knowledge, feedback, config, repair, logistics, graph, db, demo
from app.store.seed import init_demo_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(title="RAG Customer Service (MySQL + Redis)", version="2.0.0")

app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(feedback.router)
app.include_router(config.router)
app.include_router(repair.router)
app.include_router(logistics.router)
app.include_router(graph.router)
app.include_router(db.router)
app.include_router(demo.router)


@app.on_event("startup")
async def startup_event():
    try:
        init_demo_data(reset_runtime=False)
    except Exception as exc:
        logging.getLogger(__name__).warning("Storage bootstrap skipped: %s", exc)


@app.get("/", response_class=HTMLResponse)
async def index():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health_check():
    return {"status": "ok", "storage": "mysql+redis"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
