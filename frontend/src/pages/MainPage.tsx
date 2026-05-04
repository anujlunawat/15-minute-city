import { useEffect, useState } from "react";
import MapView, { type IsochroneResult } from "../components/MapView";
import {
  fetchNodes,
  geocodeAddress,
  POI_COLORS,
  POI_LABELS,
  SCORE_LABELS,
  CATEGORIES,
  type PoiSummary,
} from "../api/nodes";
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

function MainPage() {
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [result, setResult] = useState<IsochroneResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [summary, setSummary] = useState<PoiSummary | null>(null);
  const [activeCategories, setActiveCategories] = useState<Set<string>>(
    new Set(CATEGORIES)
  );
  const [heatmapOpacity, setHeatmapOpacity] = useState(0.3);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<
    { lat: number; lon: number; display_name: string }[]
  >([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [flyToTarget, setFlyToTarget] = useState<{ lat: number; lon: number } | null>(null);

  useEffect(() => {
    fetchNodes()
      .then(setNodes)
      .catch((e) => console.error("Failed to load nodes:", e));
  }, []);

  // Toggle a POI category filter
  const toggleCategory = (cat: string) => {
    setActiveCategories((prev) => {
      const next = new Set(prev);
      next.has(cat) ? next.delete(cat) : next.add(cat);
      return next;
    });
  };

  // Nominatim address search
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearchLoading(true);
    setSearchResults([]);
    try {
      const results = await geocodeAddress(searchQuery);
      setSearchResults(results.slice(0, 4));
    } catch {
      console.error("Geocode failed");
    } finally {
      setSearchLoading(false);
    }
  };

  const scoreLabel = result ? (SCORE_LABELS[result.score] ?? "Unknown") : null;

  return (
    <div className="app-container">
      {isLoading && <div className="loading-bar" />}

      <MapView
        nodes={nodes}
        onResult={setResult}
        onLoading={setIsLoading}
        onSummary={setSummary}
        activeCategories={activeCategories}
        heatmapOpacity={heatmapOpacity}
        flyToTarget={flyToTarget}
      />

      <div className="ui-overlay">
        {/* ── Top row ── */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-start" }}>
          {/* Header */}
          <div className="header-bar">
            <div className="header-logo">🏙️</div>
            <div className="header-text">
              <h1>15-Minute City Auditor</h1>
              <p>Pune walkability explorer · click anywhere on the map</p>
            </div>
          </div>

          {/* Address search */}
          <div className="search-panel">
            <form onSubmit={handleSearch} className="search-form">
              <input
                className="search-input"
                type="text"
                placeholder="Search address in Pune…"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setSearchResults([]);
                }}
              />
              <button className="search-btn" type="submit" disabled={searchLoading}>
                {searchLoading ? "…" : "↵"}
              </button>
            </form>
            {searchResults.length > 0 && (
              <div className="search-results">
                {searchResults.map((r, i) => (
                  <button
                    key={i}
                    className="search-result-item"
                    onClick={() => {
                      setSearchQuery(r.display_name.split(",")[0]);
                      setSearchResults([]);
                      setFlyToTarget({ lat: r.lat, lon: r.lon });
                    }}
                  >
                    {r.display_name.split(",").slice(0, 2).join(",")}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Bottom row ── */}
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
                  <div className="score-badge" style={{ background: result.colour }}>
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

                {/* POI category summary */}
                {summary && (
                  <div className="poi-summary">
                    {CATEGORIES.map((cat) => {
                      const count = summary[cat] ?? 0;
                      const color = POI_COLORS[cat];
                      return (
                        <div key={cat} className="poi-summary-row">
                          <span
                            className="poi-summary-dot"
                            style={{ background: color }}
                          />
                          <span className="poi-summary-label">
                            {POI_LABELS[cat]}
                          </span>
                          <span
                            className={`poi-summary-count ${count === 0 ? "zero" : ""}`}
                          >
                            {count}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}

              </div>
            ) : (
              <div className="info-panel-hint">
                <div className="pulse-dot" />
                Click anywhere on the map to explore
              </div>
            )}
          </div>

          {/* Right column: controls + legends */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {/* Heatmap opacity slider — uncomment when heatmap is enabled in MapView.tsx
            <div className="control-panel">
              <div className="legend-title">Heatmap Opacity</div>
              <input
                type="range"
                min={0}
                max={0.7}
                step={0.05}
                value={heatmapOpacity}
                onChange={(e) => setHeatmapOpacity(parseFloat(e.target.value))}
                className="opacity-slider"
              />
              <span className="opacity-value">{Math.round(heatmapOpacity * 100)}%</span>
            </div>
            */}

            <div className="legends-group">
              {/* POI filter legend */}
              <div className="legend-panel">
                <div className="legend-title">POI Categories</div>
                <div className="legend-items">
                  {CATEGORIES.map((cat) => (
                    <label key={cat} className="legend-item legend-item-check">
                      <input
                        type="checkbox"
                        checked={activeCategories.has(cat)}
                        onChange={() => toggleCategory(cat)}
                        className="cat-checkbox"
                      />
                      <div
                        className="legend-swatch legend-swatch-circle"
                        style={{
                          background: POI_COLORS[cat],
                          opacity: activeCategories.has(cat) ? 1 : 0.3,
                        }}
                      />
                      <span style={{ opacity: activeCategories.has(cat) ? 1 : 0.5 }}>
                        {POI_LABELS[cat]}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Score legend */}
              <div className="legend-panel">
                <div className="legend-title">Accessibility Score</div>
                <div className="legend-items">
                  {SCORE_LEGEND.map(({ score, color, label }) => (
                    <div className="legend-item" key={score}>
                      <div className="legend-swatch" style={{ background: color }} />
                      <span>{label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default MainPage;
