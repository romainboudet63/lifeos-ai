import { useCallback, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { nudgesApi } from "../api/endpoints";
import { Nudge } from "../api/types";
import { deviceTimeZone, localIsoDay } from "../utils/dates";

const DISMISSED_KEY = "lifeos_dismissed_nudges";

/** Clés des rappels masqués AUJOURD'HUI (la liste repart à zéro chaque jour). */
async function loadDismissed(): Promise<string[]> {
  try {
    const raw = await AsyncStorage.getItem(DISMISSED_KEY);
    if (!raw) return [];
    const saved = JSON.parse(raw) as { day: string; keys: string[] };
    return saved.day === localIsoDay() && Array.isArray(saved.keys) ? saved.keys : [];
  } catch {
    return [];
  }
}

async function saveDismissed(keys: string[]): Promise<void> {
  try {
    await AsyncStorage.setItem(DISMISSED_KEY, JSON.stringify({ day: localIsoDay(), keys }));
  } catch {
    // stockage indisponible : le rappel réapparaîtra au prochain chargement, sans gravité
  }
}

/**
 * Rappels intelligents du moment (calculés par le backend, GET /nudges).
 * Les rappels sont facultatifs : en cas d'échec réseau on n'affiche simplement rien.
 */
export function useNudges() {
  const [nudges, setNudges] = useState<Nudge[]>([]);

  const refresh = useCallback(async () => {
    try {
      const dismissed = await loadDismissed();
      setNudges(await nudgesApi.list(deviceTimeZone(), dismissed));
    } catch {
      setNudges([]);
    }
  }, []);

  const dismiss = useCallback(async (key: string) => {
    setNudges((prev) => prev.filter((n) => n.key !== key));
    await saveDismissed([...(await loadDismissed()), key]);
  }, []);

  return { nudges, refresh, dismiss };
}
