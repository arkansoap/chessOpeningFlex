import { NavLink, Route, Routes } from "react-router-dom";
import BuildRepertoirePage from "./pages/BuildRepertoire/BuildRepertoirePage";
import ConsultRepertoirePage from "./pages/ConsultRepertoire/ConsultRepertoirePage";
import TrainingPage from "./pages/Training/TrainingPage";

export default function App() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <h2>ChessOpeningFlex</h2>
        <nav>
          <NavLink to="/build-repertoire">Construire le répertoire</NavLink>
          <NavLink to="/consult-repertoire">Consulter le répertoire</NavLink>
          <NavLink to="/training">Entraînement</NavLink>
        </nav>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<BuildRepertoirePage />} />
          <Route path="/build-repertoire" element={<BuildRepertoirePage />} />
          <Route path="/consult-repertoire" element={<ConsultRepertoirePage />} />
          <Route path="/training" element={<TrainingPage />} />
        </Routes>
      </main>
    </div>
  );
}
