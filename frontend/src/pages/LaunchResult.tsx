import { AgentTimeline } from "../components/AgentTimeline";
import { AssetPreview } from "../components/AssetPreview";
import type { LaunchPackage } from "../types";

type LaunchResultProps = {
  launchPackage: LaunchPackage;
  showAssets?: boolean;
};

function keyPointList(items: string[]): string {
  if (items.length === 0) {
    return "요약 항목 없음";
  }
  return items.slice(0, 3).join(" / ");
}

export function LaunchResult({ launchPackage, showAssets = false }: LaunchResultProps) {
  return (
    <section className="resultGrid">
      <article className="panel" style={{ padding: "40px" }}>
        <h2 className="section-title">기획 보고서</h2>
        <div style={{ display: "grid", gap: "32px", marginTop: "24px" }}>
          <div className="result-item">
            <span className="result-label">Run ID</span>
            <div className="result-value" style={{ fontSize: "0.8rem", opacity: 0.6 }}>
              {launchPackage.request_id}
            </div>
          </div>

          <div className="result-item">
            <div className="result-label">시장 평가</div>
            <p className="result-text">{launchPackage.research_summary.summary}</p>
            <small style={{ color: "var(--muted)" }}>
              핵심: {keyPointList(launchPackage.research_summary.key_points)}
            </small>
          </div>

          <div className="result-item">
            <div className="result-label">포지셔닝 전략</div>
            <p className="result-text">{launchPackage.product_strategy.summary}</p>
            <small style={{ color: "var(--muted)" }}>
              핵심: {keyPointList(launchPackage.product_strategy.key_points)}
            </small>
          </div>

          <div className="result-item">
            <div className="result-label">실행 로드맵</div>
            <p className="result-text">{launchPackage.launch_plan.summary}</p>
            <small style={{ color: "var(--muted)" }}>
              핵심: {keyPointList(launchPackage.launch_plan.key_points)}
            </small>
          </div>

          <div className="result-item">
            <div className="result-label">캠페인 메시지</div>
            <p className="result-text">{launchPackage.campaign_strategy.summary}</p>
            <small style={{ color: "var(--muted)" }}>
              핵심: {keyPointList(launchPackage.campaign_strategy.key_points)}
            </small>
          </div>

          <div className="result-item">
            <div className="result-label">리스크</div>
            <p className="result-text">
              {launchPackage.risks_and_mitigations.length > 0
                ? launchPackage.risks_and_mitigations.slice(0, 4).join(" / ")
                : "현재 주요 리스크 없음"}
            </p>
          </div>
        </div>
      </article>

      {showAssets ? (
        <AssetPreview assets={launchPackage.marketing_assets} />
      ) : (
        <section className="glass-panel">
          <h2 className="section-title">이벤트/소재 생성 대기</h2>
          <p style={{ marginBottom: 0, color: "var(--muted)" }}>
            기획 보고서 검토 후, 아래 단계에서 포스터/영상 이벤트를 추가 생성하세요.
          </p>
        </section>
      )}
      <AgentTimeline timeline={launchPackage.timeline} />
    </section>
  );
}

