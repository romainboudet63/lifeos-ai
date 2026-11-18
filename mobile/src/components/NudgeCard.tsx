import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { useTheme } from "../theme/useTheme";
import { typography, spacing } from "../theme/typography";
import { Nudge } from "../api/types";
import { Card } from "./Card";

interface NudgeCardProps {
  nudges: Nudge[];
  onOpen: (view: Nudge["view"]) => void;
  onDismiss: (key: string) => void;
}

/** Rappels du moment : un tap ouvre l'écran concerné, la croix masque le rappel pour la journée. */
export function NudgeCard({ nudges, onOpen, onDismiss }: NudgeCardProps) {
  const { colors } = useTheme();
  if (nudges.length === 0) return null;

  return (
    <Card style={styles.card}>
      {nudges.map((nudge, index) => (
        <View
          key={nudge.key}
          style={[styles.row, index > 0 && { borderTopWidth: 1, borderTopColor: colors.border }]}
        >
          <View style={[styles.dot, { backgroundColor: nudge.warn ? colors.warning : colors.accent }]} />
          <Pressable style={{ flex: 1 }} onPress={() => onOpen(nudge.view)} accessibilityRole="button">
            <Text style={[typography.body, { color: colors.textPrimary }]}>{nudge.text}</Text>
          </Pressable>
          <Pressable
            onPress={() => onDismiss(nudge.key)}
            hitSlop={12}
            accessibilityRole="button"
            accessibilityLabel="Masquer ce rappel pour aujourd'hui"
          >
            <Text style={{ color: colors.textSecondary, fontSize: 20 }}>×</Text>
          </Pressable>
        </View>
      ))}
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: spacing.md, paddingVertical: spacing.xs },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.sm + 4, paddingVertical: spacing.sm + 4 },
  dot: { width: 8, height: 8, borderRadius: 4 },
});
