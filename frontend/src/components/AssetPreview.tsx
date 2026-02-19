import { Sparkles } from "lucide-react";
import type { MarketingAssets } from "../types";

type AssetPreviewProps = {
  assets: MarketingAssets;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8090/api";
const ASSET_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, "");

function resolveAssetUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${ASSET_BASE_URL}${path}`;
}

export function AssetPreview({ assets }: AssetPreviewProps) {
  return (
    <section className="glass-panel">
      <h2 className="section-title">AI Generated Assets</h2>
      <div className="assetGrid">
        <article style={{ background: 'rgba(15, 23, 42, 0.4)', borderRadius: '20px', padding: '24px', border: '1px solid rgba(255,255,255,0.05)' }}>
          <h4>🎥 홍보 영상 패키지 (Sora)</h4>
          {assets.video_url ? (
            <div className="media-preview" style={{ borderRadius: '16px', border: '1px solid var(--surface-border)', overflow: 'hidden' }}>
              <video 
                src={resolveAssetUrl(assets.video_url)}
                controls 
                style={{ width: '100%', display: 'block' }}
              />
            </div>
          ) : (
            <div className="media-placeholder" style={{ background: 'rgba(0,0,0,0.5)', height: '220px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', borderRadius: '16px', border: '1px dashed var(--surface-border)', gap: '16px' }}>
              <div className="shimmer" style={{ width: '48px', height: '48px', borderRadius: '50%', border: '3px solid var(--accent-glow)', borderTopColor: 'var(--accent)' }} />
              <div style={{ textAlign: 'center' }}>
                <div style={{ color: '#fff', fontSize: '1rem', fontWeight: 700, marginBottom: '4px' }}>Sora-2 영상 생성 대기 중</div>
                <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>AI 에이전트가 물리 시뮬레이션을 연산하고 있습니다.</div>
              </div>
            </div>
          )}
          <p style={{ marginTop: '1.5rem', color: 'var(--ink)', fontSize: '0.95rem', lineHeight: '1.7', opacity: 0.9 }}>{assets.video_script}</p>
        </article>

        <article style={{ background: 'rgba(15, 23, 42, 0.4)', borderRadius: '20px', padding: '24px', border: '1px solid rgba(255,255,255,0.05)' }}>
          <h4>🎨 마케팅 히어로 포스터</h4>
          {assets.poster_headline && <p style={{ fontSize: '1.2rem', fontWeight: '800', marginBottom: '1rem', background: 'linear-gradient(135deg, #fff 0%, #94a3b8 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{assets.poster_headline}</p>}
          {assets.poster_image_url ? (
            <div className="media-preview" style={{ borderRadius: '16px', border: '1px solid var(--surface-border)', overflow: 'hidden' }}>
              <img 
                src={resolveAssetUrl(assets.poster_image_url)}
                alt="Launch Poster" 
                style={{ width: '100%', display: 'block' }}
              />
            </div>
          ) : (
            <div className="media-placeholder" style={{ background: 'rgba(0,0,0,0.5)', height: '220px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', borderRadius: '16px', border: '1px dashed var(--surface-border)', gap: '16px' }}>
              <Sparkles size={32} color="var(--accent)" className="shimmer" />
              <div style={{ textAlign: 'center' }}>
                <div style={{ color: '#fff', fontSize: '1rem', fontWeight: 700, marginBottom: '4px' }}>히어로 포스터 생성 대기 중</div>
                <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>디자인 에이전트가 브랜드 에셋을 구성하고 있습니다.</div>
              </div>
            </div>
          )}
          <p style={{ marginTop: '1.5rem', color: 'var(--muted)', fontSize: '0.95rem' }}>{assets.poster_brief}</p>
        </article>

        <article style={{ background: 'rgba(15, 23, 42, 0.4)', borderRadius: '20px', padding: '24px', border: '1px solid rgba(255,255,255,0.05)' }}>
          <h4>📝 제품 상세 카피 (Copy)</h4>
          <p style={{ fontSize: '1.05rem', lineHeight: '1.8', color: 'var(--ink)' }}>{assets.product_copy}</p>
          {assets.product_copy_bullets && assets.product_copy_bullets.length > 0 && (
            <ul style={{ marginTop: '1.5rem', paddingLeft: '1.2rem', color: 'var(--muted)', display: 'grid', gap: '8px' }}>
              {assets.product_copy_bullets.map((point, index) => (
                <li key={`${point}-${index}`}>{point}</li>
              ))}
            </ul>
          )}
        </article>
      </div>
    </section>
  );
}
