/**
 * Utilitaires de dates (jours locaux, sans fuseau).
 *
 * Le backend ne garde que le JOUR d'une échéance : on envoie donc minuit local
 * sans fuseau ("2026-11-17T00:00:00") plutôt qu'un instant UTC, qui pourrait
 * tomber la veille ou le lendemain.
 */

const pad = (n: number) => String(n).padStart(2, "0");

function parts(iso: string): [number, number, number] {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return [y, m, d];
}

/** Jour local au format YYYY-MM-DD. */
export function localIsoDay(date: Date = new Date()): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function addDays(iso: string, n: number): string {
  const [y, m, d] = parts(iso);
  return localIsoDay(new Date(y, m - 1, d + n));
}

/** Valeur de `due_date` à envoyer au backend pour un jour donné. */
export function dueDateForApi(isoDay: string): string {
  return `${isoDay}T00:00:00`;
}

/** Nombre de jours entre `today` et `iso` (négatif = passé). */
export function dayDiff(iso: string, today: string = localIsoDay()): number {
  const [y1, m1, d1] = parts(iso);
  const [y2, m2, d2] = parts(today);
  return Math.round((Date.UTC(y1, m1 - 1, d1) - Date.UTC(y2, m2 - 1, d2)) / 86400000);
}

export function dueLabel(dueDate: string, today: string = localIsoDay()): { text: string; late: boolean } {
  const iso = dueDate.slice(0, 10);
  const n = dayDiff(iso, today);
  if (n < 0) return { text: n === -1 ? "En retard · hier" : `En retard · ${-n} j`, late: true };
  if (n === 0) return { text: "Aujourd'hui", late: false };
  if (n === 1) return { text: "Demain", late: false };
  const [y, m, d] = parts(iso);
  const text = new Date(y, m - 1, d).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" });
  return { text, late: false };
}

/**
 * Date de création renvoyée par le backend : un instant UTC SANS suffixe "Z"
 * (datetime.utcnow). Sans correction, `new Date()` l'interpréterait comme local.
 */
export function formatCreatedAt(createdAt: string): string {
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(createdAt);
  const date = new Date(hasZone ? createdAt : `${createdAt}Z`);
  if (isNaN(date.getTime())) return "";
  return date.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

/** Fuseau IANA de l'appareil (ex. "Europe/Paris"), ou undefined s'il est indisponible. */
export function deviceTimeZone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
  } catch {
    return undefined;
  }
}
