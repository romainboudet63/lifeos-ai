import React, { useCallback, useState } from "react";
import { View, Text, FlatList, StyleSheet } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useTheme } from "../theme/useTheme";
import { typography, spacing, radius } from "../theme/typography";
import { nutritionApi } from "../api/endpoints";
import { NutritionLog, NutritionDailySummary } from "../api/types";
import { Card } from "../components/Card";
import { Input } from "../components/Input";
import { Button } from "../components/Button";
import { showMessage } from "../utils/dialogs";

export function NutritionScreen() {
  const { colors } = useTheme();
  const [summary, setSummary] = useState<NutritionDailySummary | null>(null);
  const [description, setDescription] = useState("");
  const [calories, setCalories] = useState("");
  const [protein, setProtein] = useState("");
  const [carbs, setCarbs] = useState("");
  const [fat, setFat] = useState("");
  const [creating, setCreating] = useState(false);
  const [estimating, setEstimating] = useState(false);
  const [estimateNote, setEstimateNote] = useState<string | null>(null);

  const load = useCallback(async () => {
    setSummary(await nutritionApi.daily());
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleEstimate = async () => {
    if (!description.trim()) return;
    setEstimating(true);
    setEstimateNote(null);
    try {
      const result = await nutritionApi.estimate(description.trim());
      if (!result.found) {
        setEstimateNote("Aucun aliment reconnu — renseigne les valeurs manuellement.");
        return;
      }
      if (result.calories != null) setCalories(String(Math.round(result.calories)));
      if (result.protein_g != null) setProtein(String(result.protein_g));
      if (result.carbs_g != null) setCarbs(String(result.carbs_g));
      if (result.fat_g != null) setFat(String(result.fat_g));

      setEstimateNote(
        result.source === "ia"
          ? "Estimation IA — vérifie avant de valider."
          : "Estimation heuristique (mode démo, base d'aliments limitée) — vérifie avant de valider."
      );
    } catch {
      showMessage("Estimation impossible", "Réessaie ou renseigne les valeurs manuellement.");
    } finally {
      setEstimating(false);
    }
  };

  const handleAdd = async () => {
    if (!description.trim()) return;
    setCreating(true);
    try {
      await nutritionApi.create(
        description.trim(),
        calories ? parseInt(calories, 10) : undefined,
        protein ? parseFloat(protein.replace(",", ".")) : undefined,
        carbs ? parseFloat(carbs.replace(",", ".")) : undefined,
        fat ? parseFloat(fat.replace(",", ".")) : undefined
      );
      setDescription("");
      setCalories("");
      setProtein("");
      setCarbs("");
      setFat("");
      setEstimateNote(null);
      await load();
    } finally {
      setCreating(false);
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={{ height: spacing.md }} />

      <Card style={styles.summaryCard}>
        <Text style={[typography.display, { color: colors.textPrimary }]}>{summary?.total_calories ?? 0}</Text>
        <Text style={[typography.caption, { color: colors.textSecondary }]}>KCAL AUJOURD'HUI</Text>
        <View style={styles.macroRow}>
          <MacroBadge label="Protéines" value={summary?.total_protein_g} unit="g" />
          <MacroBadge label="Glucides" value={summary?.total_carbs_g} unit="g" />
          <MacroBadge label="Lipides" value={summary?.total_fat_g} unit="g" />
        </View>
      </Card>

      <View style={styles.formSection}>
        <Input value={description} onChangeText={setDescription} placeholder="Ce que tu as mangé... (ex: 2 oeufs et du pain)" />

        <Button
          label={estimating ? "Estimation..." : "Estimer les calories"}
          onPress={handleEstimate}
          loading={estimating}
          variant="secondary"
          disabled={!description.trim()}
          style={{ marginBottom: spacing.sm }}
        />

        {estimateNote && (
          <Text style={[typography.caption, { color: colors.textSecondary, marginBottom: spacing.sm }]}>
            {estimateNote}
          </Text>
        )}

        <View style={styles.macroInputRow}>
          <View style={{ flex: 1 }}>
            <Input value={calories} onChangeText={setCalories} placeholder="kcal" keyboardType="number-pad" />
          </View>
          <View style={{ flex: 1, marginLeft: spacing.sm }}>
            <Input value={protein} onChangeText={setProtein} placeholder="protéines (g)" keyboardType="decimal-pad" />
          </View>
        </View>
        <View style={styles.macroInputRow}>
          <View style={{ flex: 1 }}>
            <Input value={carbs} onChangeText={setCarbs} placeholder="glucides (g)" keyboardType="decimal-pad" />
          </View>
          <View style={{ flex: 1, marginLeft: spacing.sm }}>
            <Input value={fat} onChangeText={setFat} placeholder="lipides (g)" keyboardType="decimal-pad" />
          </View>
        </View>

        <Button label="Ajouter" onPress={handleAdd} loading={creating} disabled={!description.trim()} />
      </View>

      <FlatList
        data={summary?.entries ?? []}
        keyExtractor={(e: NutritionLog) => e.id}
        contentContainerStyle={{ padding: spacing.lg, paddingTop: 0 }}
        renderItem={({ item }) => (
          <Card style={styles.entryCard}>
            <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>{item.description}</Text>
            {item.calories != null && (
              <Text style={[typography.caption, { color: colors.textSecondary }]}>{item.calories} kcal</Text>
            )}
          </Card>
        )}
      />
    </View>
  );
}

function MacroBadge({ label, value, unit }: { label: string; value?: number; unit: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.macroBadge}>
      <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>
        {value != null ? Math.round(value) : 0}{unit}
      </Text>
      <Text style={[typography.caption, { color: colors.textSecondary }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  summaryCard: { alignItems: "center", marginHorizontal: spacing.lg, marginBottom: spacing.md, paddingVertical: spacing.lg },
  macroRow: { flexDirection: "row", marginTop: spacing.md, gap: spacing.lg },
  macroBadge: { alignItems: "center" },
  formSection: { paddingHorizontal: spacing.lg },
  macroInputRow: { flexDirection: "row" },
  entryCard: { marginBottom: spacing.sm },
});
