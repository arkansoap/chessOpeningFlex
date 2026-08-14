import { useEffect, useState } from "react";
import RepertoireTree from "../../components/RepertoireTree/RepertoireTree";
import LineEditor from "../../components/LineEditor/LineEditor";
import { repertoire as repertoireApi } from "../../services/api";
import type { Repertoire, RepertoireDetail, RepertoireLine } from "../../types";

/**
 * Page 2: Consult a repertoire.
 *
 * Pick a repertoire, browse its lines as a tree, and edit a selected line
 * (comment, depth, priority) or delete it.
 */
export default function ConsultRepertoirePage() {
  const [repertoires, setRepertoires] = useState<Repertoire[]>([]);
  const [selectedRepId, setSelectedRepId] = useState("");
  const [detail, setDetail] = useState<RepertoireDetail | null>(null);
  const [selectedLine, setSelectedLine] = useState<RepertoireLine | null>(null);

  useEffect(() => {
    void repertoireApi.list().then((reps) => {
      setRepertoires(reps);
      if (reps.length > 0 && !selectedRepId) setSelectedRepId(reps[0].id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedRepId) {
      setDetail(null);
      return;
    }
    void repertoireApi
      .get(selectedRepId)
      .then((d) => {
        setDetail(d);
        setSelectedLine(d.lines[0] ?? null);
      })
      .catch(() => setDetail(null));
  }, [selectedRepId]);

  return (
    <div>
      <h1>Consulter le répertoire</h1>

      <label>
        Répertoire&nbsp;
        <select
          value={selectedRepId}
          onChange={(e) => setSelectedRepId(e.target.value)}
        >
          <option value="">— Choisir —</option>
          {repertoires.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name} ({r.color})
            </option>
          ))}
        </select>
      </label>

      <div style={{ display: "flex", gap: "2rem", marginTop: "1rem", flexWrap: "wrap" }}>
        <section style={{ flex: "1 1 280px" }}>
          <h2>Lignes</h2>
          {detail && (
            <RepertoireTree
              lines={detail.lines}
              selectedLineId={selectedLine?.id}
              onSelectLine={setSelectedLine}
            />
          )}
        </section>

        <section style={{ flex: "2 1 480px" }}>
          {selectedLine ? (
            <LineEditor
              key={selectedLine.id}
              line={selectedLine}
              onUpdated={(updated) => {
                setSelectedLine(updated);
                // refresh detail to keep the tree in sync
                if (selectedRepId) {
                  void repertoireApi
                    .get(selectedRepId)
                    .then(setDetail)
                    .catch(() => undefined);
                }
              }}
              onDeleted={() => {
                setSelectedLine(null);
                if (selectedRepId) {
                  void repertoireApi
                    .get(selectedRepId)
                    .then((d) => {
                      setDetail(d);
                      setSelectedLine(d.lines[0] ?? null);
                    })
                    .catch(() => undefined);
                }
              }}
            />
          ) : (
            <p>Sélectionnez une ligne pour l'éditer.</p>
          )}
        </section>
      </div>
    </div>
  );
}
