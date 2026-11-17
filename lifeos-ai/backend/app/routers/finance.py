from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.finance_utils import compute_budget_status, compute_spending_by_category

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/transactions", response_model=List[schemas.TransactionOut])
def list_transactions(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    return (
        db.query(models.FinancialTransaction)
        .filter(models.FinancialTransaction.user_id == user.id)
        .order_by(models.FinancialTransaction.occurred_at.desc())
        .limit(200)
        .all()
    )


@router.post("/transactions", response_model=schemas.TransactionOut, status_code=201)
def create_transaction(
    payload: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    data = payload.model_dump()
    if data.get("occurred_at") is None:
        data.pop("occurred_at")
    tx = models.FinancialTransaction(user_id=user.id, **data)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.get("/budgets", response_model=List[schemas.BudgetOut])
def list_budgets(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Budget).filter(models.Budget.user_id == user.id).all()


@router.post("/budgets", response_model=schemas.BudgetOut, status_code=201)
def create_budget(
    payload: schemas.BudgetCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user),
):
    existing = (
        db.query(models.Budget)
        .filter(models.Budget.user_id == user.id, models.Budget.category == payload.category)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Un budget existe déjà pour la catégorie '{payload.category}'")

    budget = models.Budget(user_id=user.id, **payload.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("/spending-by-category", response_model=List[schemas.CategorySpending])
def spending_by_category(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    """Dépenses du mois en cours groupées par catégorie, triées par
    montant décroissant — alimente le graphique de répartition côté
    mobile. Contrairement à /budgets/status, inclut TOUTES les
    catégories (pas seulement celles avec un budget défini)."""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    transactions = (
        db.query(models.FinancialTransaction)
        .filter(
            models.FinancialTransaction.user_id == user.id,
            models.FinancialTransaction.occurred_at >= month_start,
        )
        .all()
    )

    result = compute_spending_by_category([{"category": tx.category, "amount": tx.amount} for tx in transactions])
    return [schemas.CategorySpending(**r) for r in result]


@router.get("/budgets/status", response_model=List[schemas.BudgetStatus])
def budgets_status(db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user)):
    budgets = db.query(models.Budget).filter(models.Budget.user_id == user.id).all()
    if not budgets:
        return []

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    transactions = (
        db.query(models.FinancialTransaction)
        .filter(
            models.FinancialTransaction.user_id == user.id,
            models.FinancialTransaction.occurred_at >= month_start,
        )
        .all()
    )

    spending_by_category: dict = {}
    for tx in transactions:
        if tx.category:
            spending_by_category[tx.category] = spending_by_category.get(tx.category, 0.0) + tx.amount

    checks = compute_budget_status(
        budgets=[{"category": b.category, "monthly_limit": b.monthly_limit} for b in budgets],
        spending_by_category=spending_by_category,
    )

    return [
        schemas.BudgetStatus(
            category=c.category,
            monthly_limit=c.monthly_limit,
            spent_this_month=c.spent_this_month,
            percent_used=c.percent_used,
            over_budget=c.over_budget,
        )
        for c in checks
    ]
