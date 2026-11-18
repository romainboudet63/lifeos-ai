import httpx

BASE = "http://localhost:8000"
c = httpx.Client(base_url=BASE, timeout=10)
results = []


def check(name, resp, expected_status):
    ok = resp.status_code == expected_status
    results.append((name, ok))
    print(f"{'OK ' if ok else 'FAIL'} [{resp.status_code}] {name}")
    if not ok:
        print("   ->", resp.text[:300])
    return resp


r = check("register", c.post("/auth/register", json={
    "email": "nutrifin@example.com", "password": "azerty123"
}), 201)
r = check("login", c.post("/auth/login", data={
    "username": "nutrifin@example.com", "password": "azerty123"
}), 200)
headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

# --- Nutrition ---
check("log petit-déjeuner", c.post("/nutrition", json={
    "description": "Porridge avoine + banane", "calories": 350, "protein_g": 12, "carbs_g": 55, "fat_g": 8
}, headers=headers), 201)
check("log déjeuner", c.post("/nutrition", json={
    "description": "Poulet riz légumes", "calories": 650, "protein_g": 45, "carbs_g": 70, "fat_g": 15
}, headers=headers), 201)
check("list nutrition logs", c.get("/nutrition", headers=headers), 200)

r = check("résumé du jour", c.get("/nutrition/daily", headers=headers), 200)
summary = r.json()
assert summary["total_calories"] == 1000, f"attendu 1000 kcal, obtenu {summary['total_calories']}"
assert summary["total_protein_g"] == 57, f"attendu 57g protéines, obtenu {summary['total_protein_g']}"
print(f"   -> total calories = {summary['total_calories']} (correct), protéines = {summary['total_protein_g']}g (correct)")

# --- Finance ---
check("créer budget restaurant", c.post("/finance/budgets", json={
    "category": "restaurant", "monthly_limit": 200
}, headers=headers), 201)
check("budget dupliqué (doit échouer)", c.post("/finance/budgets", json={
    "category": "restaurant", "monthly_limit": 300
}, headers=headers), 400)

from datetime import datetime, timezone
now_iso = datetime.now(timezone.utc).isoformat()
check("transaction 1", c.post("/finance/transactions", json={
    "amount": 45.5, "category": "restaurant", "description": "Dîner", "occurred_at": now_iso
}, headers=headers), 201)
check("transaction 2", c.post("/finance/transactions", json={
    "amount": 180.0, "category": "restaurant", "description": "Anniversaire", "occurred_at": now_iso
}, headers=headers), 201)
check("transaction hors budget suivi", c.post("/finance/transactions", json={
    "amount": 30.0, "category": "transport", "occurred_at": now_iso
}, headers=headers), 201)

check("list transactions", c.get("/finance/transactions", headers=headers), 200)

r = check("statut budgets (doit détecter le dépassement restaurant)", c.get("/finance/budgets/status", headers=headers), 200)
status = r.json()
restaurant = next(s for s in status if s["category"] == "restaurant")
assert restaurant["over_budget"] is True, "225.5€ dépensés sur 200€ de budget doit être détecté en dépassement"
assert restaurant["spent_this_month"] == 225.5
print(f"   -> restaurant : {restaurant['spent_this_month']}€/{restaurant['monthly_limit']}€ ({restaurant['percent_used']}%) — dépassement détecté correctement")

print("\n" + "=" * 50)
passed = sum(1 for _, ok in results if ok)
print(f"RÉSULTAT: {passed}/{len(results)} tests passés")
