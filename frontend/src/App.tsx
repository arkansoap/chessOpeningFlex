import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import HomePage from "./pages/HomePage";
import LeaksPage from "./pages/LeaksPage";
import TrainingPage from "./pages/TrainingPage";
import ExplorerPage from "./pages/explorer/ExplorerPage";
import RepertoirePage from "./pages/repertoire/RepertoirePage";
import { training as trainingApi } from "./services/api";

const NAV: { to: string; label: string; short?: string; icon: string }[] = [
  { to: "/", label: "Accueil", icon: "M3 11.5 12 4l9 7.5M5.5 10v9.5h13V10" },
  { to: "/ouvertures", label: "Mes ouvertures", short: "Ouvertures", icon: "M12 4v6m0 0-6 4v6m6-10 6 4v6M12 10v10" },
  { to: "/fuites", label: "Mes fuites", short: "Fuites", icon: "M12 3.5 21 19.5H3zM12 10v4.5m0 2.5v.5" },
  { to: "/repertoire", label: "Répertoire", icon: "M5 4.5h11a3 3 0 0 1 3 3v12H8a3 3 0 0 1-3-3zm0 12a3 3 0 0 1 3-3h11" },
  { to: "/entrainement", label: "Entraînement", short: "Réviser", icon: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zm0-4a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0-4a1 1 0 1 0 0-2 1 1 0 0 0 0 2z" },
];

/**
 * App shell. The navigation is a bottom bar on a phone, within thumb reach,
 * and a side rail on wider screens.
 */
export default function App() {
  const location = useLocation();
  const [due, setDue] = useState(0);

  // Refreshed on navigation: cheap, and the badge follows what was just done.
  useEffect(() => {
    trainingApi
      .stats()
      .then((stats) =>
        setDue(
          stats.colors.white.due + stats.colors.black.due +
            stats.colors.white.new + stats.colors.black.new
        )
      )
      .catch(() => undefined);
  }, [location.pathname]);

  return (
    <div className="app">
      <nav className="nav" aria-label="Navigation principale">
        <div className="nav__brand">ChessOpeningFlex</div>
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) => `nav__item${isActive ? " nav__item--active" : ""}`}
          >
            <svg viewBox="0 0 24 24" className="nav__icon" aria-hidden="true">
              <path d={item.icon} />
            </svg>
            <span className="nav__label nav__label--full">{item.label}</span>
            <span className="nav__label nav__label--short">{item.short ?? item.label}</span>
            {item.to === "/entrainement" && due > 0 && <span className="badge">{due}</span>}
          </NavLink>
        ))}
      </nav>
      <main className="main">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/ouvertures" element={<ExplorerPage />} />
          <Route path="/fuites" element={<LeaksPage />} />
          <Route path="/repertoire" element={<RepertoirePage />} />
          <Route path="/entrainement" element={<TrainingPage />} />
          <Route path="*" element={<HomePage />} />
        </Routes>
      </main>
    </div>
  );
}
