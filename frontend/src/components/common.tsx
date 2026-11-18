import type { ReactNode } from "react";
import { useSettings } from "../hooks/useSettings";
import { TIME_CLASS_LABELS } from "../lib/format";
import type { JobState } from "../types";

/** Wins / draws / losses as a proportional bar, from my point of view. */
export function ResultBar({ wins, draws, losses }: { wins: number; draws: number; losses: number }) {
  const total = wins + draws + losses;
  if (total === 0) return <div className="resultbar resultbar--empty" />;
  const share = (n: number) => `${(100 * n) / total}%`;
  return (
    <div
      className="resultbar"
      role="img"
      aria-label={`${wins} gains, ${draws} nulles, ${losses} défaites`}
      title={`${wins} gains · ${draws} nulles · ${losses} défaites`}
    >
      {wins > 0 && <span className="resultbar__win" style={{ width: share(wins) }} />}
      {draws > 0 && <span className="resultbar__draw" style={{ width: share(draws) }} />}
      {losses > 0 && <span className="resultbar__loss" style={{ width: share(losses) }} />}
    </div>
  );
}

/** Which side I am looking at: White or Black. Shared by all screens. */
export function ColorToggle() {
  const { color, setColor } = useSettings();
  return (
    <div className="segmented" role="group" aria-label="Couleur">
      {(["white", "black"] as const).map((c) => (
        <button
          key={c}
          type="button"
          className={`segmented__item${color === c ? " segmented__item--active" : ""}`}
          aria-pressed={color === c}
          onClick={() => setColor(c)}
        >
          <span className={`dot dot--${c}`} aria-hidden="true" />
          {c === "white" ? "Blancs" : "Noirs"}
        </button>
      ))}
    </div>
  );
}

const PERIODS = [
  { months: 0, label: "Toutes" },
  { months: 12, label: "12 mois" },
  { months: 6, label: "6 mois" },
  { months: 3, label: "3 mois" },
  { months: 1, label: "1 mois" },
];

/** Time controls and period taken into account. */
export function FiltersBar() {
  const { filters, setFilters } = useSettings();
  const toggle = (timeClass: string) => {
    const active = filters.timeClasses.includes(timeClass);
    setFilters({
      ...filters,
      timeClasses: active
        ? filters.timeClasses.filter((c) => c !== timeClass)
        : [...filters.timeClasses, timeClass],
    });
  };
  return (
    <div className="filters">
      <div className="chips" role="group" aria-label="Cadences">
        {Object.entries(TIME_CLASS_LABELS).map(([value, label]) => (
          <button
            key={value}
            type="button"
            className={`chip${filters.timeClasses.includes(value) ? " chip--active" : ""}`}
            aria-pressed={filters.timeClasses.includes(value)}
            onClick={() => toggle(value)}
          >
            {label}
          </button>
        ))}
      </div>
      <label className="filters__period">
        Période
        <select
          value={filters.months}
          onChange={(e) => setFilters({ ...filters, months: Number(e.target.value) })}
        >
          {PERIODS.map((p) => (
            <option key={p.months} value={p.months}>
              {p.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

/** Progress of a background job of the server. */
export function JobProgress({ job }: { job: JobState | null }) {
  if (!job || job.status === "idle") return null;
  const ratio = job.total > 0 ? Math.min(1, job.done / job.total) : null;
  return (
    <div className={`job job--${job.status}`} role="status">
      {job.status === "running" && (
        <div className="progress">
          <div
            className={`progress__bar${ratio === null ? " progress__bar--indeterminate" : ""}`}
            style={ratio === null ? undefined : { width: `${ratio * 100}%` }}
          />
        </div>
      )}
      <span>
        {job.status === "running" && (job.message || "En cours…")}
        {job.status === "done" && (job.message || "Terminé.")}
        {job.status === "stopped" && "Arrêté."}
        {job.status === "error" && `Erreur : ${job.error}`}
      </span>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {children && <p>{children}</p>}
    </div>
  );
}

export function ErrorNote({ message }: { message: string | null }) {
  return message ? <p className="error" role="alert">{message}</p> : null;
}

export interface TabItem<T extends string> {
  id: T;
  label: string;
  badge?: number;
}

export function Tabs<T extends string>({
  items,
  value,
  onChange,
}: {
  items: TabItem<T>[];
  value: T;
  onChange: (id: T) => void;
}) {
  return (
    <div className="tabs" role="tablist">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="tab"
          aria-selected={value === item.id}
          className={`tabs__item${value === item.id ? " tabs__item--active" : ""}`}
          onClick={() => onChange(item.id)}
        >
          {item.label}
          {item.badge ? <span className="badge">{item.badge}</span> : null}
        </button>
      ))}
    </div>
  );
}

/** Page header: title on the left, controls on the right. */
export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="page-header">
      <h1>{title}</h1>
      {children && <div className="page-header__controls">{children}</div>}
    </header>
  );
}
