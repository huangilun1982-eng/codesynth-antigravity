from fastapi import APIRouter
from services.simulation_svc import start_simulation_logic

router = APIRouter()

@router.post("/simulation/start")
async def api_start_simulation(data: dict):
    return start_simulation_logic(data)
