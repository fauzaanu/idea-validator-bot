from pydantic import BaseModel


class ValueFormula(BaseModel):
    market_potential: str
    feasibility: str
    competitive_advantage: str
    risks: str
    recommendation: str
    next_steps: str
