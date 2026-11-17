import React, { useCallback, useState } from "react";
import { View, Text, FlatList, StyleSheet, Pressable } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useTheme } from "../theme/useTheme";
import { typography, spacing, radius } from "../theme/typography";
import { tasksApi } from "../api/endpoints";
import { Task } from "../api/types";
import { Card } from "../components/Card";
import { Input } from "../components/Input";
import { Button } from "../components/Button";
import { addDays, dueDateForApi, dueLabel, localIsoDay } from "../utils/dates";

const PRIORITY_COLOR: Record<Task["priority"], string> = {
  high: "#B4523F",
  medium: "#C98A3D",
  low: "#5C6B63",
};

// Échéances proposées à la création : décalage en jours depuis aujourd'hui (null = sans échéance).
const DUE_CHOICES: { label: string; offset: number | null }[] = [
  { label: "Sans date", offset: null },
  { label: "Aujourd'hui", offset: 0 },
  { label: "Demain", offset: 1 },
  { label: "Dans 7 j", offset: 7 },
];

export function TasksScreen() {
  const { colors } = useTheme();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [newTitle, setNewTitle] = useState("");
  const [creating, setCreating] = useState(false);
  const [dueOffset, setDueOffset] = useState<number | null>(null);

  const load = useCallback(async () => {
    setTasks(await tasksApi.list());
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const dueDate = dueOffset === null ? undefined : dueDateForApi(addDays(localIsoDay(), dueOffset));
      await tasksApi.create(newTitle.trim(), "medium", dueDate);
      setNewTitle("");
      setDueOffset(null);
      await load();
    } finally {
      setCreating(false);
    }
  };

  const toggleDone = async (task: Task) => {
    await tasksApi.updateStatus(task.id, task.status === "done" ? "todo" : "done");
    await load();
  };

  const remove = async (task: Task) => {
    await tasksApi.remove(task.id);
    await load();
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Text style={[typography.title, { color: colors.textPrimary, margin: spacing.lg, marginBottom: spacing.sm }]}>
        Tâches
      </Text>

      <View style={styles.newTaskRow}>
        <View style={{ flex: 1 }}>
          <Input value={newTitle} onChangeText={setNewTitle} placeholder="Nouvelle tâche..." onSubmitEditing={handleCreate} />
        </View>
        <Button label="+" onPress={handleCreate} loading={creating} disabled={!newTitle.trim()} style={styles.addButton} />
      </View>

      <View style={styles.dueRow}>
        {DUE_CHOICES.map((choice) => {
          const selected = dueOffset === choice.offset;
          return (
            <Pressable
              key={choice.label}
              onPress={() => setDueOffset(choice.offset)}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              style={[
                styles.chip,
                {
                  borderColor: selected ? colors.accent : colors.border,
                  backgroundColor: selected ? colors.accentMuted : "transparent",
                },
              ]}
            >
              <Text style={[typography.caption, { color: selected ? colors.accent : colors.textSecondary }]}>
                {choice.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <FlatList
        data={tasks}
        keyExtractor={(t) => t.id}
        contentContainerStyle={{ padding: spacing.lg, paddingTop: 0 }}
        ListEmptyComponent={
          <Card><Text style={[typography.body, { color: colors.textSecondary }]}>Aucune tâche. Ajoute la première ci-dessus.</Text></Card>
        }
        renderItem={({ item }) => (
          <Card style={styles.taskCard}>
            <Pressable onPress={() => toggleDone(item)} style={styles.taskRow}>
              <View
                style={[
                  styles.checkbox,
                  { borderColor: colors.accent, backgroundColor: item.status === "done" ? colors.accent : "transparent" },
                ]}
              />
              <View style={{ flex: 1 }}>
                <Text
                  style={[
                    typography.bodyStrong,
                    {
                      color: colors.textPrimary,
                      textDecorationLine: item.status === "done" ? "line-through" : "none",
                    },
                  ]}
                >
                  {item.title}
                </Text>
                <Text style={[typography.caption, { color: PRIORITY_COLOR[item.priority] }]}>
                  {item.priority.toUpperCase()}
                </Text>
                {item.due_date && item.status !== "done" && (
                  <Text
                    style={[
                      typography.caption,
                      { color: dueLabel(item.due_date).late ? colors.danger : colors.textSecondary },
                    ]}
                  >
                    {dueLabel(item.due_date).text}
                  </Text>
                )}
              </View>
              <Pressable onPress={() => remove(item)} hitSlop={8}>
                <Text style={{ color: colors.textSecondary, fontSize: 18 }}>×</Text>
              </Pressable>
            </Pressable>
          </Card>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  newTaskRow: { flexDirection: "row", alignItems: "flex-start", paddingHorizontal: spacing.lg, gap: spacing.sm },
  addButton: { paddingHorizontal: spacing.md, marginTop: 0 },
  dueRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, paddingHorizontal: spacing.lg, paddingBottom: spacing.md },
  chip: { paddingVertical: spacing.xs + 2, paddingHorizontal: spacing.sm + 4, borderRadius: radius.pill, borderWidth: 1 },
  taskCard: { marginBottom: spacing.sm },
  taskRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  checkbox: { width: 22, height: 22, borderRadius: radius.sm, borderWidth: 2 },
});
