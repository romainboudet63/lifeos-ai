import React from "react";
import { View, Text, Pressable, StyleSheet, ScrollView } from "react-native";
import { useTheme } from "../theme/useTheme";
import { typography, spacing, radius } from "../theme/typography";
import { Card } from "../components/Card";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { MoreStackParamList } from "../navigation/MoreStackNavigator";

type Props = NativeStackScreenProps<MoreStackParamList, "MoreHome">;

interface MenuItem {
  route: keyof MoreStackParamList;
  label: string;
  description: string;
}

const ITEMS: MenuItem[] = [
  { route: "Calendar", label: "Calendrier", description: "Événements et synchronisation Google Calendar" },
  { route: "Workouts", label: "Sport", description: "Entraînements et synchronisation Strava" },
  { route: "Nutrition", label: "Nutrition", description: "Repas et résumé calorique du jour" },
  { route: "Finance", label: "Finances", description: "Dépenses et budgets par catégorie" },
  { route: "Memory", label: "Mémoire de l'assistant", description: "Ce que l'assistant retient sur toi, que tu peux corriger" },
];

export function MoreScreen({ navigation }: Props) {
  const { colors } = useTheme();

  return (
    <ScrollView style={{ backgroundColor: colors.background }} contentContainerStyle={styles.content}>
      <Text style={[typography.title, { color: colors.textPrimary, marginBottom: spacing.lg }]}>Plus</Text>

      {ITEMS.map((item) => (
        <Pressable key={item.route} onPress={() => navigation.navigate(item.route as any)}>
          <Card style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={[typography.bodyStrong, { color: colors.textPrimary }]}>{item.label}</Text>
              <Text style={[typography.caption, { color: colors.textSecondary, marginTop: 2 }]}>
                {item.description}
              </Text>
            </View>
            <Text style={{ color: colors.textSecondary, fontSize: 20 }}>›</Text>
          </Card>
        </Pressable>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.lg, paddingBottom: spacing.xxl },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing.sm,
    borderRadius: radius.lg,
  },
});
