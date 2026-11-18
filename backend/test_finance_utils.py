from app.finance_utils import BudgetCheck, compute_budget_status, compute_spending_by_category


def test_percent_used_computed_correctly():
    check = BudgetCheck(category="restaurant", monthly_limit=200, spent_this_month=150)
    assert check.percent_used == 75.0


def test_over_budget_true_when_spent_exceeds_limit():
    check = BudgetCheck(category="restaurant", monthly_limit=200, spent_this_month=250)
    assert check.over_budget is True
    assert check.percent_used == 125.0


def test_over_budget_false_when_under_limit():
    check = BudgetCheck(category="restaurant", monthly_limit=200, spent_this_month=100)
    assert check.over_budget is False


def test_over_budget_false_when_exactly_at_limit():
    check = BudgetCheck(category="loisirs", monthly_limit=100, spent_this_month=100)
    assert check.over_budget is False, "dépenser exactement le budget n'est pas un dépassement"


def test_handles_zero_limit_without_division_error():
    check = BudgetCheck(category="divers", monthly_limit=0, spent_this_month=50)
    assert check.percent_used == 0.0
    assert check.over_budget is True


def test_compute_budget_status_matches_spending_by_category():
    budgets = [
        {"category": "restaurant", "monthly_limit": 200},
        {"category": "transport", "monthly_limit": 80},
    ]
    spending = {"restaurant": 220.0, "transport": 30.0}
    results = compute_budget_status(budgets, spending)

    assert len(results) == 2
    restaurant = next(r for r in results if r.category == "restaurant")
    transport = next(r for r in results if r.category == "transport")
    assert restaurant.over_budget is True
    assert transport.over_budget is False


def test_compute_budget_status_zero_spending_when_no_transactions():
    budgets = [{"category": "sante", "monthly_limit": 50}]
    results = compute_budget_status(budgets, spending_by_category={})
    assert results[0].spent_this_month == 0.0
    assert results[0].percent_used == 0.0


def test_spending_by_category_sums_correctly():
    transactions = [
        {"category": "restaurant", "amount": 25.0},
        {"category": "restaurant", "amount": 15.5},
        {"category": "transport", "amount": 40.0},
    ]
    result = compute_spending_by_category(transactions)
    assert result[0] == {"category": "restaurant", "total": 40.5}
    assert result[1] == {"category": "transport", "total": 40.0}


def test_spending_by_category_sorted_descending():
    transactions = [
        {"category": "a", "amount": 10.0},
        {"category": "b", "amount": 100.0},
        {"category": "c", "amount": 50.0},
    ]
    result = compute_spending_by_category(transactions)
    assert [r["category"] for r in result] == ["b", "c", "a"]


def test_spending_by_category_groups_missing_category_as_autre():
    transactions = [{"category": None, "amount": 30.0}, {"category": "resto", "amount": 10.0}]
    result = compute_spending_by_category(transactions)
    categories = {r["category"] for r in result}
    assert "autre" in categories


def test_spending_by_category_empty_list():
    assert compute_spending_by_category([]) == []


if __name__ == "__main__":
    import sys
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"OK   {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} tests passés")
    sys.exit(1 if failed else 0)
