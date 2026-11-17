import React, { useCallback, useState } from "react";
import { View, Text, FlatList, StyleSheet } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useTheme } from "../theme/useTheme";
import { typography, spacing } from "../theme/typography";
import { habitsApi } from "../api/endpoints";
import { Habit } from "../api/types";
import { Card } from "../components/Card";
import { Input } from "../components/Input";
import { Button } from "../components/Button";

export function HabitsScreen() {
  const { colors } = useTheme();
  const [habits, setHabits] = useState<Habit[]>([]);
  const [loggedToday, setLoggedToday] = useState<Set<string>>(new Set());
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setHabits(await habitsApi.list());
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await habitsApi.create(newName.trim());
      setNewName("");
      await load();
    } finally {
      setCreating(false);
    }
  };

  const handleLog = async (habit: Habit) => {
    await habitsApi.log(habit.id, true);
    setLoggedToday((prev) => new Set(prev).add(habit.id));
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Text style={[typography.title, { color: colors.textPrimary, margin: spacing.lg, marginBottom: spacing.sm }]}>
        Habitudes
      </Text>

      <View style={styles.newRow}>
        <View style={{ flex: 1 }}>
          <Input value={newName} onChangeText={setNewName} placeholder="Nouvelle habitude..." onSubmitEditing={handleCreate} />
        </View>
        <Button label="+" onPress={handleCreate} loading={creating} disabled={!newName.trim()} style={styles.addButton} />
      </View>

      <FlatList
        data={habits}
        keyExtractor={(h) => h.id}
        contentContainerStyle={{ padding: spacing.lg, paddingTop: 0 }}
        ListEmptyComponent={
          <Card><Text style={[typography.body, { color: colors.textSecondary }]}>Aucune habitude suivie pour l'instant.</Text></Card>
        }
        renderItem={({ item }) => {
          const done = loggedToday.has(item.id);
          return (
            <Card style={styles.habitCard}>
              <View style={{ flex: 1 }}>
                <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>{item.name}</Text>
                <Text style={[typography.caption, { color: colors.textSecondary }]}>
                  {item.target_frequency}x / semaine{item.category ? ` · ${item.category}` : ""}
                </Text>
              </View>
              <Button
                label={done ? "✓ Fait" : "Marquer fait"}
                onPress={() => handleLog(item)}
                variant={done ? "secondary" : "primary"}
                disabled={done}
                style={{ paddingHorizontal: spacing.md, paddingVertical: spacing.sm }}
              />
            </Card>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  newRow: { flexDirection: "row", alignItems: "flex-start", paddingHorizontal: spacing.lg, gap: spacing.sm },
  addButton: { paddingHorizontal: spacing.md, marginTop: 0 },
  habitCard: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: spacing.sm },
});
