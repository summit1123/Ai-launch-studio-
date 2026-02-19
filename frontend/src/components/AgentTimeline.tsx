import type { AgentEnvelope } from "../types";

type AgentTimelineProps = {
  timeline: AgentEnvelope[];
};

export function AgentTimeline({ timeline }: AgentTimelineProps) {
  return (
    <section className="panel">
      <h3>Agent Timeline</h3>
      <ul className="timeline">
        {timeline.map((item, index) => (
          <li key={`${item.agent}-${index}`}>
            <div className="timelineHead">
              <strong>{item.agent}</strong>
              <span>{item.stage}</span>
            </div>
            <p>{item.payload.summary}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

