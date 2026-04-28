from fastapi import APIRouter

from app.store.seed import demo_status, init_demo_data


router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/init")
async def init_demo():
    data = init_demo_data(reset_runtime=True)
    return {
        "message": "Demo data initialized",
        **data,
    }


@router.get("/status")
async def status():
    return demo_status()
