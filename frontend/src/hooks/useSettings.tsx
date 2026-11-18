import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Color, Filters } from "../types";

interface Settings {
  /** Side whose games and repertoire are shown. */
  color: Color;
  filters: Filters;
  /** My approximate rating, for the "players of my level" statistics. */
  rating: number;
}

interface SettingsContextValue extends Settings {
  setColor: (color: Color) => void;
  setFilters: (filters: Filters) => void;
  setRating: (rating: number) => void;
}

const STORAGE_KEY = "chessopeningflex.settings";
const DEFAULTS: Settings = {
  color: "white",
  filters: { timeClasses: [], months: 0 },
  rating: 1500,
};

function load(): Settings {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
    return { ...DEFAULTS, ...stored, filters: { ...DEFAULTS.filters, ...stored.filters } };
  } catch {
    return DEFAULTS;
  }
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

/** Colour and game filters, shared by every screen and remembered. */
export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(load);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch {
      // Private browsing: the choice simply does not survive a reload.
    }
  }, [settings]);

  const setColor = useCallback((color: Color) => setSettings((s) => ({ ...s, color })), []);
  const setFilters = useCallback(
    (filters: Filters) => setSettings((s) => ({ ...s, filters })),
    []
  );
  const setRating = useCallback((rating: number) => setSettings((s) => ({ ...s, rating })), []);

  const value = useMemo(
    () => ({ ...settings, setColor, setFilters, setRating }),
    [settings, setColor, setFilters, setRating]
  );
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): SettingsContextValue {
  const value = useContext(SettingsContext);
  if (!value) throw new Error("useSettings must be used inside SettingsProvider");
  return value;
}
