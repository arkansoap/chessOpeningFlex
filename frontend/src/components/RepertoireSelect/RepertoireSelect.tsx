import { useCallback, useEffect, useState } from "react";
import { repertoire as repertoireApi } from "../../services/api";
import type { Color, Repertoire } from "../../types";

export interface RepertoireSelectProps {
  /** Id of the selected repertoire, or "" for none. */
  value: string;
  onChange: (repertoireId: string) => void;
  /** Label shown next to the dropdown. */
  label?: string;
  /** Select the first repertoire once the list loads, if none is selected. */
  autoSelectFirst?: boolean;
}

/**
 * Repertoire dropdown with inline creation.
 *
 * Creating a repertoire is offered right here rather than only on a management
 * screen: the need shows up when the user has something to file, and sending
 * them elsewhere would lose the work in progress.
 */
export default function RepertoireSelect({
  value,
  onChange,
  label = "Répertoire",
  autoSelectFirst = false,
}: RepertoireSelectProps) {
  const [repertoires, setRepertoires] = useState<Repertoire[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [color, setColor] = useState<Color>("white");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const reps = await repertoireApi.list();
      setRepertoires(reps);
      return reps;
    } catch {
      setRepertoires([]);
      return [];
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    void load().then((reps) => {
      if (autoSelectFirst && reps.length > 0 && !value) onChange(reps[0].id);
      // With nothing to choose from, open the form instead of showing an
      // empty dropdown the user cannot act on.
      if (reps.length === 0) setCreating(true);
    });
    // Runs once: reloading is driven by create() below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const create = async () => {
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Donnez un nom au répertoire.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const created = await repertoireApi.create({ name: trimmed, color });
      await load();
      onChange(created.id);
      setName("");
      setCreating(false);
    } catch (e: unknown) {
      setError(messageFromError(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="repertoire-select">
      <div className="repertoire-select__row">
        <label>
          {label}&nbsp;
          <select value={value} onChange={(e) => onChange(e.target.value)}>
            <option value="">
              {loaded && repertoires.length === 0
                ? "— Aucun répertoire —"
                : "— Choisir —"}
            </option>
            {repertoires.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} ({r.color === "white" ? "blancs" : "noirs"})
              </option>
            ))}
          </select>
        </label>

        {!creating && (
          <button type="button" onClick={() => setCreating(true)}>
            ＋ Nouveau répertoire
          </button>
        )}
      </div>

      {creating && (
        <div className="repertoire-select__form">
          <label>
            Nom&nbsp;
            <input
              type="text"
              value={name}
              autoFocus
              placeholder="ex. Sicilienne — noirs"
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void create();
                if (e.key === "Escape") setCreating(false);
              }}
            />
          </label>

          <label>
            Couleur&nbsp;
            <select
              value={color}
              onChange={(e) => setColor(e.target.value as Color)}
            >
              <option value="white">Blancs</option>
              <option value="black">Noirs</option>
            </select>
          </label>

          <button type="button" disabled={saving} onClick={() => void create()}>
            {saving ? "Création…" : "Créer"}
          </button>
          {repertoires.length > 0 && (
            <button
              type="button"
              disabled={saving}
              onClick={() => {
                setCreating(false);
                setError(null);
              }}
            >
              Annuler
            </button>
          )}
        </div>
      )}

      {error && <p style={{ color: "#dc2626" }}>Erreur : {error}</p>}
    </div>
  );
}

function messageFromError(e: unknown): string {
  if (e && typeof e === "object" && "response" in e) {
    const resp = (e as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? "Échec de la création.";
  }
  return "Échec de la création.";
}
