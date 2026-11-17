import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useTheme } from "../theme/useTheme";
import { MoreScreen } from "../screens/MoreScreen";
import { CalendarScreen } from "../screens/CalendarScreen";
import { WorkoutsScreen } from "../screens/WorkoutsScreen";
import { NutritionScreen } from "../screens/NutritionScreen";
import { FinanceScreen } from "../screens/FinanceScreen";
import { MemoryScreen } from "../screens/MemoryScreen";

export type MoreStackParamList = {
  MoreHome: undefined;
  Calendar: undefined;
  Workouts: undefined;
  Nutrition: undefined;
  Finance: undefined;
  Memory: undefined;
};

const Stack = createNativeStackNavigator<MoreStackParamList>();

export function MoreStackNavigator() {
  const { colors } = useTheme();

  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.textPrimary,
        headerShadowVisible: false,
        headerTitleStyle: { fontWeight: "700" },
      }}
    >
      <Stack.Screen name="MoreHome" component={MoreScreen} options={{ title: "Plus", headerShown: false }} />
      <Stack.Screen name="Calendar" component={CalendarScreen} options={{ title: "Calendrier" }} />
      <Stack.Screen name="Workouts" component={WorkoutsScreen} options={{ title: "Sport" }} />
      <Stack.Screen name="Nutrition" component={NutritionScreen} options={{ title: "Nutrition" }} />
      <Stack.Screen name="Finance" component={FinanceScreen} options={{ title: "Finances" }} />
      <Stack.Screen name="Memory" component={MemoryScreen} options={{ title: "Mémoire de l'assistant" }} />
    </Stack.Navigator>
  );
}
