import { useState } from "react";
import { Brain, Video, Palette, CheckCircle, ArrowRight, Zap, Plus, Minus, Rocket, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const PARTNER_LOGOS = [
  "리서치", "전략", "카피", "포스터", "영상", "보이스", "측정"
];

const PRICING_PLANS = [
  {
    name: "스타터",
    price: "무료",
    priceNote: "계정당 1회 런칭 패키지",
    features: ["초기 정보 입력 1회", "시장 스냅샷 + 전략 옵션", "카피·포스터·영상 프롬프트·보이스 스크립트", "결과 다운로드 1회"],
    cta: "무료 체험 시작",
    available: true,
    accent: "var(--muted)"
  },
  {
    name: "프로",
    price: "출시 예정",
    priceNote: "MVP 종료 후 오픈",
    features: ["런칭 패키지 생성 무제한", "영상 생성 크레딧 확대", "포스터·영상 프롬프트 커스터마이징", "채널별 콘텐츠 변형 자동 생성", "결과 저장·재조회"],
    cta: "오픈 준비중",
    available: false,
    accent: "var(--accent)",
    popular: true
  },
  {
    name: "오토파일럿",
    price: "출시 예정",
    priceNote: "로드맵",
    features: ["에이전트 반복 검토 루프(초안→피드백→개선)", "재고·매출 신호 기반 캠페인 제안", "온라인 스토어 상품 등록 자동화", "주간 성과 리포트 자동 생성"],
    cta: "오픈 준비중",
    available: false,
    accent: "#f59e0b",
    roadmap: true
  },
  {
    name: "엔터프라이즈",
    price: "문의",
    priceNote: "요구사항 기반 맞춤 견적",
    features: ["팀별 워크플로우 맞춤 구성", "보안/권한 정책 커스터마이징", "전담 온보딩·운영 지원", "SLA 기반 기술 지원"],
    cta: "오픈 준비중",
    available: false,
    accent: "#a855f7"
  }
];

const FAQS = [
  { q: "어떤 팀에게 잘 맞나요?", a: "이미 제품을 판매/운영 중인 사업자, 브랜드팀, 마케팅팀이 주간 프로모션 방향을 빠르게 정리할 때 가장 효과적입니다." },
  { q: "결과물에는 무엇이 포함되나요?", a: "시장 스냅샷, 포지셔닝/메시지 옵션, 주간 실행 체크리스트, 카피/포스터/영상 프롬프트/보이스 스크립트, KPI/A-B 테스트 계획이 한 패키지로 제공됩니다." },
  { q: "입력 방식은 어떤가요?", a: "현재 MVP는 텍스트 대화 기반으로 브리프를 수집하며, 자연어 입력을 그대로 이해해 필요한 정보를 멀티턴으로 누적합니다." }
];

const WORKFLOW_STEPS = [
  { step: "01", title: "입력 정보 수집", desc: "챗봇 대화로 목표, 타깃, 채널, 예산 정보를 빠르게 수집합니다.", icon: <Zap size={24} />, agents: "플래너 에이전트" },
  { step: "02", title: "시장 신호 분석", desc: "수요 신호, 경쟁 포지셔닝, 채널 벤치마크를 근거와 함께 정리합니다.", icon: <Brain size={24} />, agents: "리서치 에이전트" },
  { step: "03", title: "전략·콘텐츠 생성", desc: "메시지 옵션과 주간 플랜을 만들고 카피/포스터/영상/보이스 소재를 동시에 생성합니다.", icon: <Palette size={24} />, agents: "전략·크리에이티브·보이스" },
  { step: "04", title: "패키지 저장·재사용", desc: "결과를 구조화해 저장하고 KPI, A-B 테스트, 다음 입력 가이드까지 연결합니다.", icon: <Video size={24} />, agents: "오케스트레이터" },
];

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8090/api";
const ASSET_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, "");
const LUMI_WELCOME_REEL =
  `${ASSET_BASE_URL}/static/assets/lumi_sora_12x2_connected_v5_narr_bgm.mp4?v=20260220-sora-12x2-v6-wide-crop`;

