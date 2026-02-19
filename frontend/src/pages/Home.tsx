import { useState } from "react";
import { Brain, Video, Palette, CheckCircle, ArrowRight, Zap, Plus, Minus, Rocket, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { LaunchBrief } from "../types";
import { BRIEF_TEMPLATES, cloneBrief } from "../data/briefTemplates";

const PARTNER_LOGOS = [
  "OpenAI", "Anthropic", "Mistral", "Google Cloud", "AWS", "NVIDIA", "Meta AI"
];

const PRICING_PLANS = [
  {
    name: "Starter",
    price: "0",
    features: ["주 3회 패키지 생성", "GPT-4o 기본 모델", "커뮤니티 지원", "기본 마케팅 자산"],
    cta: "무료로 시작하기",
    accent: "var(--muted)"
  },
  {
    name: "Pro",
    price: "49",
    features: ["무제한 패키지 생성", "GPT-5.2 & Sora-2 전용", "우선순위 렌더링", "고해상도 비디오 수출", "1:1 전문가 기술 상담"],
    cta: "Pro 플랜 시작하기",
    accent: "var(--accent)",
    popular: true
  },
  {
    name: "Enterprise",
    price: "Custom",
    features: ["커스텀 에이전트 구축", "온프레미스 배포 옵션", "전담 매니저 배치", "API 무제한 호출", "보안 및 규정 준수 패키지"],
    cta: "영업팀에 문의하기",
    accent: "#a855f7"
  }
];

const FAQS = [
  { q: "에이전트 9종은 어떤 역할을 수행하나요?", a: "기획자, 시장 조사관, UI/UX 디자이너, 카피라이터, 영상 감독 등 각 분야에 특화된 프롬프트와 지식 베이스를 가진 독립적 페르소나들입니다." },
  { q: "Sora-2 영상 생성 성능은 어느 정도인가요?", a: "기존 Sora 대비  물리 법칙 이해도가 40% 향상되었으며, 최대 2분 분량의 시네마틱 홍보 영상을 단일 시퀀스로 생성 가능합니다." },
  { q: "생성된 자료의 저작권은 누구에게 있나요?", a: "귀하의 비즈니스 아이디어를 바탕으로 생성된 모든 글, 이미지, 영상 에셋의 상업적 이용 권한은 전적으로 사용자에게 부여됩니다." }
];

type HomeProps = {
  onStart: (brief?: LaunchBrief) => void;
};

export function Home(props: HomeProps) {
  const [activeFaq, setActiveFaq] = useState<number | null>(null);


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
          Now Integrated with Sora 2.0
        </motion.div>
        <h1>
          Beyond Imagination,<br />
          <span style={{ color: 'var(--accent)' }}>Product Launch</span> Reimagined
        </h1>
        <p>
          단 하나의 아이디어로 9종의 AI 전문 에이전트가 협업하여 
          시장 분석부터 마케팅 영상 제작까지 완벽한 런칭 패키지를 즉시 구축합니다.
        </p>
        <div className="cta-group">
          <button className="btn-primary" onClick={() => props.onStart()}>
            스튜디오 입장하기 <ArrowRight size={20} style={{ marginLeft: '8px' }} />
          </button>
          <button className="btn-secondary" onClick={() => window.scrollTo({ top: 900, behavior: 'smooth' })}>
            기능 살펴보기
          </button>
        </div>

        {/* Video Showcase */}
        <motion.div 
          id="vision"
          className="video-showcase"
          style={{ scrollMarginTop: '100px' }}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5, duration: 1 }}
        >
          <div className="video-label">
            <span className="pulse-dot"></span>
            AI Studio Vision (Sora 2.0)
          </div>
          <video 
            src="http://localhost:8090/static/assets/studio_intro.mp4" 
            autoPlay 
            muted 
            loop 
            playsInline
          />
        </motion.div>
      </motion.section>



      {/* Social Proof (Marquee) */}
      <section style={{ marginTop: '100px', padding: '60px 0' }}>
        <p style={{ textAlign: 'center', color: 'var(--muted)', fontSize: '0.9rem', marginBottom: '32px', fontWeight: 600, letterSpacing: '0.05em' }}>
          STRATEGIC PARTNERS & POWERED BY
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
          <div className="eyebrow">The Orchestration Process</div>
          <h2 style={{ fontSize: '3rem', fontWeight: 800, marginTop: '16px' }}>아이디어가 현실이 되는 순간</h2>
          <p style={{ color: 'var(--muted)', fontSize: '1.2rem', maxWidth: '700px', margin: '16px auto 0' }}>
            단순한 명령이 런칭 패키지로 변하는 9종 에이전트의 정교한 협업 시스템입니다.
          </p>
        </div>

        <div className="workflow-container">
          <div className="workflow-line" />
          {[
            { step: "01", title: "Smart Briefing", desc: "사용자의 한 줄 아이디어를 바탕으로 시장 상황과 핵심 타겟을 즉시 정의합니다.", icon: <Zap size={24} />, agents: "Research Agent" },
            { step: "02", title: "Strategy Synthesis", desc: "9종의 에이전트가 각자의 전문 영역에서 협업하여 최적의 비즈니스 모델을 도출합니다.", icon: <Brain size={24} />, agents: "Planner & Biz-Strategy" },
            { step: "03", title: "Creative Production", desc: "시나리오에 최적화된 마케팅 메시지, 이미지, 브랜드 에셋을 동시다발적으로 생성합니다.", icon: <Palette size={24} />, agents: "Copywriter & Designer" },
            { step: "04", title: "Cinematic Rendering", desc: "Sora 엔진을 통해 현실의 물리 법칙이 살아있는 4K 홍보 영상을 직접 제작합니다.", icon: <Video size={24} />, agents: "Sora Director" },
          ].map((item, idx) => (
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
          <h3>GPT-5.2 Orchestration</h3>
          <p>현존하는 가장 강력한 추론 능력을 가진 에이전트들이 비즈니스 전략과 기술 구현 계획을 입체적으로 수립합니다.</p>
          <div className="model-badge">Logic Engine V5.2</div>
        </div>
        <div className="glass-panel feature-card">
          <div className="icon-wrapper" style={{ background: 'rgba(14, 165, 233, 0.1)' }}>
            <Video size={32} color="#0ea5e9" />
          </div>
          <h3>Sora 2 Cinematic Assets</h3>
          <p>기획안의 시나리오를 바탕으로 현실의 물리 법칙을 완벽히 이해하는 시네마틱 홍보 영상을 Sora-2 엔진이 즉각적으로 렌더링합니다.</p>
          <div className="model-badge">Video Engine Sora-2</div>
        </div>
        <div className="glass-panel feature-card">
          <div className="icon-wrapper" style={{ background: 'rgba(139, 92, 246, 0.1)' }}>
            <Palette size={32} color="#8b5cf6" />
          </div>
          <h3>GPT-Image High Fidelity</h3>
          <p>DALL-E 3를 압도하는 텍스트 렌더링과 디테일로 브랜드 아이덴티티가 살아있는 마케팅 포스터를 제작합니다.</p>
          <div className="model-badge">Vision Engine 1.5</div>
        </div>
      </div>

      {/* Pricing Section */}
      <section style={{ marginTop: '160px' }} id="pricing">
        <div style={{ textAlign: 'center', marginBottom: '80px' }}>
          <div className="eyebrow">Flexible Pricing</div>
          <h2 style={{ fontSize: '3rem', fontWeight: 800, marginTop: '16px' }}>비즈니스 규모에 맞는 최적의 플랜</h2>
          <p style={{ color: 'var(--muted)', fontSize: '1.2rem' }}>단순한 도구를 넘어 최고의 AI 전략 팀을 구독하세요.</p>
        </div>

        <div className="pricing-grid">
          {PRICING_PLANS.map((plan) => (
            <div key={plan.name} className={`glass-panel pricing-card ${plan.popular ? 'popular-card' : ''}`}>
              {plan.popular && <div className="popular-badge">Most Popular</div>}
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: plan.accent, marginBottom: '8px' }}>{plan.name}</div>
              <div style={{ fontSize: '3.5rem', fontWeight: 900, marginBottom: '24px' }}>
                ${plan.price}<span style={{ fontSize: '1rem', color: 'var(--muted)' }}>/mo</span>
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
                onClick={() => props.onStart()}
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
        <h2 className="section-title" style={{ justifyContent: 'center' }}>Ready to Launch Your Vision?</h2>
        <p style={{ color: 'var(--muted)', maxWidth: '800px', margin: '0 auto 40px', fontSize: '1.2rem' }}>
          혁신적인 서비스를 완성하기 위한 마지막 한 조각, AI Launch Studio가 채워드립니다. 
          에이전트 팀과 함께 지금 바로 출발하세요.
        </p>
        <button className="btn-primary" style={{ padding: '20px 60px', fontSize: '1.4rem' }} onClick={() => props.onStart()}>
          지금 무료로 시작하기 <Zap size={24} style={{ marginLeft: '8px' }} />
        </button>
        <div style={{ marginTop: '40px' }}>
          <div className="glass-panel" style={{ display: 'inline-block', padding: '12px 24px', borderRadius: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle size={18} color="var(--accent)" />
              <span style={{ color: '#fff', fontWeight: 700 }}>이미 1,200개 이상의 스타트업이 선택한 인공지능 스튜디오</span>
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
            <p style={{ fontSize: '0.9rem' }}>Visionary AI tools for the future of business and creation.</p>
          </div>
          <div>
            <h4 style={{ color: '#fff', marginBottom: '20px' }}>Product</h4>
            <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: '12px', fontSize: '0.9rem' }}>
              <li>Features</li>
              <li>Pricing</li>
              <li>Sora Integration</li>
              <li>API Access</li>
            </ul>
          </div>
          <div>
            <h4 style={{ color: '#fff', marginBottom: '20px' }}>Resources</h4>
            <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: '12px', fontSize: '0.9rem' }}>
              <li>Documentation</li>
              <li>Success Stories</li>
              <li>Community</li>
              <li>Blog</li>
            </ul>
          </div>
          <div>
            <h4 style={{ color: '#fff', marginBottom: '20px' }}>Legal</h4>
            <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: '12px', fontSize: '0.9rem' }}>
              <li>Privacy Policy</li>
              <li>Terms of Service</li>
              <li>Cookie Policy</li>
            </ul>
          </div>
        </div>
        <div style={{ textAlign: 'center', fontSize: '0.85rem' }}>
          <p>© 2026 AI Launch Studio. All rights reserved. Built for the Future of Commerce.</p>
        </div>
      </footer>
    </div>
  );
}
