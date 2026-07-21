import { useEffect, useRef, useState } from 'react';
import { SendIcon, SparkIcon } from './components/icons';
import { GraphTab, type Subgraph } from './components/GraphTab';
import { AskTab, ImpactTab, ReplayTab } from './components/tabs';
import type {
  AskExpansion,
  AskResult,
  EditorCtx,
  ImpactReport,
  IndexJob,
  ReplayStep,
  Tab,
} from './types';
import { send } from './vscode';

const TABS: { id: Tab; label: string }[] = [
  { id: 'ask', label: 'Ask' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'graph', label: 'Graph' },
  { id: 'impact', label: 'Impact' },
];

export default function App() {
  const [tab, setTab] = useState<Tab>('ask');
  const [ctx, setCtx] = useState<EditorCtx | null>(null);
  const [model, setModel] = useState<string>('');

  const [askPending, setAskPending] = useState(false);
  const [askTarget, setAskTarget] = useState('');
  const [askQuestion, setAskQuestion] = useState('');
  const [result, setResult] = useState<AskResult | null>(null);
  const [expansion, setExpansion] = useState<AskExpansion | null>(null);

  const [replayPending, setReplayPending] = useState(false);
  const [steps, setSteps] = useState<ReplayStep[]>([]);

  const [impactPending, setImpactPending] = useState(false);
  const [impactTarget, setImpactTarget] = useState('');
  const [report, setReport] = useState<ImpactReport | null>(null);

  const [subgraph, setSubgraph] = useState<Subgraph | null>(null);
  const [index, setIndex] = useState<IndexJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [online, setOnline] = useState<boolean | null>(null); // null = unknown
  const followUp = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const msg = event.data;
      switch (msg?.type) {
        case 'context': setCtx(msg.ctx); break;
        case 'health': setModel(msg.health?.model ?? ''); setOnline(!!msg.health); break;
        case 'tab': setTab(msg.tab); break;
        case 'ask:pending':
          setError(null); setAskPending(true); setResult(null); setExpansion(null);
          setAskTarget(msg.target); setAskQuestion(msg.question); setTab('ask');
          break;
        case 'ask:result': setAskPending(false); setResult(msg.result); break;
        case 'ask:expansion': setExpansion(msg.expansion); break;
        case 'replay:pending': setReplayPending(true); setSteps([]); break;
        case 'replay:result': setReplayPending(false); setSteps(msg.steps); break;
        case 'impact:pending': setImpactPending(true); setReport(null); setImpactTarget(msg.target); setTab('impact'); break;
        case 'impact:result': setImpactPending(false); setReport(msg.report); break;
        case 'graph:result': setSubgraph(msg.subgraph); break;
        case 'index:pending': setIndex({ status: 'queued', detail: 'Starting…', repo: msg.repo } as IndexJob); break;
        case 'index:status': setIndex(msg.job); break;
        case 'error': setError(msg.message); setAskPending(false); setReplayPending(false); setImpactPending(false); break;
      }
    };
    window.addEventListener('message', handler);
    send({ type: 'ready' });
    return () => window.removeEventListener('message', handler);
  }, []);

  // Ask the graph host for the subgraph when the user opens the Graph tab.
  useEffect(() => {
    if (tab === 'graph' && ctx && !subgraph) send({ type: 'graph' });
  }, [tab, ctx, subgraph]);

  const submitFollowUp = () => {
    const q = followUp.current?.value?.trim();
    if (!q) return;
    send({ type: 'ask', question: q });
    if (followUp.current) followUp.current.value = '';
  };

  const indexing = index && index.status !== 'done' && index.status !== 'error';

  return (
    <div className="atlas">
      <div className="header">
        <span className="spark"><SparkIcon /></span>
        ATLAS
        {model && <span className="model-pill">{model}</span>}
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t.id} className={`tab ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="body">
        {online === false && (
          <div className="card" style={{ borderColor: 'var(--atlas-amber)' }}>
            <div className="card-title">Atlas backend not reachable</div>
            <div className="tl-detail" style={{ marginBottom: 8 }}>
              Start it, then reopen this panel:
            </div>
            <div className="pill mono" style={{ display: 'inline-block' }}>./run.sh</div>
            <div className="tl-detail" style={{ marginTop: 8 }}>
              or <span className="mono">docker compose up</span> in <span className="mono">backend/</span>.
              Configure the URL in Settings → <span className="mono">atlas.backendUrl</span>.
            </div>
          </div>
        )}
        {indexing && (
          <div className="status-line"><span className="dot-pulse" /> Indexing {index?.repo}: {index?.detail}</div>
        )}
        {error && <div className="card" style={{ borderColor: 'var(--atlas-red)' }}>{error}</div>}

        {tab === 'ask' && (
          <>
            <div className="ask-input">
              <input value={askQuestion || 'Why is this function implemented this way?'} readOnly />
              <span className="kbd">⌘⏎</span>
            </div>
            <AskTab
              pending={askPending}
              question={askQuestion}
              target={askTarget}
              result={result}
              expansion={expansion}
              onExpand={() => result && send({ type: 'expand', answerId: result.answer_id })}
            />
          </>
        )}

        {tab === 'timeline' && <ReplayTab pending={replayPending} steps={steps} />}
        {tab === 'graph' && <GraphTab subgraph={subgraph} />}
        {tab === 'impact' && <ImpactTab pending={impactPending} target={impactTarget} report={report} />}
      </div>

      <div className="footer">
        <div className="ask-input">
          <input
            ref={followUp}
            placeholder="Ask a follow-up…"
            onKeyDown={(e) => e.key === 'Enter' && submitFollowUp()}
          />
          <button className="send-btn" onClick={submitFollowUp} aria-label="Send">
            <SendIcon />
          </button>
        </div>
      </div>
    </div>
  );
}
