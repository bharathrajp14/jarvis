# api/routes/devices.py — Device Management and Pairing Endpoints
from __future__ import annotations

import platform
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mobile.gateway import get_device_gateway
from mobile.session import get_mobile_session_manager

router = APIRouter(tags=["Devices"])


class PairDeviceRequest(BaseModel):
    pin: str
    device_id: str
    model_name: str
    public_key: str = ""


@router.get("/api/agent/devices")
async def list_agent_devices():
    """List connected desktop and paired Android mobile devices."""
    gateway = get_device_gateway()
    session_mgr = get_mobile_session_manager()

    devices = gateway.list_devices()
    active_ids = set(session_mgr.list_active_devices())

    out = []
    # Primary PC device
    out.append({
        "device_id": "pc_primary",
        "display_name": "Host PC Controller",
        "platform": platform.system().lower(),
        "trust_state": "trusted",
        "status": "online",
        "capabilities": ["desktop_control", "filesystem", "browser", "voice", "vision"]
    })
    for d in devices:
        item = d.to_dict()
        item["status"] = "online" if d.device_id in active_ids else "offline"
        out.append(item)
    return {"devices": out}


@router.post("/api/agent/devices/pair-token")
async def generate_device_pairing_token():
    """Generate a pairing PIN and QR token for Android Companion app."""
    gateway = get_device_gateway()
    return gateway.generate_pairing_token()


@router.post("/api/agent/devices/pair")
async def pair_android_device(req: PairDeviceRequest):
    """Complete device pairing with PIN and register Android device."""
    gateway = get_device_gateway()
    paired = gateway.complete_pairing(req.pin, req.device_id, req.model_name, req.public_key)
    if not paired:
        raise HTTPException(status_code=400, detail="Invalid or expired pairing PIN")
    return {"status": "success", "device": paired.to_dict()}
