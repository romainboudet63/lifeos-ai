import { useEffect, useRef } from "react";
import { AppState } from "react-native";
import { useIsFocused } from "@react-navigation/native";

/**
 * Relance `callback` quand l'app repasse au premier plan (réouverture depuis l'écran d'accueil de
 * l'iPhone, retour d'un autre onglet...). Sur le web le tirer-pour-rafraîchir n'existe pas : c'est
 * ce qui garde les données à jour. Ne s'exécute que pour l'écran actuellement affiché.
 */
export function useOnForeground(callback: () => void | Promise<void>): void {
  const focused = useIsFocused();
  const latest = useRef(callback);
  latest.current = callback;

  useEffect(() => {
    if (!focused) return;
    const sub = AppState.addEventListener("change", (state) => {
      if (state === "active") void Promise.resolve(latest.current()).catch(() => undefined);
    });
    return () => sub.remove();
  }, [focused]);
}
