import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ErrorNote, JobProgress, PageHeader } from "../components/common";
import { useAsync } from "../hooks/useAsync";
import { useJob } from "../hooks/useJob";
import { PLATFORM_LABELS, formatDateTime, plural } from "../lib/format";
import {
  analysis as analysisApi,
  errorMessage,
  games as gamesApi,
  training as trainingApi,
} from "../services/api";

/**
 * Home: where my games come from (accounts, sync, PGN files) and the engine
 * analysis that feeds the other screens.
 */
export default function HomePage() {
  const accounts = useAsync(() => gamesApi.accounts(), []);
  const summary = useAsync(() => gamesApi.summary(), []);
  const analysis = useAsync(() => analysisApi.status(), []);
  const training = useAsync(() => trainingApi.stats(), []);

  const [chesscom, setChesscom] = useState("");
  const [lichess, setLichess] = useState("");
  const [firstImport, setFirstImport] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [pgnPlayer, setPgnPlayer] = useState("");
  const [pgnMessage, setPgnMessage] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (accounts.data) {
      setChesscom(accounts.data.chesscom?.username ?? "");
      setLichess(accounts.data.lichess?.username ?? "");
    }
  }, [accounts.data]);

  const sync = useJob(gamesApi.syncStatus, () => {
    summary.reload();
    accounts.reload();
    analysis.reload();
  });
  const engine = useJob(
    () => analysisApi.status().then((s) => s.job),
    () => analysis.reload()
  );

  const saved =
    (accounts.data?.chesscom?.username ?? "") === chesscom.trim() &&
    (accounts.data?.lichess?.username ?? "") === lichess.trim();
  const hasAccount = Boolean(accounts.data?.chesscom || accounts.data?.lichess);
  const neverSynced =
    hasAccount &&
    !accounts.data?.chesscom?.last_synced_at &&
    !accounts.data?.lichess?.last_synced_at;

  const run = async (action: () => Promise<unknown>) => {
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  const saveAccounts = () =>
    run(async () => {
      accounts.setData(await gamesApi.setAccounts({ chesscom, lichess }));
    });
  const startSync = () =>
    run(async () => {
      if (!saved) accounts.setData(await gamesApi.setAccounts({ chesscom, lichess }));
      sync.track(await gamesApi.sync(neverSynced ? firstImport : undefined));
    });
  const startAnalysis = () => run(async () => engine.track(await analysisApi.run()));

  const uploadPgn = (file: File) =>
    run(async () => {
      setPgnMessage(null);
      const counts = await gamesApi.uploadPgn(await file.text(), pgnPlayer.trim() || undefined);
      setPgnMessage(
        `${plural(counts.imported, "partie importée", "parties importées")} sur ${counts.found}` +
          (counts.unknown_side > 0
            ? ` — ${counts.unknown_side} sans savoir de quel côté tu jouais : indique ton nom dans le fichier.`
            : ".")
      );
      summary.reload();
      analysis.reload();
    });

  const total = summary.data?.games ?? 0;
  const pending = analysis.data?.pending ?? 0;
  const due = training.data
    ? training.data.colors.white.due + training.data.colors.black.due +
      training.data.colors.white.new + training.data.colors.black.new
    : 0;

  return (
    <div className="page">
      <PageHeader title="Accueil" />
      <ErrorNote message={error ?? accounts.error ?? summary.error} />

      {total > 0 && (
        <div className="tiles">
          <Link className="tile" to="/ouvertures">
            <span className="tile__value">{total.toLocaleString("fr-FR")}</span>
            <span className="tile__label">
              parties · {summary.data?.by_color.white} avec les blancs, {summary.data?.by_color.black}{" "}
              avec les noirs
            </span>
          </Link>
          <Link className="tile" to="/fuites">
            <span className="tile__value">{(analysis.data?.total ?? 0) - pending}</span>
            <span className="tile__label">
              positions analysées{pending > 0 ? ` · ${pending} en attente` : ""}
            </span>
          </Link>
          <Link className="tile" to="/entrainement">
            <span className="tile__value">{due}</span>
            <span className="tile__label">coups à réviser ou à apprendre</span>
          </Link>
        </div>
      )}

      <section className="card">
        <h2>1. Mes parties</h2>
        <p className="muted">
          Indique tes noms d'utilisateur : l'app récupère tes parties, puis seulement les nouvelles à
          chaque synchronisation.
        </p>
        <div className="form-grid">
          <label>
            chess.com
            <input value={chesscom} onChange={(e) => setChesscom(e.target.value)} placeholder="nom d'utilisateur" autoCapitalize="none" autoCorrect="off" />
            <AccountHint info={accounts.data?.chesscom} />
          </label>
          <label>
            Lichess
            <input value={lichess} onChange={(e) => setLichess(e.target.value)} placeholder="nom d'utilisateur" autoCapitalize="none" autoCorrect="off" />
            <AccountHint info={accounts.data?.lichess} />
          </label>
        </div>
        {(neverSynced || (!hasAccount && (chesscom || lichess))) && (
          <label className="inline-field">
            Premier import
            <select value={firstImport} onChange={(e) => setFirstImport(Number(e.target.value))}>
              <option value={0}>toutes mes parties</option>
              <option value={24}>les 24 derniers mois</option>
              <option value={12}>les 12 derniers mois</option>
              <option value={3}>les 3 derniers mois</option>
            </select>
          </label>
        )}
        <div className="actions">
          <button
            type="button"
            className="btn btn--primary"
            disabled={sync.running || (!chesscom.trim() && !lichess.trim())}
            onClick={() => void startSync()}
          >
            {sync.running ? "Synchronisation…" : "Synchroniser"}
          </button>
          {!saved && (
            <button type="button" className="btn" onClick={() => void saveAccounts()}>
              Enregistrer les noms
            </button>
          )}
          {sync.running && (
            <button type="button" className="btn btn--ghost" onClick={() => void gamesApi.stopSync().then(sync.track)}>
              Arrêter
            </button>
          )}
        </div>
        <JobProgress job={sync.job} />
        {sync.job?.status === "done" && Number(sync.job.result.deviations ?? 0) > 0 && (
          <p className="note">
            Dans ces nouvelles parties tu t'es écarté de ton répertoire{" "}
            {plural(Number(sync.job.result.deviations), "fois", "fois")} : ces coups sont revenus dans
            l'<Link to="/entrainement">entraînement</Link>. Détail dans{" "}
            <Link to="/repertoire?vue=parties">Répertoire › Dernières parties</Link>.
          </p>
        )}
        {Array.isArray(sync.job?.result.errors) && (
          <p className="error">{(sync.job?.result.errors as string[]).join(" ; ")}</p>
        )}
        {summary.data && total > 0 && (
          <p className="muted">
            {Object.entries(summary.data.by_platform)
              .map(([platform, count]) => `${count} ${PLATFORM_LABELS[platform]}`)
              .join(" · ")}
            {summary.data.by_color.unknown > 0 &&
              ` · ${summary.data.by_color.unknown} sans couleur connue (ignorées)`}
          </p>
        )}

        <details className="details">
          <summary>Importer un fichier PGN</summary>
          <p className="muted">
            Pour des parties jouées ailleurs. Si le fichier ne te désigne pas par un de tes noms
            d'utilisateur, indique sous quel nom tu y apparais.
          </p>
          <div className="actions">
            <input value={pgnPlayer} onChange={(e) => setPgnPlayer(e.target.value)} placeholder="mon nom dans le fichier (facultatif)" />
            <button type="button" className="btn" onClick={() => fileInput.current?.click()}>
              Choisir un fichier…
            </button>
            <input
              ref={fileInput}
              type="file"
              accept=".pgn,.txt"
              hidden
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void uploadPgn(file);
                e.target.value = "";
              }}
            />
          </div>
          {pgnMessage && <p className="note">{pgnMessage}</p>}
        </details>
      </section>

      <section className="card">
        <h2>2. Analyse du moteur</h2>
        <p className="muted">
          Stockfish évalue les positions d'ouverture que tu atteins au moins deux fois et les coups
          que tu y répètes. C'est ce qui alimente <Link to="/fuites">Mes fuites</Link> et les
          évaluations de l'arbre. Chaque position n'est analysée qu'une fois.
        </p>
        {analysis.data && !analysis.data.engine_available ? (
          <p className="error">
            Stockfish n'est pas installé sur le serveur : lance{" "}
            <code>python scripts/fetch_stockfish.py</code> dans <code>backend/</code> (voir le README).
          </p>
        ) : (
          <>
            <div className="actions">
              <button
                type="button"
                className="btn btn--primary"
                disabled={engine.running || pending === 0}
                onClick={() => void startAnalysis()}
              >
                {engine.running
                  ? "Analyse en cours…"
                  : pending > 0
                    ? `Analyser ${plural(pending, "position")}`
                    : "Tout est analysé"}
              </button>
              {engine.running && (
                <button type="button" className="btn btn--ghost" onClick={() => void analysisApi.stop().then(engine.track)}>
                  Arrêter
                </button>
              )}
            </div>
            <JobProgress job={engine.job} />
          </>
        )}
      </section>

      <section className="card">
        <h2>3. Construire et réviser</h2>
        <ol className="steps">
          <li>
            <Link to="/ouvertures">Mes ouvertures</Link> : ce que je joue le plus, et avec quels
            résultats.
          </li>
          <li>
            <Link to="/fuites">Mes fuites</Link> : les coups que je répète et qui me coûtent, avec la
            correction.
          </li>
          <li>
            <Link to="/repertoire">Répertoire</Link> : un brouillon tiré de mes parties, puis les
            trous à combler.
          </li>
          <li>
            <Link to="/entrainement">Entraînement</Link> : quelques minutes par jour pour retenir
            mes coups.
          </li>
        </ol>
      </section>
    </div>
  );
}

function AccountHint({ info }: { info: { last_synced_at: string | null } | null | undefined }) {
  if (!info) return null;
  return (
    <span className="hint">
      {info.last_synced_at
        ? `Dernière synchro : ${formatDateTime(info.last_synced_at)}`
        : "Jamais synchronisé"}
    </span>
  );
}
