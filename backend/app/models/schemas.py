from pydantic import BaseModel, Field

class SimulationRequest(BaseModel):
    raceLaps: int = Field(default=57, ge=10, le=100)
    basePace: float = Field(default=92.0, gt=50, lt=180)
    degradationPerLap: float = Field(default=0.04, ge=0, le=2)
    pitLoss: float = Field(default=22.0, ge=0, le=60)
    stops: list[int] = Field(default=[20, 40])
    iterations: int = Field(default=3000, ge=500, le=20000)
