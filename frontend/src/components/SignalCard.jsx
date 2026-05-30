// ==========================================
// AEGIS
// File: frontend/src/components/SignalCard.jsx
// Phase: 2A (Intelligence Layer — Scoring Visibility)
// Version: 003
// ==========================================

// Maps a significance_score (0.0–1.0) to a display level.
// Returns null when score is too low to override the category border color.
function getSignificanceLevel(score) {
  if (!score || score < 0.20) return null;
  if (score >= 0.70) return "critical";
  if (score >= 0.45) return "high";
  return "medium";
}

export default function SignalCard({ item, onDelete, isPendingDelete, onConfirmDelete, onCancelDelete, isSelected, onToggleSelected, viewMode, onTrack, compact }) {
  const sigLevel = getSignificanceLevel(item.significance_score);
  const sigScore  = item.significance_score ? item.significance_score.toFixed(2) : null;

  // narrative_flags is stored as a JSON-serialized string in the DB.
  let flags = [];
  try {
    if (item.narrative_flags) {
      flags = JSON.parse(item.narrative_flags);
    }
  } catch {
    // Malformed JSON — silently ignore; not a critical display field.
  }

  // Builds a clean "Feed Name · Category" source line.
  // Avoids showing the raw source type ("rss") which is meaningless to analysts.
  function sourceLabel() {
    const name = item.feed_name || "";
    const cat  = item.category ? item.category.replace(/_/g, " ") : "";
    if (name && cat && cat !== "general") return `${name} \u00b7 ${cat}`;
    return name || item.source || "Unknown source";
  }

  // data-significance overrides the category border color when a meaningful
  // significance score is present. Below 0.20, category color is used instead.
  const significanceAttr = sigLevel ? { "data-significance": sigLevel } : {};

  // Compact mode: minimal card used for lead report in compressed clusters.
  if (compact) {
    return (
      <article
        className={`opp-card opp-card--compact${isSelected ? " is-selected" : ""}`}
        data-category={item.category || "general"}
        {...significanceAttr}
      >
        <div className="compact-row">
          {sigLevel && sigScore && (
            <span className={`badge sig-score-badge ${sigLevel}`}>sig {sigScore}</span>
          )}
          <h3 className="compact-title">{item.title || "Untitled"}</h3>
          <p className="compact-source">{sourceLabel()}</p>
        </div>
        <div className="card-actions">
          {isPendingDelete ? (
            <>
              <span className="delete-confirm-label">Delete this signal?</span>
              <button
                type="button"
                className="delete-confirm-btn"
                onClick={(e) => { e.stopPropagation(); onConfirmDelete?.(); }}
              >
                Yes, Delete
              </button>
              <button
                type="button"
                className="delete-cancel-btn"
                onClick={(e) => { e.stopPropagation(); onCancelDelete?.(); }}
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="delete-button"
                onClick={(e) => { e.stopPropagation(); onDelete?.(); }}
              >
                Delete
              </button>
              {viewMode === "live" && (
                <button
                  type="button"
                  className="track-btn"
                  onClick={(e) => { e.stopPropagation(); onTrack?.(); }}
                >
                  Save to Library
                </button>
              )}
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => e.stopPropagation()}
                >
                  View Source
                </a>
              )}
            </>
          )}
        </div>
      </article>
    );
  }

  return (
    <article
      className={`opp-card${isSelected ? " is-selected" : ""}`}
      data-category={item.category || "general"}
      {...significanceAttr}
    >
      <div className="opp-card-header">
        <label
          className="card-checkbox-label"
          title={isSelected ? "Deselect signal" : "Select signal"}
          onClick={(e) => e.stopPropagation()}
        >
          <input
            type="checkbox"
            className="card-checkbox"
            checked={!!isSelected}
            onChange={() => onToggleSelected?.()}
          />
        </label>
        <div>
          <div className="badge-row">
            {/* Signal type badges — verified_news is silent; only show non-default types */}
            {item.signal_type === "narrative_pulse" && (
              <span className="badge signal-type-badge pulse">Pulse</span>
            )}
            {item.signal_type === "narrative_integrity" && (
              <span className="badge signal-type-badge integrity">Integrity</span>
            )}

            {/* Significance score — shown only when score is meaningful (≥ 0.20) */}
            {sigLevel && sigScore && (
              <span className={`badge sig-score-badge ${sigLevel}`}>
                sig {sigScore}
              </span>
            )}

            {/* Manipulation risk — shown only when elevated above baseline */}
            {item.manipulation_risk === "medium" && (
              <span className="badge risk-badge medium">Med Risk</span>
            )}
            {item.manipulation_risk === "high" && (
              <span className="badge risk-badge high">High Risk</span>
            )}

            {item.filtered && (
              <span className="badge mode-badge">filtered</span>
            )}
          </div>

          <h3>{item.title || "Untitled"}</h3>

          <p className="opp-source">{sourceLabel()}</p>
        </div>
      </div>

      <div className="build-summary">
        {item.topic && (
          <p>
            <strong>Topic:</strong> {item.topic}
          </p>
        )}

        {item.summary && (
          <p>
            <strong>Summary:</strong> {item.summary}
          </p>
        )}

        {item.framing && (
          <p>
            <strong>Framing:</strong> {item.framing}
          </p>
        )}

        {item.claims && (
          <p>
            <strong>Claims:</strong> {item.claims}
          </p>
        )}

        {/* Narrative flags — shown only when anomalies were detected by the analyzer */}
        {flags.length > 0 && (
          <p>
            <strong>Narrative flags:</strong> {flags.join(", ")}
          </p>
        )}

        {item.filter_reason && (
          <p>
            <strong>Filter reason:</strong> {item.filter_reason}
          </p>
        )}
      </div>

      <div className="card-actions">
        {isPendingDelete ? (
          // Inline confirm prompt — replaces window.confirm() which browsers can silence.
          <>
            <span className="delete-confirm-label">Delete this signal?</span>
            <button
              type="button"
              className="delete-confirm-btn"
              onClick={(e) => { e.stopPropagation(); onConfirmDelete?.(); }}
            >
              Yes, Delete
            </button>
            <button
              type="button"
              className="delete-cancel-btn"
              onClick={(e) => { e.stopPropagation(); onCancelDelete?.(); }}
            >
              Cancel
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              className="delete-button"
              onClick={(e) => {
                e.stopPropagation();
                onDelete?.();
              }}
            >
              Delete
            </button>

            {viewMode === "live" && (
              <button
                type="button"
                className="track-btn"
                onClick={(e) => { e.stopPropagation(); onTrack?.(); }}
                title="Save this report to the Report Library"
              >
                Save to Library
              </button>
            )}

            {item.url && (
              <a
                href={item.url}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
              >
                View Source
              </a>
            )}
          </>
        )}
      </div>
    </article>
  );
}

