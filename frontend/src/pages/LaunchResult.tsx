import { AgentTimeline } from "../components/AgentTimeline";
import { AssetPreview } from "../components/AssetPreview";
import type { LaunchPackage } from "../types";

type LaunchResultProps = {
  launchPackage: LaunchPackage;
};

export function LaunchResult({ launchPackage }: LaunchResultProps) {
  return (
    <section className="resultGrid">
      <article className="panel" style={{ padding: '40px' }}>
        <h2 className="section-title">Launch Package Summary</h2>
        <div style={{ display: 'grid', gap: '32px', marginTop: '24px' }}>
          <div className="result-item">
            <span className="result-label">Request ID</span>
            <div className="result-value" style={{ fontSize: '0.8rem', opacity: 0.6 }}>{launchPackage.request_id}</div>
          </div>
          
          <div className="result-item">
            <div className="result-label">Research Analysis</div>
            <p className="result-text">{launchPackage.research_summary.summary}</p>
          </div>
          
          <div className="result-item">
            <div className="result-label">Product Strategy</div>
            <p className="result-text">{launchPackage.product_strategy.summary}</p>
          </div>
          
          <div className="result-item">
            <div className="result-label">Launch Roadmap</div>
            <p className="result-text">{launchPackage.launch_plan.summary}</p>
          </div>
          
          <div className="result-item">
            <div className="result-label">Marketing Campaign</div>
            <p className="result-text">{launchPackage.campaign_strategy.summary}</p>
          </div>
        </div>
      </article>

      <AssetPreview assets={launchPackage.marketing_assets} />
      <AgentTimeline timeline={launchPackage.timeline} />
    </section>
  );
}

