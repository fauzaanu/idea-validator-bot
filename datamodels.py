from pydantic import BaseModel


class ValueFormula(BaseModel):
    dream_outcome: str
    likelihood_of_achievement: str
    time_delay: str
    effort_and_sacrifice: str
    conclusion: str
