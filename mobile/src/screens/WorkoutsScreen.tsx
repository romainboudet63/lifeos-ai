import React, { useCallback, useState } from "react";
import { View, Text, ScrollView, StyleSheet, Linking, Pressable } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useTheme } from "../theme/useTheme";
import { typography, spacing } from "../theme/typography";
import { stravaApi, workoutProgramApi } from "../api/endpoints";
import { Workout, WorkoutProgram, WorkoutProgramSummary } from "../api/types";
import { Card } from "../components/Card";
import { Input } from "../components/Input";
import { Button } from "../components/Button";
import { ApiError } from "../api/client";
import { showMessage } from "../utils/dialogs";

const TYPE_LABEL: Record<string, string> = {
  course: "Course à pied",
  cyclisme: "Cyclisme",
  natation: "Natation",
  musculation: "Musculation",
  yoga: "Yoga",
  randonnee: "Randonnée",
  marche: "Marche",
};

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" });
}

function ProgramWeeks({ program }: { program: WorkoutProgram }) {
  const { colors } = useTheme();
  return (
    <View style={{ marginTop: spacing.sm }}>
      {program.weeks.map((week) => (
        <View key={week.week_number} style={{ marginBottom: spacing.sm }}>
          <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>
            Semaine {week.week_number} — {week.focus}
          </Text>
          {week.sessions.map((s, i) => (
            <Text key={i} style={[typography.caption, { color: colors.textSecondary, marginLeft: spacing.sm }]}>
              {s.day_label} · {s.type} ({s.duration_min} min) — {s.description}
            </Text>
          ))}
        </View>
      ))}
    </View>
  );
}

export function WorkoutsScreen() {
  const { colors } = useTheme();
  const [connected, setConnected] = useState(false);
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [connecting, setConnecting] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const [objective, setObjective] = useState("");
  const [generating, setGenerating] = useState(false);
  const [freshProgram, setFreshProgram] = useState<WorkoutProgram | null>(null);
  const [programs, setPrograms] = useState<WorkoutProgramSummary[]>([]);
  const [expandedProgram, setExpandedProgram] = useState<WorkoutProgram | null>(null);
  const [expandingId, setExpandingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const status = await stravaApi.status();
    setConnected(status.connected);
    setWorkouts(await stravaApi.list());
    setPrograms(await workoutProgramApi.list());
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const { auth_url } = await stravaApi.authUrl();
      await Linking.openURL(auth_url);
    } catch (e) {
      const message =
        e instanceof ApiError && e.status === 503
          ? "Strava n'est pas encore configuré côté backend (voir README.md pour créer les identifiants Strava)."
          : "Impossible d'ouvrir la fenêtre de connexion Strava.";
      showMessage("Connexion impossible", message);
    } finally {
      setConnecting(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await stravaApi.sync();
      await load();
    } catch {
      showMessage("Synchronisation impossible", "Vérifie que ton compte Strava est bien connecté.");
    } finally {
      setSyncing(false);
    }
  };

  const handleGenerate = async () => {
    if (!objective.trim()) return;
    setGenerating(true);
    setFreshProgram(null);
    try {
      const program = await workoutProgramApi.generate(objective.trim());
      setFreshProgram(program);
      setObjective("");
      await load();
    } catch {
      showMessage("Génération impossible", "Réessaie dans un instant.");
    } finally {
      setGenerating(false);
    }
  };

  const toggleExpand = async (summary: WorkoutProgramSummary) => {
    if (expandedProgram?.id === summary.id) {
      setExpandedProgram(null);
      return;
    }
    setExpandingId(summary.id);
    try {
      const full = await workoutProgramApi.get(summary.id);
      setExpandedProgram(full);
    } finally {
      setExpandingId(null);
    }
  };

  return (
    <ScrollView style={[styles.container, { backgroundColor: colors.background }]} contentContainerStyle={{ padding: spacing.lg }}>
      <Card style={styles.statusCard}>
        <View style={{ flex: 1 }}>
          <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>
            {connected ? "Strava connecté" : "Strava non connecté"}
          </Text>
          <Text style={[typography.caption, { color: colors.textSecondary }]}>
            {connected ? "Synchronise pour récupérer tes dernières activités" : "Connecte ton compte pour importer tes entraînements"}
          </Text>
        </View>
        {connected ? (
          <Button label="Synchroniser" onPress={handleSync} loading={syncing} variant="secondary" />
        ) : (
          <Button label="Connecter" onPress={handleConnect} loading={connecting} />
        )}
      </Card>

      <Text style={[typography.subtitle, { color: colors.textPrimary, marginTop: spacing.lg, marginBottom: spacing.sm }]}>
        Programme d'entraînement
      </Text>
      <Card>
        <Input
          value={objective}
          onChangeText={setObjective}
          placeholder="Ton objectif... (ex: courir un semi-marathon dans 3 mois)"
        />
        <Button
          label={generating ? "Génération..." : "Générer un programme"}
          onPress={handleGenerate}
          loading={generating}
          disabled={!objective.trim()}
        />
        {freshProgram && (
          <View style={{ marginTop: spacing.md }}>
            <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>{freshProgram.title}</Text>
            <Text style={[typography.caption, { color: colors.textSecondary, marginBottom: spacing.xs }]}>
              {freshProgram.source === "ia" ? "Généré par l'IA" : "Généré par l'heuristique locale (mode démo)"}
            </Text>
            <ProgramWeeks program={freshProgram} />
          </View>
        )}
      </Card>

      {programs.length > 0 && (
        <>
          <Text style={[typography.subtitle, { color: colors.textPrimary, marginTop: spacing.lg, marginBottom: spacing.sm }]}>
            Programmes précédents
          </Text>
          {programs.map((p) => (
            <Card key={p.id} style={styles.programCard}>
              <Pressable onPress={() => toggleExpand(p)}>
                <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>{p.title}</Text>
                <Text style={[typography.caption, { color: colors.textSecondary }]}>
                  {p.week_count} semaines · {p.source === "ia" ? "IA" : "heuristique"}
                  {expandingId === p.id ? " · chargement..." : ""}
                </Text>
              </Pressable>
              {expandedProgram?.id === p.id && <ProgramWeeks program={expandedProgram} />}
            </Card>
          ))}
        </>
      )}

      <Text style={[typography.subtitle, { color: colors.textPrimary, marginTop: spacing.lg, marginBottom: spacing.sm }]}>
        Entraînements récents
      </Text>
      {workouts.length === 0 ? (
        <Card>
          <Text style={[typography.body, { color: colors.textSecondary }]}>
            Aucun entraînement pour l'instant. {connected ? "Essaie de synchroniser." : "Connecte ton compte Strava pour commencer."}
          </Text>
        </Card>
      ) : (
        workouts.map((item) => (
          <Card key={item.id} style={styles.workoutCard}>
            <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>
              {item.type ? TYPE_LABEL[item.type] ?? item.type : "Entraînement"}
            </Text>
            <Text style={[typography.caption, { color: colors.textSecondary }]}>
              {formatDate(item.performed_at)}
              {item.duration_min ? ` · ${item.duration_min} min` : ""}
              {item.calories ? ` · ${item.calories} kcal` : ""}
            </Text>
          </Card>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  statusCard: { flexDirection: "row", alignItems: "center" },
  workoutCard: { marginBottom: spacing.sm },
  programCard: { marginBottom: spacing.sm },
});
