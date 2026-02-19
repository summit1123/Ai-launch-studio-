import { AlertCircle } from "lucide-react";
import { useEffect, useState } from "react";

import {
  deleteLaunchHistory,
  getLaunchHistory,
  listLaunchHistory,
  runLaunch,
} from "../api/client";
import { LaunchHistoryList } from "../components/LaunchHistoryList";
import type { LaunchBrief, LaunchHistoryItem, LaunchPackage } from "../types";
import { LaunchForm } from "./LaunchForm";
import { LaunchResult } from "./LaunchResult";

const HISTORY_LIMIT = 10;
const ESTIMATED_RUN_SECONDS = 150;
const RUN_STAGES = [
  { threshold: 0, label: "브리프 분석", hint: "Research/MD/Dev 에이전트 병렬 실행" },
  { threshold: 20, label: "전략 합성", hint: "Planner/Marketer/Biz Planning 통합" },
  { threshold: 45, label: "콘텐츠 초안", hint: "영상 스크립트, 포스터, 상품 카피 생성" },
  { threshold: 70, label: "영상 렌더링", hint: "Sora 렌더링 및 파일 저장" },
] as const;

type DashboardProps = {
  prefillBrief?: LaunchBrief | null;
};

function formatElapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remain = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remain).padStart(2, "0")}`;
}

export function Dashboard({ prefillBrief = null }: DashboardProps) {
  const [runLoading, setRunLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [launchPackage, setLaunchPackage] = useState<LaunchPackage | null>(null);
  const [historyItems, setHistoryItems] = useState<LaunchHistoryItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [historyHasMore, setHistoryHasMore] = useState(false);
  const [historyQuery, setHistoryQuery] = useState("");
  const [historyQueryDraft, setHistoryQueryDraft] = useState("");
  const [runElapsedSeconds, setRunElapsedSeconds] = useState(0);
  const [runAbortController, setRunAbortController] = useState<AbortController | null>(
    null
  );

  const activeStageIndex = RUN_STAGES.reduce((currentIndex, stage, index) => {
    if (runElapsedSeconds >= stage.threshold) {
      return index;
    }
    return currentIndex;
  }, 0);
  const progress = Math.min(
    95,
    Math.max(6, Math.round((runElapsedSeconds / ESTIMATED_RUN_SECONDS) * 100))
  );

  const refreshHistory = async (
    nextOffset = historyOffset,
    nextQuery = historyQuery
  ) => {
    setHistoryLoading(true);
    try {
      const history = await listLaunchHistory(HISTORY_LIMIT, nextOffset, nextQuery);
      setHistoryItems(history.items);
      setHistoryTotal(history.total);
      setHistoryOffset(history.offset);
      setHistoryHasMore(history.has_more);
      setHistoryQuery(history.query);
      setHistoryQueryDraft(history.query);
    } catch (err) {
      const message = err instanceof Error ? err.message : "히스토리 조회 실패";
      setError(message);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleSubmit = async (brief: LaunchBrief) => {
    const controller = new AbortController();

    setRunAbortController(controller);
    setRunLoading(true);
    setError(null);
    setRunElapsedSeconds(0);
    try {
      const response = await runLaunch(
        { brief, mode: "standard" },
        { signal: controller.signal }
      );
      setLaunchPackage(response.package);
      await refreshHistory(0, historyQuery);
    } catch (err) {
      const isAbortError = err instanceof Error && err.name === "AbortError";
      const message = isAbortError
        ? "생성을 취소했습니다. 다시 실행할 수 있습니다."
        : err instanceof Error
          ? err.message
          : "알 수 없는 오류";
      setError(message);
    } finally {
      setRunLoading(false);
      setRunAbortController(null);
    }
  };

  const handleSelectHistory = async (requestId: string) => {
    setDetailLoading(true);
    setError(null);
    try {
      const response = await getLaunchHistory(requestId);
      setLaunchPackage(response.package);
    } catch (err) {
      const message = err instanceof Error ? err.message : "이력 상세 조회 실패";
      setError(message);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDeleteHistory = async (requestId: string) => {
    setHistoryLoading(true);
    setError(null);
    try {
      await deleteLaunchHistory(requestId);
      if (launchPackage?.request_id === requestId) {
        setLaunchPackage(null);
      }

      const candidateOffset =
        historyItems.length === 1 && historyOffset > 0
          ? Math.max(0, historyOffset - HISTORY_LIMIT)
          : historyOffset;
      await refreshHistory(candidateOffset, historyQuery);
    } catch (err) {
      const message = err instanceof Error ? err.message : "이력 삭제 실패";
      setError(message);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handlePrevHistory = async () => {
    if (historyOffset <= 0) {
      return;
    }
    await refreshHistory(Math.max(0, historyOffset - HISTORY_LIMIT), historyQuery);
  };

  const handleNextHistory = async () => {
    if (!historyHasMore) {
      return;
    }
    await refreshHistory(historyOffset + HISTORY_LIMIT, historyQuery);
  };

  const handleSearchHistory = async () => {
    await refreshHistory(0, historyQueryDraft.trim());
  };

  const handleClearHistorySearch = async () => {
    await refreshHistory(0, "");
  };

  const handleCancelRun = () => {
    runAbortController?.abort();
  };

  useEffect(() => {
    void refreshHistory(0, "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!runLoading) {
      setRunElapsedSeconds(0);
      return;
    }

    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      setRunElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);

    return () => {
      window.clearInterval(timer);
    };
  }, [runLoading]);

  useEffect(() => {
    return () => {
      runAbortController?.abort();
    };
  }, [runAbortController]);

  return (
    <main className="container" style={{ marginTop: '80px', paddingBottom: '120px' }}>
      <header className="hero">
        <div className="eyebrow">AI Orchestration Studio</div>
        <h1>AI Launch Studio</h1>
        <p>
          단 하나의 아이디어로 완벽한 제품 런칭 전략과 마케팅 에셋을
          단 몇 분 만에 구축하는 프리미엄 AI 에이전트 스페이스입니다.
        </p>
      </header>

      <div className="glass-panel">
        <h2 className="section-title">New Launch Brief</h2>
        <LaunchForm
          loading={runLoading}
          onSubmit={handleSubmit}
          initialBrief={prefillBrief}
        />
      </div>

      {runLoading && (
        <section className="glass-panel runStatusPanel">
          <div className="runStatusTop">
            <div>
              <h3>런칭 패키지 생성 중</h3>
              <p>{RUN_STAGES[activeStageIndex].hint}</p>
            </div>
            <strong>{formatElapsed(runElapsedSeconds)}</strong>
          </div>
          <div className="runProgressTrack">
            <div className="runProgressFill" style={{ width: `${progress}%` }} />
          </div>
          <ul className="runStageList">
            {RUN_STAGES.map((stage, index) => {
              const state =
                index < activeStageIndex
                  ? "done"
                  : index === activeStageIndex
                    ? "active"
                    : "idle";

              return (
                <li key={stage.label} className={state}>
                  <span>{stage.label}</span>
                </li>
              );
            })}
          </ul>
          <div className="runStatusFoot">
            <p>영상 단계는 보통 1~3분 소요됩니다.</p>
            <button type="button" className="dangerGhost" onClick={handleCancelRun}>
              실행 취소
            </button>
          </div>
        </section>
      )}

      {error && (
        <div className="errorBox">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {launchPackage && (
        <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
          <LaunchResult launchPackage={launchPackage} />
        </div>
      )}

      <div className="glass-panel" style={{ padding: '40px' }}>
        <LaunchHistoryList
          items={historyItems}
          total={historyTotal}
          limit={HISTORY_LIMIT}
          offset={historyOffset}
          hasMore={historyHasMore}
          queryDraft={historyQueryDraft}
          loading={historyLoading || detailLoading || runLoading}
          onRefresh={refreshHistory}
          onSelect={handleSelectHistory}
          onDelete={handleDeleteHistory}
          onPrev={handlePrevHistory}
          onNext={handleNextHistory}
          onQueryDraftChange={setHistoryQueryDraft}
          onSearch={handleSearchHistory}
          onClear={handleClearHistorySearch}
        />
      </div>
    </main>
  );
}
