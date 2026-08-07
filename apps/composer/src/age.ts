// Sources age; the viewer should say so before an agent follows them.
// Mirrors STALE_SOURCE_DAYS in speccify_core.playbook.

export const STALE_SOURCE_DAYS = 180;

export function ageInDays(retrieved: string, today = new Date()): number | null {
  const parsed = Date.parse(`${retrieved}T00:00:00Z`);
  if (Number.isNaN(parsed)) return null;
  const midnight = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  return Math.floor((midnight - parsed) / 86_400_000);
}

export function isStale(retrieved: string, today = new Date()): boolean {
  const age = ageInDays(retrieved, today);
  return age !== null && age > STALE_SOURCE_DAYS;
}

export function describeAge(retrieved: string, today = new Date()): string {
  const age = ageInDays(retrieved, today);
  if (age === null) return "unknown age";
  if (age < 0) return "dated in the future";
  if (age === 0) return "retrieved today";
  if (age === 1) return "1 day old";
  if (age < 60) return `${age} days old`;
  return `${Math.round(age / 30)} months old`;
}
