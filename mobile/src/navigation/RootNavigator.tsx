import React from "react";
import { ActivityIndicator, View } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../theme/useTheme";
import { LoginScreen } from "../screens/LoginScreen";
import { RegisterScreen } from "../screens/RegisterScreen";
import { DashboardScreen } from "../screens/DashboardScreen";
import { TasksScreen } from "../screens/TasksScreen";
import { HabitsScreen } from "../screens/HabitsScreen";
import { ChatScreen } from "../screens/ChatScreen";
import { MoreStackNavigator } from "./MoreStackNavigator";

export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
};

// 5 onglets principaux — Calendrier/Sport/Nutrition/Finances sont
// regroupés dans "Plus" (voir MoreStackNavigator) plutôt que d'être
// des onglets séparés : au-delà de 5, la barre d'onglets devient
// illisible sur mobile et les fonctions secondaires se noient parmi
// les principales.
export type MainTabParamList = {
  Dashboard: undefined;
  Tasks: undefined;
  Habits: undefined;
  Chat: undefined;
  More: undefined;
};

const AuthStack = createNativeStackNavigator<AuthStackParamList>();
const MainTabs = createBottomTabNavigator<MainTabParamList>();

function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Login" component={LoginScreen} />
      <AuthStack.Screen name="Register" component={RegisterScreen} />
    </AuthStack.Navigator>
  );
}

function MainNavigator() {
  const { colors } = useTheme();
  return (
    <MainTabs.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.accent,
        tabBarInactiveTintColor: colors.textSecondary,
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border },
      }}
    >
      <MainTabs.Screen name="Dashboard" component={DashboardScreen} options={{ title: "Accueil" }} />
      <MainTabs.Screen name="Tasks" component={TasksScreen} options={{ title: "Tâches" }} />
      <MainTabs.Screen name="Habits" component={HabitsScreen} options={{ title: "Habitudes" }} />
      <MainTabs.Screen name="Chat" component={ChatScreen} options={{ title: "Assistant" }} />
      <MainTabs.Screen name="More" component={MoreStackNavigator} options={{ title: "Plus" }} />
    </MainTabs.Navigator>
  );
}

export function RootNavigator() {
  const { user, isLoading } = useAuth();
  const { colors } = useTheme();

  if (isLoading) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.background }}>
        <ActivityIndicator color={colors.accent} size="large" />
      </View>
    );
  }

  return <NavigationContainer>{user ? <MainNavigator /> : <AuthNavigator />}</NavigationContainer>;
}
