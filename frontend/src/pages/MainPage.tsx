import { useEffect, useState } from "react";
import MapView, {
  type IsochroneResult,
  SCORE_LABELS,
} from "../components/MapView";
import { fetchNodes, POI_COLORS, POI_LABELS } from "../api/nodes";
import { type NodeData } from "../types/Node";

const SCORE_LEGEND = [
  { score: 0, color: "var(--score-0)", label: "No amenities (0/6)" },
  { score: 1, color: "var(--score-1)", label: "Very poor (1/6)" },
  { score: 2, color: "var(--score-2)", label: "Poor (2/6)" },
  { score: 3, color: "var(--score-3)", label: "Below average (3/6)" },
  { score: 4, color: "var(--score-4)", label: "Average (4/6)" },
  { score: 5, color: "var(--score-5)", label: "Good (5/6)" },
  { score: 6, color: "var(--score-6)", label: "Excellent (6/6)" },
];

const POI_LEGEND = Object.entries(POI_LABELS).map(([key, label]) => ({
  key,
  label,
  color: POI_COLORS[key],
}));

function MainPage() {
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [result, setResult] = useState<IsochroneResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await fetchNodes();
        setNodes(data);
      } catch (error) {
        console.error("Failed to load nodes:", error);
      }
    }
    loadData();
  }, []);

  const scoreLabel = result
    ? (SCORE_LABELS[result.score] ?? "Unknown")
    : null;

  return (
    <div className="app-container">
      {/* Loading bar */}
      {isLoading && <div className="loading-bar" />}

      {/* Map */}
      <MapView nodes={nodes} onResult={setResult} onLoading={setIsLoading} />

      {/* Overlay UI */}
      <div className="ui-overlay">
        {/* Header */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <div className="header-bar">
            <div className="header-logo">🏙️</div>
            <div className="header-text">
              <h1>15-Minute City Auditor</h1>
              <p>Pune walkability explorer · click anywhere on the map</p>
            </div>
          </div>
        </div>

        {/* Bottom row */}
        <div className="bottom-strip">
          {/* Info panel */}
          <div className="info-panel">
            {isLoading ? (
              <div className="info-panel-hint">
                <div className="pulse-dot" />
                Fetching nearest isochrone…
              </div>
            ) : result ? (
              <div className="info-result">
                <div className="info-result-header">
                  <div
                    className="score-badge"
                    style={{ background: result.colour }}
                  >
                    {result.score}
                  </div>
                  <div className="info-result-title">
                    <div className="label">Walkability Score</div>
                    <div className="value">{scoreLabel}</div>
                  </div>
                </div>
                <div className="info-meta">
                  <span className="meta-chip">
                    Node <span>{result.origin_node}</span>
                  </span>
                  <span className="meta-chip">
                    ~<span>{Math.round(result.distance_m)} m</span> from click
                  </span>
                  <span className="meta-chip">
                    Score <span>{result.score} / 6</span>
                  </span>
                </div>
              </div>
            ) : (
              <div className="info-panel-hint">
                <div className="pulse-dot" />
                Click anywhere on the map to explore
              </div>
            )}
          </div>

          {/* Legends side by side */}
          <div className="legends-group">
            {/* POI legend */}
            <div className="legend-panel">
              <div className="legend-title">POI Categories</div>
              <div className="legend-items">
                {POI_LEGEND.map(({ key, color, label }) => (
                  <div className="legend-item" key={key}>
                    <div
                      className="legend-swatch legend-swatch-circle"
                      style={{ background: color }}
                    />
                    <span>{label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Score legend */}
            <div className="legend-panel">
              <div className="legend-title">Accessibility Score</div>
              <div className="legend-items">
                {SCORE_LEGEND.map(({ score, color, label }) => (
                  <div className="legend-item" key={score}>
                    <div
                      className="legend-swatch"
                      style={{ background: color }}
                    />
                    <span>{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default MainPage;
