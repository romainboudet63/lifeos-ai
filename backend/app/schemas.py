from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# --- Auth ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Tasks ---
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class TaskOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    priority: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Habits ---
class HabitCreate(BaseModel):
    name: str
    category: Optional[str] = None
    target_frequency: int = 7


class HabitOut(BaseModel):
    id: str
    name: str
    category: Optional[str]
    target_frequency: int

    class Config:
        from_attributes = True


class HabitLogCreate(BaseModel):
    date: Optional[date] = None
    completed: bool = True
    note: Optional[str] = None


class HabitLogOut(BaseModel):
    id: str
    date: date
    completed: bool
    note: Optional[str]

    class Config:
        from_attributes = True


# --- Goals ---
class GoalCreate(BaseModel):
    title: str
    category: Optional[str] = None
    target_date: Optional[date] = None


class GoalOut(BaseModel):
    id: str
    title: str
    category: Optional[str]
    target_date: Optional[date]
    progress: float
    status: str

    class Config:
        from_attributes = True


# --- AI Chat ---
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    used_memories: List[str] = []


class ChatMessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class MemoryOut(BaseModel):
    id: str
    content: str
    category: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Rappels intelligents ---
class NudgeOut(BaseModel):
    key: str     # identifiant stable de la règle (sert à masquer un rappel)
    view: str    # écran à ouvrir : "tasks" | "habits"
    text: str
    warn: bool


# --- Calendar ---
class CalendarEventOut(BaseModel):
    id: str
    external_provider: Optional[str]
    title: str
    start_at: datetime
    end_at: datetime
    location: Optional[str]

    class Config:
        from_attributes = True


class CalendarEventCreate(BaseModel):
    title: str
    start_at: datetime
    end_at: datetime
    location: Optional[str] = None
    push_to_google: bool = True  # si un compte Google est connecté, y créer aussi l'événement


class ConnectionStatus(BaseModel):
    connected: bool
    provider: Optional[str] = None


# --- Workouts ---
class WorkoutOut(BaseModel):
    id: str
    external_id: Optional[str]
    type: Optional[str]
    duration_min: Optional[int]
    calories: Optional[int]
    performed_at: Optional[datetime]
    source: str

    class Config:
        from_attributes = True


# --- Workout programs (IA) ---
class WorkoutSession(BaseModel):
    day_label: str
    type: str
    duration_min: int
    description: str


class WorkoutWeek(BaseModel):
    week_number: int
    focus: str
    sessions: List[WorkoutSession]


class WorkoutProgramCreate(BaseModel):
    objective: str
    weeks: Optional[int] = None


class WorkoutProgramOut(BaseModel):
    id: str
    objective: str
    title: str
    source: str
    weeks: List[WorkoutWeek]
    created_at: datetime

    class Config:
        from_attributes = True


class WorkoutProgramSummary(BaseModel):
    """Version allégée pour la liste — sans le détail complet des semaines."""
    id: str
    objective: str
    title: str
    source: str
    week_count: int
    created_at: datetime


# --- Nutrition ---
class NutritionLogCreate(BaseModel):
    description: str
    calories: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None


class NutritionLogOut(BaseModel):
    id: str
    description: str
    calories: Optional[int]
    protein_g: Optional[float]
    carbs_g: Optional[float]
    fat_g: Optional[float]
    logged_at: datetime

    class Config:
        from_attributes = True


class NutritionDailySummary(BaseModel):
    date: date
    total_calories: int
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    entries: List[NutritionLogOut]


class NutritionEstimateRequest(BaseModel):
    description: str


class NutritionEstimateResponse(BaseModel):
    found: bool
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    matched_foods: List[str] = []
    source: str  # "ia" | "heuristique"


# --- Finance ---
class TransactionCreate(BaseModel):
    amount: float
    category: Optional[str] = None
    description: Optional[str] = None
    occurred_at: Optional[datetime] = None


class TransactionOut(BaseModel):
    id: str
    amount: float
    currency: str
    category: Optional[str]
    description: Optional[str]
    occurred_at: datetime

    class Config:
        from_attributes = True


class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float


class BudgetOut(BaseModel):
    id: str
    category: str
    monthly_limit: float

    class Config:
        from_attributes = True


class BudgetStatus(BaseModel):
    category: str
    monthly_limit: float
    spent_this_month: float
    percent_used: float
    over_budget: bool


class CategorySpending(BaseModel):
    category: str
    total: float
