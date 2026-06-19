from pydantic import BaseModel
from typing import Optional


class TransactionCreate(BaseModel):
    user_id: int
    amount: float
    type: str  # "income" or "expense"
    category: str
    description: Optional[str] = None


class AIAdviceRequest(BaseModel):
    user_id: int
    message: str
