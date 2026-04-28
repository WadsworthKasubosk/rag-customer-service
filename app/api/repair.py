from __future__ import annotations

from typing import Optional

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.repair_service import create_ticket, get_ticket, update_status, list_tickets

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/repair", tags=["维修工单"])


class CreateTicketRequest(BaseModel):
    phone: str
    product: str
    issue: str


class UpdateStatusRequest(BaseModel):
    status: str


@router.post("/create")
async def api_create_ticket(req: CreateTicketRequest):
    ticket = create_ticket(req.phone, req.product, req.issue)
    return {"message": "工单已创建", "ticket": ticket}


@router.get("/list")
async def api_list_tickets(phone: Optional[str] = None):
    return {"tickets": list_tickets(phone)}


@router.get("/{ticket_id}")
async def api_get_ticket(ticket_id: str):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ticket


@router.put("/{ticket_id}/status")
async def api_update_status(ticket_id: str, req: UpdateStatusRequest):
    ticket = update_status(ticket_id, req.status)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    return {"message": "状态已更新", "ticket": ticket}
