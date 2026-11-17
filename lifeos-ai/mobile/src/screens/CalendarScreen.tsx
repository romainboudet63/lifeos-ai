import React, { useCallback, useState } from "react";
import { View, Text, FlatList, StyleSheet, Linking } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useTheme } from "../theme/useTheme";
import { typography, spacing } from "../theme/typography";
import { calendarApi } from "../api/endpoints";
import { CalendarEvent } from "../api/types";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { ApiError } from "../api/client";
import { showMessage } from "../utils/dialogs";

function formatRange(startIso: string, endIso: string): string {
  const start = new Date(startIso);
  const end = new Date(endIso);
  const day = start.toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" });
  const startTime = start.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  const endTime = end.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  return `${day} · ${startTime} - ${endTime}`;
}

export function CalendarScreen() {
  const { colors } = useTheme();
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [connecting, setConnecting] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const load = useCallback(async () => {
    const status = await calendarApi.googleStatus();
    setConnected(status.connected);
    setEvents(await calendarApi.list());
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const { auth_url } = await calendarApi.googleAuthUrl();
      await Linking.openURL(auth_url);
    } catch (e) {
      const message =
        e instanceof ApiError && e.status === 503
          ? "Google Calendar n'est pas encore configuré côté backend (voir README.md pour créer les identifiants Google Cloud)."
          : "Impossible d'ouvrir la fenêtre de connexion Google.";
      showMessage("Connexion impossible", message);
    } finally {
      setConnecting(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await calendarApi.sync();
      await load();
    } catch {
      showMessage("Synchronisation impossible", "Vérifie que ton compte Google est bien connecté.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={{ height: spacing.md }} />

      <Card style={styles.statusCard}>
        <View style={{ flex: 1 }}>
          <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>
            {connected ? "Google Calendar connecté" : "Google Calendar non connecté"}
          </Text>
          <Text style={[typography.caption, { color: colors.textSecondary }]}>
            {connected
              ? "Synchronise pour récupérer tes derniers événements"
              : "Connecte ton compte pour importer tes événements"}
          </Text>
        </View>
        {connected ? (
          <Button label="Synchroniser" onPress={handleSync} loading={syncing} variant="secondary" />
        ) : (
          <Button label="Connecter" onPress={handleConnect} loading={connecting} />
        )}
      </Card>

      <FlatList
        data={events}
        keyExtractor={(e) => e.id}
        contentContainerStyle={{ padding: spacing.lg, paddingTop: spacing.sm }}
        ListEmptyComponent={
          <Card>
            <Text style={[typography.body, { color: colors.textSecondary }]}>
              Aucun événement pour l'instant. {connected ? "Essaie de synchroniser." : "Connecte ton compte Google pour commencer."}
            </Text>
          </Card>
        }
        renderItem={({ item }) => (
          <Card style={styles.eventCard}>
            <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>{item.title}</Text>
            <Text style={[typography.caption, { color: colors.textSecondary }]}>
              {formatRange(item.start_at, item.end_at)}
              {item.location ? ` · ${item.location}` : ""}
            </Text>
            {item.external_provider && (
              <Text style={[typography.caption, { color: colors.accent, marginTop: 2 }]}>
                Synchronisé depuis Google
              </Text>
            )}
          </Card>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  statusCard: { flexDirection: "row", alignItems: "center", marginHorizontal: spacing.lg, marginBottom: spacing.sm },
  eventCard: { marginBottom: spacing.sm },
});
