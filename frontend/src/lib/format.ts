const DATE = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", year: "numeric" });
const DATE_TIME = new Intl.DateTimeFormat("fr-FR", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

/** The API sends naive UTC timestamps. */
function parse(iso: string): Date {
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
}

export function formatDate(iso: string | null | undefined): string {
  return iso ? DATE.format(parse(iso)) : "";
}

export function formatDateTime(iso: string | null | undefined): string {
  return iso ? DATE_TIME.format(parse(iso)) : "";
}

export function percent(part: number, total: number): string {
  return total > 0 ? `${Math.round((100 * part) / total)} %` : "–";
}

export function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
  return `${count} ${count > 1 ? pluralForm : singular}`;
}

export const TIME_CLASS_LABELS: Record<string, string> = {
  bullet: "Bullet",
  blitz: "Blitz",
  rapid: "Rapide",
  classical: "Classique",
  daily: "Différé",
};

export const PLATFORM_LABELS: Record<string, string> = {
  chesscom: "chess.com",
  lichess: "Lichess",
  pgn: "PGN",
};
