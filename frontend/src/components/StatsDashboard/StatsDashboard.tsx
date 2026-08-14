import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  LineChart,
  Line,
  Legend,
} from "recharts";
import { training as trainingApi } from "../../services/api";
import type { MemorizationStat } from "../../types";

export interface StatsDashboardProps {
  repertoireId?: string;
  lineId?: string;
}

/**
 * Memorization statistics dashboard: success rate over time and attempts
 * per line. Data is fetched from /api/v1/training/stats.
 */
export default function StatsDashboard({ repertoireId, lineId }: StatsDashboardProps) {
  const [stats, setStats] = useState<MemorizationStat[]>([]);

  useEffect(() => {
    const params: { repertoire_id?: string; line_id?: string } = {};
    if (repertoireId) params.repertoire_id = repertoireId;
    if (lineId) params.line_id = lineId;
    void trainingApi
      .stats(params)
      .then(setStats)
      .catch(() => setStats([]));
  }, [repertoireId, lineId]);

  if (stats.length === 0) {
    return <p>Aucune statistique disponible pour l'instant.</p>;
  }

  // Chronological order for the time series.
  const timeSeries = [...stats]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((s) => ({
      date: s.date,
      "Taux de réussite (%)": Math.round(s.success_rate * 100),
      Tentatives: s.attempts,
    }));

  // Aggregate attempts per line.
  const perLine = aggregatePerLine(stats);

  return (
    <div className="stats-dashboard">
      <h3>Statistiques de mémorisation</h3>

      <section style={{ height: 260, marginBottom: "2rem" }}>
        <h4>Évolution du taux de réussite</h4>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={timeSeries}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="Taux de réussite (%)"
              stroke="#2563eb"
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </section>

      <section style={{ height: 260 }}>
        <h4>Tentatives par ligne</h4>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={perLine}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="Tentatives" fill="#16a34a" />
          </BarChart>
        </ResponsiveContainer>
      </section>
    </div>
  );
}

function aggregatePerLine(stats: MemorizationStat[]): {
  label: string;
  Tentatives: number;
}[] {
  const byLine = new Map<string, number>();
  for (const s of stats) {
    byLine.set(s.line_id, (byLine.get(s.line_id) ?? 0) + s.attempts);
  }
  return Array.from(byLine.entries()).map(([, attempts], i) => ({
    label: `L${i + 1}`,
    Tentatives: attempts,
  }));
}
