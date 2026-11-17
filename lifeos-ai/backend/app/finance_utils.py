"""Calculs liés aux finances personnelles. Logique séparée du router
pour être testable sans base de données (voir test_finance_utils.py)."""
from dataclasses import dataclass
from typing import List


@dataclass
class BudgetCheck:
    category: str
    monthly_limit: float
    spent_this_month: float

    @property
    def percent_used(self) -> float:
        if self.monthly_limit <= 0:
            return 0.0
        return round((self.spent_this_month / self.monthly_limit) * 100, 1)

    @property
    def over_budget(self) -> bool:
        return self.spent_this_month > self.monthly_limit


def compute_budget_status(budgets: List[dict], spending_by_category: dict) -> List[BudgetCheck]:
    """budgets: [{"category": "restaurant", "monthly_limit": 200}, ...]
    spending_by_category: {"restaurant": 150.0, ...} (dépenses du mois en cours)
    """
    return [
        BudgetCheck(
            category=b["category"],
            monthly_limit=b["monthly_limit"],
            spent_this_month=spending_by_category.get(b["category"], 0.0),
        )
        for b in budgets
    ]


def compute_spending_by_category(transactions: List[dict]) -> List[dict]:
    """transactions: [{"category": "restaurant", "amount": 25.5}, ...]
    Additionne les montants par catégorie et trie du plus dépensé au
    moins dépensé. Les transactions sans catégorie sont regroupées
    sous "autre". Renvoie une liste (pas un dict) pour préserver l'ordre
    de tri côté client sans dépendre de l'ordre d'insertion d'un dict.
    """
    totals: dict = {}
    for tx in transactions:
        category = tx.get("category") or "autre"
        totals[category] = totals.get(category, 0.0) + tx["amount"]

    return [
        {"category": category, "total": round(total, 2)}
        for category, total in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]
