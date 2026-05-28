// frontend/src/components/OpportunityDetail.jsx

export default function OpportunityDetail({
  item,
  onClose,
  onToggleSaved,
  onDelete,
}) {
  if (!item) {
    return null;
  }

  const founderFit = item.founder_fit || {};
  const mvp = item.mvp_plan || {};

  function formatScore(value) {
    const number = Number(value || 0);
    return number.toFixed(2);
  }

  return (
    <aside className="opp-detail">
      <div className="opp-detail-header">
        <div>
          <div className="badge-row">
            {item.build_this && (
              <span className="badge build-badge">BUILD THIS</span>
            )}

            {item.mode && (
              <span className="badge mode-badge">{item.mode}</span>
            )}

            {item.time_sensitive && (
              <span className="badge limited-badge">LIMITED TIME</span>
            )}
          </div>

          <h2>{mvp.build || item.summary || "Untitled opportunity"}</h2>

          <p className="opp-source">
            {item.source || "unknown source"}
            {item.subreddit ? ` · ${item.subreddit}` : ""}
          </p>
        </div>

        <button type="button" onClick={onClose}>
          Close
        </button>
      </div>

      <div className="detail-actions">
        <button
          type="button"
          className={item.is_saved ? "save-button saved" : "save-button"}
          onClick={onToggleSaved}
        >
          {item.is_saved ? "★ Saved" : "☆ Save"}
        </button>

        <button
          type="button"
          className="delete-button"
          onClick={onDelete}
        >
          Delete
        </button>
      </div>

      <section className="build-plan-section">
        <h3>Build Plan</h3>

        <p>
          <strong>Build:</strong>{" "}
          {mvp.build || "Not specified"}
        </p>

        <p>
          <strong>For:</strong>{" "}
          {mvp.for_user || item.job_role || "Unknown user"}
        </p>

        <p>
          <strong>Solves:</strong>{" "}
          {mvp.solves || item.pain_point || "No clear pain point extracted."}
        </p>

        <p>
          <strong>MVP:</strong>{" "}
          {mvp.mvp || item.desired_feature || "Not specified"}
        </p>

        <p>
          <strong>Time to MVP:</strong>{" "}
          {item.time_to_mvp_days || "?"} days
        </p>

        <p>
          <strong>Reality:</strong>{" "}
          {mvp.reality || "No reality check available."}
        </p>

        <p>
          <strong>Action:</strong>{" "}
          {mvp.action || "No next action available."}
        </p>
      </section>

      <section>
        <h3>Signal Summary</h3>
        <p>{item.summary || "No summary available."}</p>
      </section>

      <section>
        <h3>Original Opportunity</h3>

        <p>
          <strong>Pain Point:</strong>{" "}
          {item.pain_point || "No clear pain point extracted."}
        </p>

        <p>
          <strong>Role:</strong>{" "}
          {item.job_role || "Unknown"}
        </p>

        <p>
          <strong>Workflow:</strong>{" "}
          {item.workflow || "Not specified"}
        </p>

        <p>
          <strong>Desired Feature:</strong>{" "}
          {item.desired_feature || "Not specified"}
        </p>
      </section>

      <section>
        <h3>Scoring Breakdown</h3>

        <ul>
          <li>Severity: {item.severity || 0}/10</li>
          <li>Frequency: {item.frequency || 0}/10</li>
          <li>Willingness to Pay: {item.willingness_to_pay || 0}/10</li>
          <li>Solvability: {item.solvability || "unknown"}</li>
          <li>Scope: {item.niche_or_broad || "unknown"}</li>
          <li>Market Accessibility: {item.market_accessibility || 0}/10</li>
          <li>
            <strong>Opportunity Score:</strong>{" "}
            {formatScore(item.opportunity_score)}
          </li>
        </ul>
      </section>

      <section>
        <h3>Founder Fit</h3>

        <ul>
          <li>Founder Fit Score: {formatScore(founderFit.founder_fit_score)}</li>
          <li>Technical Fit: {founderFit.technical_fit || 0}</li>
          <li>Interest Fit: {founderFit.interest_fit || 0}</li>
          <li>Speed to Build: {founderFit.speed_to_build || 0}</li>
          <li>Unfair Advantage: {founderFit.unfair_advantage || 0}</li>
        </ul>

        <p className="founder-reasoning">
          <strong>Reasoning:</strong>{" "}
          {founderFit.reasoning || "No founder-fit reasoning available."}
        </p>
      </section>

      <section className="total-score-section">
        <h3>Total Score</h3>
        <p className="total-score-large">
          {formatScore(item.total_score)}
        </p>
      </section>

      {item.url && (
        <a href={item.url} target="_blank" rel="noreferrer">
          View Original Post
        </a>
      )}
    </aside>
  );
}