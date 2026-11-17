import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, ForeignKey, Text, Integer, Float, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
    habits = relationship("Habit", back_populates="owner", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="owner", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="owner", cascade="all, delete-orphan")
    conversations = relationship("ChatMessage", back_populates="owner", cascade="all, delete-orphan")
    oauth_connections = relationship("OAuthConnection", back_populates="owner", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="owner", cascade="all, delete-orphan")
    workouts = relationship("Workout", back_populates="owner", cascade="all, delete-orphan")
    workout_programs = relationship("WorkoutProgram", back_populates="owner", cascade="all, delete-orphan")
    nutrition_logs = relationship("NutritionLog", back_populates="owner", cascade="all, delete-orphan")
    transactions = relationship("FinancialTransaction", back_populates="owner", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="owner", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    priority = Column(String, default="medium")  # low | medium | high
    status = Column(String, default="todo")       # todo | in_progress | done
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="tasks")


class Habit(Base):
    __tablename__ = "habits"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)  # sport | sommeil | nutrition | mental ...
    target_frequency = Column(Integer, default=7)  # fois / semaine
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="habits")
    logs = relationship("HabitLog", back_populates="habit", cascade="all, delete-orphan")


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    habit_id = Column(String, ForeignKey("habits.id"), nullable=False)
    date = Column(Date, default=date.today)
    completed = Column(Boolean, default=True)
    note = Column(Text, nullable=True)

    habit = relationship("Habit", back_populates="logs")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    category = Column(String, nullable=True)  # carriere | sport | finance | apprentissage ...
    target_date = Column(Date, nullable=True)
    progress = Column(Float, default=0.0)  # 0.0 - 1.0
    status = Column(String, default="active")  # active | done | abandoned
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="goals")
    milestones = relationship("GoalMilestone", back_populates="goal", cascade="all, delete-orphan")


class GoalMilestone(Base):
    __tablename__ = "goal_milestones"

    id = Column(String, primary_key=True, default=gen_uuid)
    goal_id = Column(String, ForeignKey("goals.id"), nullable=False)
    title = Column(String, nullable=False)
    target_date = Column(Date, nullable=True)
    done = Column(Boolean, default=False)

    goal = relationship("Goal", back_populates="milestones")


class Memory(Base):
    """Mémoire long-terme de l'IA pour un utilisateur (RAG)."""
    __tablename__ = "memories"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=True)  # preference | objectif | habitude | contexte
    embedding = Column(JSON, nullable=True)  # vecteur stocké en JSON (prototype); pgvector en prod
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="memories")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="conversations")


class OAuthConnection(Base):
    """Connexion à un service externe (Google Calendar, etc.). Un seul
    provider par utilisateur dans ce prototype (pas de multi-compte)."""
    __tablename__ = "oauth_connections"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    provider = Column(String, nullable=False)  # google_calendar
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="oauth_connections")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    external_provider = Column(String, nullable=True)  # google | null (natif)
    external_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="calendar_events")


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    external_id = Column(String, nullable=True)
    type = Column(String, nullable=True)  # course | musculation | yoga | cyclisme ...
    duration_min = Column(Integer, nullable=True)
    calories = Column(Integer, nullable=True)
    performed_at = Column(DateTime, nullable=True)
    source = Column(String, default="manuel")  # manuel | strava
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="workouts")


class WorkoutProgram(Base):
    __tablename__ = "workout_programs"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    objective = Column(Text, nullable=False)
    title = Column(String, nullable=False)
    source = Column(String, default="heuristique")  # ia | heuristique
    weeks_json = Column(JSON, nullable=False)  # liste de semaines (voir schemas.WorkoutWeek)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="workout_programs")


class NutritionLog(Base):
    __tablename__ = "nutrition_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=False)
    calories = Column(Integer, nullable=True)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    logged_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="nutrition_logs")


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)  # positif = dépense, dans ce prototype
    currency = Column(String, default="EUR")
    category = Column(String, nullable=True)
    description = Column(String, nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    category = Column(String, nullable=False)
    monthly_limit = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="budgets")
