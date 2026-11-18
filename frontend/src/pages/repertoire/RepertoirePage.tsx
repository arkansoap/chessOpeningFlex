import { useSearchParams } from "react-router-dom";
import { ColorToggle, ErrorNote, PageHeader, Tabs } from "../../components/common";
import { useAsync } from "../../hooks/useAsync";
import { useSettings } from "../../hooks/useSettings";
import { percent } from "../../lib/format";
import { repertoire as repertoireApi } from "../../services/api";
import EntriesList from "./EntriesList";
import GapsList from "./GapsList";
import ReviewList from "./ReviewList";
import Tools from "./Tools";

type View = "trous" | "parties" | "coups" | "outils";
const VIEWS: View[] = ["trous", "parties", "coups", "outils"];

/**
 * My repertoire for one colour: how well it covers my real games, where it
 * stops, where I strayed from it, and the tools to grow it.
 */
export default function RepertoirePage() {
  const { color, filters } = useSettings();
  const [params, setParams] = useSearchParams();
  const requested = params.get("vue") as View | null;
  const view: View = requested && VIEWS.includes(requested) ? requested : "trous";

  const rep = useAsync(() => repertoireApi.get(color), [color]);
  const coverage = useAsync(() => repertoireApi.coverage(color, filters), [color, filters]);
  const reload = () => {
    rep.reload();
    coverage.reload();
  };

  const cov = coverage.data;
  return (
    <div className="page">
      <PageHeader title="Répertoire">
        <ColorToggle />
      </PageHeader>
      <ErrorNote message={rep.error ?? coverage.error} />

      <div className="tiles">
        <div className="tile">
          <span className="tile__value">{rep.data?.entries ?? "–"}</span>
          <span className="tile__label">
            coups choisis
            {rep.data && rep.data.new + rep.data.due > 0
              ? ` · ${rep.data.new + rep.data.due} à réviser`
              : ""}
          </span>
        </div>
        <div className="tile">
          <span className="tile__value">{cov ? cov.average_followed.toLocaleString("fr-FR") : "–"}</span>
          <span className="tile__label">de mes coups par partie, en moyenne, suivent le répertoire</span>
        </div>
        <div className="tile">
          <span className="tile__value">{cov ? percent(cov.with_deviation, cov.games) : "–"}</span>
          <span className="tile__label">
            des parties où j'ai joué autre chose que mon coup de répertoire
          </span>
        </div>
      </div>

      <Tabs<View>
        items={[
          { id: "trous", label: "Trous", badge: cov?.gaps.length },
          { id: "parties", label: "Dernières parties" },
          { id: "coups", label: "Mes coups", badge: rep.data?.entries },
          { id: "outils", label: "Outils" },
        ]}
        value={view}
        onChange={(v) => setParams(v === "trous" ? {} : { vue: v }, { replace: true })}
      />

      {view === "trous" && <GapsList coverage={cov} onChanged={reload} />}
      {view === "parties" && <ReviewList />}
      {view === "coups" && <EntriesList data={rep.data} onChanged={reload} />}
      {view === "outils" && <Tools onChanged={reload} />}
    </div>
  );
}