type HomeProps = {
  onStart: () => void;
};

export function Home(props: HomeProps) {
  const [activeFaq, setActiveFaq] = useState<number | null>(null);
  const introVideoSrc = LUMI_WELCOME_REEL;
  const handlePlanCta = (available: boolean) => {
    if (available) {
      props.onStart();
      return;
    }
    window.alert("현재 MVP는 무료 플랜만 이용 가능합니다.\n나머지 플랜은 오픈 준비중입니다.");
  };


  return (
    <div className="container" style={{ marginTop: '72px' }}>
      <div className="grid-bg" />
      
      {/* Hero Section */}
      <motion.section 
        className="landing-hero"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
      >
        <motion.div 
          className="eyebrow" 
          style={{ marginBottom: '24px' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          이미 판매 중인 제품을 위한 프로모션 코파일럿
        </motion.div>
        <h1>
          복잡한 기획 없이도,<br />
          <span style={{ color: 'var(--accent)' }}>바로 쓰는 런칭 패키지</span>
        </h1>
        <p>
          대화로 입력 정보를 받으면 시장 리서치부터 전략, 카피·포스터·영상·보이스 소재,
          KPI 체크리스트까지 한 번에 완성합니다.
        </p>
        <div className="cta-group">
          <button className="btn-primary" onClick={() => props.onStart()}>
            지금 시작하기 <ArrowRight size={20} style={{ marginLeft: '8px' }} />
          </button>
          <button className="btn-secondary" onClick={() => window.scrollTo({ top: 900, behavior: 'smooth' })}>
            기능 둘러보기
          </button>
        </div>

        {/* Video Showcase */}
        <motion.div 
          id="vision"
          className="video-showcase video-showcase-vertical"
          style={{ scrollMarginTop: '100px' }}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5, duration: 1 }}
        >
          <div className="video-label">
            <span className="pulse-dot"></span>
            루미 쇼케이스
          </div>
          <video
            src={introVideoSrc}
            controls
            preload="metadata"
            loop
            playsInline
          />
        </motion.div>
      </motion.section>



      {/* Social Proof (Marquee) */}
      <section style={{ marginTop: '100px', padding: '60px 0' }}>
        <p style={{ textAlign: 'center', color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '32px', fontWeight: 600, letterSpacing: '0.05em' }}>
          핵심 기능
        </p>
        <div style={{ overflow: 'hidden', whiteSpace: 'nowrap', position: 'relative' }}>
          <motion.div 
            style={{ display: 'inline-flex', gap: '80px' }}
            animate={{ x: [0, -1000] }}
            transition={{ repeat: Infinity, duration: 30, ease: "linear" }}
          >
            {[...PARTNER_LOGOS, ...PARTNER_LOGOS].map((logo, idx) => (
              <span key={idx} style={{ color: 'var(--muted)', fontSize: '1.5rem', fontWeight: 800, opacity: 0.5 }}>{logo}</span>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Workflow Visualization Section */}
      <section style={{ marginTop: '160px', position: 'relative' }}>
        <div style={{ textAlign: 'center', marginBottom: '80px' }}>
          <div className="eyebrow">작동 방식</div>
          <h2 style={{ fontSize: '3rem', fontWeight: 800, marginTop: '16px' }}>입력에서 런칭 패키지까지 한 번에</h2>
          <p style={{ color: 'var(--muted)', fontSize: '1.2rem', maxWidth: '700px', margin: '16px auto 0' }}>
            리서치 → 전략 → 콘텐츠 생성 흐름으로
            실무에 바로 쓰는 결과를 만듭니다.
          </p>
        </div>

        <div className="workflow-container">
          <div className="workflow-line" />
          {WORKFLOW_STEPS.map((item, idx) => (
            <motion.div 
              key={idx}
              className="workflow-item"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ delay: idx * 0.2 }}
            >
              <div className="workflow-dot">
                <div className="dot-inner" />
              </div>
              <div className="glass-panel workflow-card">
                <div className="workflow-step-num">{item.step}</div>
                <div className="workflow-icon">{item.icon}</div>
                <h3>{item.title}</h3>
                <p>{item.desc}</p>
                <div className="workflow-agents">
                  <span className="sparkle-icon"><Sparkles size={12} /></span>
                  {item.agents}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Feature Grid */}
      <div className="feature-grid" id="features" style={{ scrollMarginTop: '100px' }}>
        <div className="glass-panel feature-card">
          <div className="icon-wrapper" style={{ background: 'rgba(56, 189, 248, 0.1)' }}>
            <Brain size={32} color="var(--accent)" />
          </div>
          <h3>시장 근거가 있는 전략</h3>
          <p>수요·경쟁·채널 신호를 함께 읽고, 지금 가장 효과적인 메시지와 우선순위를 제안합니다.</p>
          <div className="model-badge">전략 에이전트</div>
        </div>
        <div className="glass-panel feature-card">
          <div className="icon-wrapper" style={{ background: 'rgba(14, 165, 233, 0.1)' }}>
            <Video size={32} color="#0ea5e9" />
          </div>
          <h3>채널별 콘텐츠 자동 생성</h3>
          <p>카피, 포스터 스펙, 영상 프롬프트, 보이스 스크립트를 채널 톤에 맞춰 빠르게 만듭니다.</p>
          <div className="model-badge">크리에이티브 에이전트</div>
        </div>
        <div className="glass-panel feature-card">
          <div className="icon-wrapper" style={{ background: 'rgba(139, 92, 246, 0.1)' }}>
            <Palette size={32} color="#8b5cf6" />
          </div>
          <h3>결과 저장과 재활용</h3>
          <p>완성된 패키지를 구조화 저장하고, 이전 결과를 불러와 다음 캠페인에 바로 이어갑니다.</p>
          <div className="model-badge">런칭 패키지 아카이브</div>
        </div>
      </div>

      {/* Pricing Section */}
      <section style={{ marginTop: '160px' }} id="pricing">
        <div style={{ textAlign: 'center', marginBottom: '80px' }}>
          <div className="eyebrow">요금 플랜</div>
          <h2 style={{ fontSize: '3rem', fontWeight: 800, marginTop: '16px' }}>팀 크기에 맞는 간단한 요금제</h2>
          <p style={{ color: 'var(--muted)', fontSize: '1.2rem' }}>지금 필요한 기능부터 시작하고, 운영 자동화가 필요해지면 단계적으로 확장하세요.</p>
          <p style={{ color: 'var(--muted)', fontSize: '0.92rem', marginTop: '10px', opacity: 0.85 }}>
            오토파일럿 플랜의 재고/스토어/매출 자동화 기능은 로드맵 항목입니다.
          </p>
        </div>

        <div className="pricing-grid">
          {PRICING_PLANS.map((plan) => (
            <div key={plan.name} className={`glass-panel pricing-card ${plan.popular ? 'popular-card' : ''}`}>
              {plan.popular && <div className="popular-badge">가장 많이 선택</div>}
              {plan.roadmap && (
                <div className="roadmap-badge">로드맵</div>
              )}
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: plan.accent, marginBottom: '8px' }}>{plan.name}</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', flexWrap: 'wrap', marginBottom: '24px' }}>
                <span style={{ fontSize: '3.2rem', fontWeight: 900, lineHeight: 1.1 }}>{plan.price}</span>
                <span style={{ fontSize: '1rem', color: 'var(--muted)' }}>{plan.priceNote}</span>
              </div>
              <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 40px', display: 'grid', gap: '12px' }}>
                {plan.features.map(f => (
                  <li key={f} style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--muted)' }}>
                    <CheckCircle size={16} color={plan.accent} /> {f}
                  </li>
                ))}
              </ul>
              <button 
                className={plan.popular ? "btn-primary" : "btn-secondary"} 
                style={{ width: '100%', padding: '14px' }}
                onClick={() => handlePlanCta(plan.available)}
              >
                {plan.cta}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ Section */}
      <section style={{ marginTop: '160px', maxWidth: '800px', margin: '160px auto 0' }} id="faq">
        <div style={{ textAlign: 'center', marginBottom: '60px' }}>
          <h2 style={{ fontSize: '2.5rem', fontWeight: 800 }}>자주 묻는 질문</h2>
        </div>
        <div style={{ display: 'grid', gap: '16px' }}>
          {FAQS.map((faq, idx) => (
            <div key={idx} className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
              <button 
                onClick={() => setActiveFaq(activeFaq === idx ? null : idx)}
                style={{ width: '100%', padding: '24px', background: 'none', border: 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', color: '#fff', textAlign: 'left' }}
              >
                <span style={{ fontSize: '1.1rem', fontWeight: 700 }}>{faq.q}</span>
                {activeFaq === idx ? <Minus size={20} color="var(--accent)" /> : <Plus size={20} />}
              </button>
              <AnimatePresence>
                {activeFaq === idx && (
                  <motion.div 
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    style={{ background: 'rgba(255,255,255,0.02)', borderTop: '1px solid var(--surface-border)' }}
                  >
                    <div style={{ padding: '24px', color: 'var(--muted)', lineHeight: 1.6 }}>{faq.a}</div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </section>

      {/* Trust Badge */}
      <section style={{ marginTop: '160px', textAlign: 'center' }}>
        <h2 className="section-title" style={{ justifyContent: 'center' }}>이번 주 런칭 플랜, 더 빠르게</h2>
        <p style={{ color: 'var(--muted)', maxWidth: '800px', margin: '0 auto 40px', fontSize: '1.2rem' }}>
          기획 문서보다 실행 결과가 먼저 필요하다면,
          AI Launch Studio에서 바로 시작하세요.
        </p>
        <button className="btn-primary" style={{ padding: '20px 60px', fontSize: '1.4rem' }} onClick={() => props.onStart()}>
          런칭 패키지 만들기 <Zap size={24} style={{ marginLeft: '8px' }} />
        </button>
        <div style={{ marginTop: '40px' }}>
          <div className="glass-panel" style={{ display: 'inline-block', padding: '12px 24px', borderRadius: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle size={18} color="var(--accent)" />
              <span style={{ color: '#fff', fontWeight: 700 }}>한 번의 입력으로 전략부터 콘텐츠까지 연결되는 실무형 워크스페이스</span>
            </div>
          </div>
        </div>
      </section>

      <footer style={{ marginTop: '160px', padding: '80px 0 40px', borderTop: '1px solid var(--surface-border)', color: 'var(--muted)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '48px', textAlign: 'left', marginBottom: '60px' }}>
          <div>
            <div style={{ color: '#fff', fontWeight: 800, fontSize: '1.2rem', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Rocket size={24} color="var(--accent)" /> AI Launch Studio
            </div>
            <p style={{ fontSize: '0.9rem' }}>판매 중인 제품을 위한 런칭·프로모션 코파일럿.</p>
          </div>
          <div>
            <h4 style={{ color: '#fff', marginBottom: '20px' }}>제품</h4>
            <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: '12px', fontSize: '0.9rem' }}>
              <li>기능 소개</li>
              <li>요금제</li>
              <li>텍스트 대화 입력</li>
              <li>실행 패키지 저장</li>
            </ul>
          </div>
          <div>
            <h4 style={{ color: '#fff', marginBottom: '20px' }}>리소스</h4>
            <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: '12px', fontSize: '0.9rem' }}>
              <li>문서</li>
              <li>실행 가이드</li>
              <li>고객 사례</li>
              <li>업데이트 노트</li>
            </ul>
          </div>
          <div>
            <h4 style={{ color: '#fff', marginBottom: '20px' }}>정책</h4>
            <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: '12px', fontSize: '0.9rem' }}>
              <li>개인정보 처리방침</li>
              <li>이용약관</li>
              <li>쿠키 정책</li>
            </ul>
          </div>
        </div>
        <div style={{ textAlign: 'center', fontSize: '0.85rem' }}>
          <p>© 2026 AI Launch Studio. 모든 권리 보유.</p>
        </div>
      </footer>
    </div>
  );
}
