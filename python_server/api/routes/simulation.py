from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict
from services.simulation_svc import start_simulation_logic

router = APIRouter()

class SimulationRequest(BaseModel):
    project_path: str
    selection: Dict[str, int] = {}

@router.post("/simulation/start")
async def api_start_simulation(req: SimulationRequest):
    return start_simulation_logic(req.model_dump())
