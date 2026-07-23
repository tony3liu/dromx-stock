import { useEffect, useRef, useState } from "react";
import type { RunEvent } from "../api/types";
import { withTokenParam } from "../lib/auth";

export type NodeStatus = "pending" | "running" | "done";

export interface StreamState {
  connected: boolean;
  nodes: string[];
  nodeStatus: Record<string, NodeStatus>;
  sections: Record<string, string>; // key -> markdown
  sectionOrder: string[]; // arrival order
  rating: string | null;
  complete: boolean;
  error: string | null;
}

const initial: StreamState = {
  connected: false,
  nodes: [],
  nodeStatus: {},
  sections: {},
  sectionOrder: [],
  rating: null,
  complete: false,
  error: null,
};

// Maps a finished report section key to the pipeline node that produces it, so a
// `section` event also flips that node (and everything before it) to done.
const SECTION_TO_NODE: Record<string, string> = {
  regime_report: "Regime Analyst",
  market_report: "Market Analyst",
  sentiment_report: "Sentiment Analyst",
  news_report: "News Analyst",
  fundamentals_report: "Fundamentals Analyst",
  industry_report: "Industry Analyst",
  signal_aggregation: "Signal Aggregator",
  event_impact: "Event Impact",
  key_question: "Key Question",
  investment_plan: "Research Manager",
  trader_investment_plan: "Trader",
  risk_consensus: "Risk Consensus",
  forecast_report: "Forecast Synthesizer",
  final_trade_decision: "Portfolio Manager",
};

/**
 * Subscribe to a run's SSE stream. Returns live progress + accumulated report
 * sections. Safe to mount for a finished run (backend replays from disk).
 */
export function useRunStream(runId: string | null): StreamState {
  const [state, setState] = useState<StreamState>(initial);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId) {
      setState(initial);
      return;
    }
    setState({ ...initial });
    const es = new EventSource(withTokenParam(`/api/runs/${runId}/stream`));
    esRef.current = es;

    es.onopen = () => setState((s) => ({ ...s, connected: true }));

    es.onmessage = (e) => {
      let ev: RunEvent;
      try {
        ev = JSON.parse(e.data);
      } catch {
        return;
      }
      setState((s) => {
        const next = { ...s };
        if (ev.type === "start") {
          next.nodes = ev.nodes;
          const status: Record<string, NodeStatus> = {};
          ev.nodes.forEach((n, i) => (status[n] = i === 0 ? "running" : "pending"));
          next.nodeStatus = status;
        } else if (ev.type === "section") {
          next.sections = { ...s.sections, [ev.key]: ev.markdown };
          next.sectionOrder = s.sectionOrder.includes(ev.key)
            ? s.sectionOrder
            : [...s.sectionOrder, ev.key];
          // Flip the producing node done + advance the next pending to running.
          const node = SECTION_TO_NODE[ev.key];
          if (node && s.nodes.length) {
            const status = { ...s.nodeStatus };
            const idx = s.nodes.indexOf(node);
            if (idx >= 0) {
              for (let i = 0; i <= idx; i++) status[s.nodes[i]] = "done";
              const nextPending = s.nodes.find((n) => status[n] !== "done");
              if (nextPending) status[nextPending] = "running";
            }
            next.nodeStatus = status;
          }
        } else if (ev.type === "complete") {
          next.rating = ev.rating;
          next.complete = true;
          const status = { ...next.nodeStatus };
          next.nodes.forEach((n) => (status[n] = "done"));
          next.nodeStatus = status;
          es.close();
        } else if (ev.type === "error") {
          next.error = ev.message;
          es.close();
        }
        return next;
      });
    };

    es.onerror = () => {
      // EventSource auto-reconnects; only surface a hard error if not complete.
      setState((s) => (s.complete ? s : { ...s, connected: false }));
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [runId]);

  return state;
}
