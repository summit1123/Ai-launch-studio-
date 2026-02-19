import type { LaunchHistoryItem } from "../types";

type LaunchHistoryListProps = {
  items: LaunchHistoryItem[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
  queryDraft: string;
  loading: boolean;
  onRefresh: () => Promise<void>;
  onSelect: (requestId: string) => Promise<void>;
  onDelete: (requestId: string) => Promise<void>;
  onPrev: () => Promise<void>;
  onNext: () => Promise<void>;
  onQueryDraftChange: (value: string) => void;
  onSearch: () => Promise<void>;
  onClear: () => Promise<void>;
};

export function LaunchHistoryList({
  items,
  total,
  limit,
  offset,
  hasMore,
  queryDraft,
  loading,
  onRefresh,
  onSelect,
  onDelete,
  onPrev,
  onNext,
  onQueryDraftChange,
  onSearch,
  onClear,
}: LaunchHistoryListProps) {
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = offset + items.length;

  return (
    <section className="panel">
      <div className="historyHead">
        <h3>Launch History</h3>
        <button type="button" onClick={() => void onRefresh()} disabled={loading}>
          {loading ? "갱신 중..." : "새로고침"}
        </button>
      </div>
      <p className="historyMeta">
        총 {total}건 · {pageStart}-{pageEnd}
      </p>
      <div className="historySearch">
        <input
          value={queryDraft}
          onChange={(event) => onQueryDraftChange(event.target.value)}
          placeholder="제품명 또는 KPI 검색"
        />
        <button type="button" onClick={() => void onSearch()} disabled={loading}>
          검색
        </button>
        <button type="button" onClick={() => void onClear()} disabled={loading}>
          초기화
        </button>
      </div>
      <div className="historyPager">
        <button type="button" onClick={() => void onPrev()} disabled={loading || offset <= 0}>
          이전
        </button>
        <button
          type="button"
          onClick={() => void onNext()}
          disabled={loading || !hasMore || items.length < limit}
        >
          다음
        </button>
      </div>
      <ul className="historyList">
        {items.map((item) => (
          <li key={item.request_id}>
            <div className="historyCard">
              <button type="button" onClick={() => void onSelect(item.request_id)}>
                <div className="historyLine">
                  <strong>{item.product_name}</strong>
                  <span>{item.mode}</span>
                </div>
                <p>{item.core_kpi}</p>
                <small>{new Date(item.created_at).toLocaleString("ko-KR")}</small>
              </button>
              <button
                type="button"
                className="dangerGhost"
                onClick={() => void onDelete(item.request_id)}
              >
                삭제
              </button>
            </div>
          </li>
        ))}
        {items.length === 0 && <li className="historyEmpty">저장된 실행 이력이 없습니다.</li>}
      </ul>
    </section>
  );
}
