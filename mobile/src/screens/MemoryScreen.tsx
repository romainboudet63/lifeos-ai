import React, { useCallback, useState } from "react";
import { View, Text, FlatList, StyleSheet, Pressable, RefreshControl } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { useTheme } from "../theme/useTheme";
import { typography, spacing } from "../theme/typography";
import { memoriesApi } from "../api/endpoints";
import { Memory } from "../api/types";
import { formatCreatedAt } from "../utils/dates";
import { Card } from "../components/Card";
import { Input } from "../components/Input";
import { Button } from "../components/Button";
import { useOnForeground } from "../hooks/useOnForeground";
import { showMessage, confirmAction } from "../utils/dialogs";

/**
 * Ce que l'assistant retient sur l'utilisateur. Les souvenirs sont ajoutés
 * automatiquement par le backend après chaque échange (en tâche de fond) : la
 * liste se recharge à chaque ouverture de l'écran et par tirage vers le bas.
 */
export function MemoryScreen() {
  const { colors } = useTheme();
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [draft, setDraft] = useState("");
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    try {
      setMemories(await memoriesApi.list());
      setError(null);
    } catch {
      setError("Impossible de charger les souvenirs. Vérifie ta connexion, puis réessaie.");
    } finally {
      setLoaded(true);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  useOnForeground(load);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const handleAdd = async () => {
    const content = draft.trim();
    if (!content) return;
    setAdding(true);
    try {
      await memoriesApi.add(content);
      setDraft("");
      await load();
    } catch {
      showMessage("Ajout impossible", "Le souvenir n'a pas pu être enregistré. Réessaie dans un instant.");
    } finally {
      setAdding(false);
    }
  };

  const forget = async (memory: Memory) => {
    setMemories((prev) => prev.filter((m) => m.id !== memory.id)); // retrait immédiat
    try {
      await memoriesApi.remove(memory.id);
    } catch {
      await load(); // la suppression a échoué : on réaffiche l'état réel
      showMessage("Suppression impossible", "Ce souvenir n'a pas pu être oublié. Réessaie dans un instant.");
    }
  };

  const forgetAll = () => {
    confirmAction(
      "Tout oublier ?",
      "L'assistant perdra tout ce qu'il a retenu sur toi. Cette action est définitive.",
      "Tout oublier",
      async () => {
        try {
          await memoriesApi.clear();
          setMemories([]);
        } catch {
          showMessage("Suppression impossible", "Les souvenirs n'ont pas pu être effacés. Réessaie dans un instant.");
        }
      }
    );
  };

  return (
    <FlatList
      style={{ backgroundColor: colors.background }}
      data={memories}
      keyExtractor={(m) => m.id}
      keyboardShouldPersistTaps="handled"
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.accent} />}
      ListHeaderComponent={
        <View style={{ marginBottom: spacing.md }}>
          <Text style={[typography.body, { color: colors.textSecondary, marginBottom: spacing.md }]}>
            L'assistant retient tout seul l'essentiel et durable : préférences, proches, projets, contraintes. Tu peux
            aussi lui dire « retiens que… » ou « oublie… » dans le chat. Supprime ce que tu ne veux pas qu'il garde.
          </Text>
          <View style={styles.addRow}>
            <View style={{ flex: 1 }}>
              <Input
                value={draft}
                onChangeText={setDraft}
                placeholder="Ajouter un souvenir..."
                maxLength={200}
                onSubmitEditing={handleAdd}
                style={{ marginBottom: 0 }}
              />
            </View>
            <Button label="Retenir" onPress={handleAdd} loading={adding} disabled={!draft.trim()} style={styles.addButton} />
          </View>
          {error && <Text style={[typography.caption, { color: colors.danger, marginTop: spacing.sm }]}>{error}</Text>}
        </View>
      }
      ListEmptyComponent={
        loaded && !error ? (
          <Card>
            <Text style={[typography.body, { color: colors.textSecondary }]}>
              Rien pour l'instant. Parle à ton assistant : il retiendra ce qui compte.
            </Text>
          </Card>
        ) : null
      }
      renderItem={({ item }) => (
        <Card style={styles.item}>
          <View style={styles.itemRow}>
            <View style={{ flex: 1 }}>
              <Text style={[typography.body, { color: colors.textPrimary }]}>{item.content}</Text>
              <Text style={[typography.caption, { color: colors.textSecondary, marginTop: 2 }]}>
                {formatCreatedAt(item.created_at)}
              </Text>
            </View>
            <Pressable
              onPress={() => forget(item)}
              hitSlop={12}
              accessibilityRole="button"
              accessibilityLabel="Oublier ce souvenir"
            >
              <Text style={{ color: colors.textSecondary, fontSize: 20 }}>×</Text>
            </Pressable>
          </View>
        </Card>
      )}
      ListFooterComponent={
        memories.length > 0 ? (
          <Button label="Tout oublier" onPress={forgetAll} variant="ghost" style={{ marginTop: spacing.md }} />
        ) : null
      }
    />
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, paddingBottom: spacing.xxl },
  addRow: { flexDirection: "row", alignItems: "flex-start", gap: spacing.sm },
  addButton: { paddingHorizontal: spacing.md },
  item: { marginBottom: spacing.sm },
  itemRow: { flexDirection: "row", alignItems: "flex-start", gap: spacing.sm },
});
