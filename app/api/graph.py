"""知识图谱 REST 接口"""

from fastapi import APIRouter
from app.core.knowledge_graph import graph_stats, get_subgraph_data

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/stats")
async def stats():
    return graph_stats()


@router.get("/subgraph")
async def subgraph():
    return get_subgraph_data()
