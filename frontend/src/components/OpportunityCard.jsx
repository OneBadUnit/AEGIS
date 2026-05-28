// ==========================================
// ARC NEXUS MARKET ANALYZER
// File: frontend/src/components/OpportunityCard.jsx
// Phase: 1 (Clean Rebuild)
// Version: 001
// ==========================================
export default function OpportunityCard({
  item,
  onClick,
  onDelete,
  isSelected = false,
}) {
  const cardNumber = item.id ? `#${item.id}` : "#?";

  function sourceLabel() {
    if (item.subreddit) return item.subreddit;
    if (item.source) return item.source;
    return "unknown source";
  }

  function stopAndRun(e, action) {
    e.stopPropagation();
    action?.();
  }

  return (
    <article
      className={`opp-card ${isSelected ? "selected" : ""}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          onClick?.();
        }
      }}
    >
      <div className="opp-card-header">
        <div>
          <div className="badge-row">
            <span className="badge card-number-badge">{cardNumber}</span>
            <span className="badge mode-badge">
              {item.rejected ? "rejected" : "candidate"}
            </span>
          </div>

          <h3>{item.title || "Untitled post"}</h3>

          <p className="opp-source">
            {item.source || "unknown"} · {sourceLabel()}
          </p>
        </div>
      </div>

      <div className="build-summary">
        <p>
          <strong>User:</strong>{" "}
          {item.target_user || "Not extracted"}
        </p>

        <p>
          <strong>Pain:</strong>{" "}
          {item.pain_point || "Not extracted"}
        </p>

        <p>
          <strong>Context:</strong>{" "}
          {item.context || "Not extracted"}
        </p>

        {item.rejection_reason && (
          <p>
            <strong>Reject reason:</strong>{" "}
            {item.rejection_reason}
          </p>
        )}
      </div>

      <div className="card-actions">
        <button
          type="button"
          className="delete-button"
          onClick={(e) => stopAndRun(e, onDelete)}
        >
          Delete
        </button>

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
      </div>
    </article>
  );
}