import React, { useCallback, useState } from "react";
import { View, Text, FlatList, StyleSheet } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useTheme } from "../theme/useTheme";
import { typography, spacing, radius } from "../theme/typography";
import { financeApi } from "../api/endpoints";
import { BudgetStatus, Transaction, CategorySpending } from "../api/types";
import { Card } from "../components/Card";
import { Input } from "../components/Input";
import { Button } from "../components/Button";
import { SpendingDonut } from "../components/SpendingDonut";

export function FinanceScreen() {
  const { colors } = useTheme();
  const [budgets, setBudgets] = useState<BudgetStatus[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [spending, setSpending] = useState<CategorySpending[]>([]);
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    const [b, t, s] = await Promise.all([
      financeApi.budgetsStatus(),
      financeApi.listTransactions(),
      financeApi.spendingByCategory(),
    ]);
    setBudgets(b);
    setTransactions(t.slice(0, 10));
    setSpending(s);
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleAdd = async () => {
    const value = parseFloat(amount.replace(",", "."));
    if (!value || !category.trim()) return;
    setCreating(true);
    try {
      await financeApi.createTransaction(value, category.trim());
      setAmount("");
      setCategory("");
      await load();
    } finally {
      setCreating(false);
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={{ height: spacing.md }} />

      <Card style={styles.donutCard}>
        <SpendingDonut data={spending} />
      </Card>

      {budgets.length > 0 && (
        <View style={{ paddingHorizontal: spacing.lg, marginBottom: spacing.md }}>
          <Text style={[typography.subtitle, { color: colors.textPrimary, marginBottom: spacing.sm }]}>Budgets du mois</Text>
          {budgets.map((b) => (
            <Card key={b.category} style={styles.budgetCard}>
              <View style={{ flex: 1 }}>
                <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>{b.category}</Text>
                <Text style={[typography.caption, { color: b.over_budget ? colors.danger : colors.textSecondary }]}>
                  {b.spent_this_month.toFixed(0)}€ / {b.monthly_limit.toFixed(0)}€ ({b.percent_used}%)
                </Text>
              </View>
              <View style={styles.progressTrack}>
                <View
                  style={[
                    styles.progressFill,
                    {
                      width: `${Math.min(100, b.percent_used)}%`,
                      backgroundColor: b.over_budget ? colors.danger : colors.accent,
                    },
                  ]}
                />
              </View>
            </Card>
          ))}
        </View>
      )}

      <View style={styles.formRow}>
        <View style={{ flex: 1 }}>
          <Input value={amount} onChangeText={setAmount} placeholder="Montant (€)" keyboardType="decimal-pad" />
        </View>
        <View style={{ flex: 1, marginLeft: spacing.sm }}>
          <Input value={category} onChangeText={setCategory} placeholder="Catégorie" />
        </View>
      </View>
      <Button label="Ajouter la dépense" onPress={handleAdd} loading={creating} disabled={!amount || !category.trim()} style={{ marginHorizontal: spacing.lg }} />

      <FlatList
        data={transactions}
        keyExtractor={(t) => t.id}
        contentContainerStyle={{ padding: spacing.lg }}
        ListHeaderComponent={
          transactions.length > 0 ? (
            <Text style={[typography.subtitle, { color: colors.textPrimary, marginBottom: spacing.sm }]}>Dépenses récentes</Text>
          ) : null
        }
        renderItem={({ item }) => (
          <Card style={styles.txCard}>
            <View style={{ flex: 1 }}>
              <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>{item.category ?? "Sans catégorie"}</Text>
              {item.description && <Text style={[typography.caption, { color: colors.textSecondary }]}>{item.description}</Text>}
            </View>
            <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>{item.amount.toFixed(2)}€</Text>
          </Card>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  donutCard: { alignItems: "center", marginHorizontal: spacing.lg, marginBottom: spacing.md, paddingVertical: spacing.lg },
  budgetCard: { marginBottom: spacing.sm },
  progressTrack: { height: 6, borderRadius: radius.pill, backgroundColor: "#00000012", marginTop: spacing.xs, overflow: "hidden" },
  progressFill: { height: 6, borderRadius: radius.pill },
  formRow: { flexDirection: "row", paddingHorizontal: spacing.lg },
  txCard: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: spacing.sm },
});
