import React, { useCallback, useState } from "react";
import { View, Text, ScrollView, StyleSheet, RefreshControl } from "react-native";
import { useFocusEffect, useNavigation } from "@react-navigation/native";
import type { BottomTabNavigationProp } from "@react-navigation/bottom-tabs";
import type { MainTabParamList } from "../navigation/RootNavigator";
import { useTheme } from "../theme/useTheme";
import { typography, spacing } from "../theme/typography";
import { useAuth } from "../context/AuthContext";
import { tasksApi, habitsApi, goalsApi } from "../api/endpoints";
import { Task, Habit, Goal } from "../api/types";
import { Card } from "../components/Card";
import { ScoreRing } from "../components/ScoreRing";
import { Button } from "../components/Button";
import { NudgeCard } from "../components/NudgeCard";
import { useNudges } from "../hooks/useNudges";
import { useOnForeground } from "../hooks/useOnForeground";

/**
 * Le "Daily Life Score" est calculé côté client dans ce prototype, à
 * partir du taux de tâches terminées et d'objectifs actifs en
 * progression. Le cahier des charges prévoit un calcul plus riche
 * (sommeil, sport, habitudes du jour) une fois les modules santé et
 * habitudes du jour branchés sur de vraies données (Phase 3/4) — ce
 * calcul devra alors migrer côté backend pour rester cohérent entre
 * plateformes.
 */
function computeDailyScore(tasks: Task[], goals: Goal[]): number {
  const doneTasks = tasks.filter((t) => t.status === "done").length;
  const taskScore = tasks.length > 0 ? (doneTasks / tasks.length) * 60 : 30;

  const avgGoalProgress = goals.length > 0 ? goals.reduce((s, g) => s + g.progress, 0) / goals.length : 0;
  const goalScore = avgGoalProgress * 40;

  return Math.round(taskScore + goalScore);
}

export function DashboardScreen() {
  const { colors } = useTheme();
  const { user, logout } = useAuth();
  const navigation = useNavigation<BottomTabNavigationProp<MainTabParamList>>();
  const { nudges, refresh: refreshNudges, dismiss: dismissNudge } = useNudges();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [habits, setHabits] = useState<Habit[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const [t, h, g] = await Promise.all([tasksApi.list(), habitsApi.list(), goalsApi.list()]);
    setTasks(t);
    setHabits(h);
    setGoals(g);
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
      refreshNudges();
    }, [load, refreshNudges])
  );

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await Promise.all([load(), refreshNudges()]);
    } finally {
      setRefreshing(false);
    }
  };

  useOnForeground(async () => {
    await Promise.all([load(), refreshNudges()]);
  });

  const score = computeDailyScore(tasks, goals);
  const pendingTasks = tasks.filter((t) => t.status !== "done").slice(0, 4);
  const activeGoals = goals.filter((g) => g.status === "active").slice(0, 3);

  return (
    <ScrollView
      style={{ backgroundColor: colors.background }}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.accent} />}
    >
      <View style={styles.header}>
        <View>
          <Text style={[typography.caption, { color: colors.textSecondary }]}>Bonjour</Text>
          <Text style={[typography.title, { color: colors.textPrimary }]}>{user?.full_name ?? user?.email}</Text>
        </View>
      </View>

      <NudgeCard
        nudges={nudges}
        onOpen={(view) => navigation.navigate(view === "habits" ? "Habits" : "Tasks")}
        onDismiss={dismissNudge}
      />

      <Card style={styles.scoreCard}>
        <ScoreRing score={score} />
        <Text style={[typography.caption, { color: colors.textSecondary, marginTop: spacing.md, textAlign: "center" }]}>
          Basé sur tes tâches terminées et la progression de tes objectifs
        </Text>
      </Card>

      <Text style={[typography.subtitle, { color: colors.textPrimary, marginTop: spacing.lg, marginBottom: spacing.sm }]}>
        Tâches en cours
      </Text>
      {pendingTasks.length === 0 ? (
        <Card><Text style={[typography.body, { color: colors.textSecondary }]}>Aucune tâche en attente. Belle journée libre.</Text></Card>
      ) : (
        pendingTasks.map((t) => (
          <Card key={t.id} style={styles.rowCard}>
            <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>{t.title}</Text>
            <Text style={[typography.caption, { color: colors.textSecondary }]}>Priorité : {t.priority}</Text>
          </Card>
        ))
      )}

      <Text style={[typography.subtitle, { color: colors.textPrimary, marginTop: spacing.lg, marginBottom: spacing.sm }]}>
        Objectifs actifs
      </Text>
      {activeGoals.length === 0 ? (
        <Card><Text style={[typography.body, { color: colors.textSecondary }]}>Aucun objectif actif pour l'instant.</Text></Card>
      ) : (
        activeGoals.map((g) => (
          <Card key={g.id} style={styles.rowCard}>
            <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>{g.title}</Text>
            <Text style={[typography.caption, { color: colors.textSecondary }]}>{Math.round(g.progress * 100)}% complété</Text>
          </Card>
        ))
      )}

      <Text style={[typography.subtitle, { color: colors.textPrimary, marginTop: spacing.lg, marginBottom: spacing.sm }]}>
        Habitudes
      </Text>
      <Card style={styles.rowCard}>
        <Text style={[typography.body, { color: colors.textSecondary }]}>{habits.length} habitude(s) suivie(s)</Text>
      </Card>

      <Button label="Se déconnecter" onPress={logout} variant="ghost" style={{ marginTop: spacing.xl }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, paddingBottom: spacing.xxl },
  header: { marginBottom: spacing.lg },
  scoreCard: { alignItems: "center", paddingVertical: spacing.lg },
  rowCard: { marginBottom: spacing.sm },
});
