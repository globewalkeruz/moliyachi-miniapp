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


class CategoryCreate(BaseModel):
    user_id: int
    name: str
    emoji: str = '🏷️'
    type: str = 'expense'  # 'expense' | 'income' | 'both'
    color: Optional[str] = None


class BudgetUpsert(BaseModel):
    user_id: int
    month: int
    year: int
    category: str
    limit_amount: float


class ScheduledPaymentCreate(BaseModel):
    user_id: int
    name: str
    amount: float
    category: str = ''
    is_recurring: bool = True
    due_day: Optional[int] = None
    due_date: Optional[str] = None
    recurrence_type: str = 'monthly'


class MarkPaidRequest(BaseModel):
    user_id: int
    month_key: str  # "YYYY-MM"
