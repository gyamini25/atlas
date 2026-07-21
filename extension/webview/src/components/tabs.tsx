import { motion } from 'framer-motion';
import type { AskExpansion, AskResult, ImpactReport, ReplayStep } from '../types';
import { send } from '../vscode';
import { sourceIcon } from './icons';
import { Reason, Shimmer, SourceChips, Timeline } from './shared';

// ─── Ask tab ──────────────────────────────────────────────────────────────────
export function AskTab(props: {
  pending: boolean;
  question: string;
  target: string;
  result: AskResult | null;
  expansion: AskExpansion | null;
  onExpand: () => void;
}) {
  const { pending, result, expansion } = props;

  if (pending && !result) {
    return (
      <>
        <div className="status-line"><span className="dot-pulse" /> Atlas is reasoning over {props.target}…</div>
        <Shimmer />
      </>
    );
  }
  if (!result) {
    return (
      <div className="empty">
        <div className="big">✨</div>
        Select a function and run <b>Ask Atlas</b> to reconstruct why it exists.
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
    >
      <div className="card">
        <div className="card-title">
          Atlas Answer
          <span className="confidence">Confidence {Math.round(result.confidence * 100)}%</span>
        </div>
        <div className="summary">{result.summary}</div>

        {result.key_reasons.length > 0 && (
          <>
            <div className="section-label">Key reasons</div>
            <div className="reasons">
              {result.key_reasons.map((r, i) => (
                <Reason key={i} label={r.label} text={r.text} />
              ))}
            </div>
          </>
        )}

        <SourceChips sources={result.sources} />

        {!expansion && (
          <button className="learn-more" onClick={props.onExpand}>
            Learn more →
          </button>
        )}

        {expansion && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }}>
            <div className="section-label">Reasoning</div>
            <div className="reasoning">{expansion.reasoning}</div>

            {expansion.alternatives.length > 0 && (
              <>
                <div className="section-label">Alternatives considered</div>
                <div className="list">
                  {expansion.alternatives.map((a, i) => (
                    <div className="row" key={i}><span className="bullet">–</span><span>{a}</span></div>
                  ))}
                </div>
              </>
            )}

            {expansion.dependencies.length > 0 && (
              <>
                <div className="section-label">Dependencies</div>
                <div className="pill-list">
                  {expansion.dependencies.map((d, i) => (
                    <span className="pill" key={i}>{d}</span>
                  ))}
                </div>
              </>
            )}
          </motion.div>
        )}
      </div>

      {result.timeline_preview.length > 0 && (
        <div className="card">
          <div className="card-title">Decision Timeline</div>
          <Timeline entries={result.timeline_preview} />
        </div>
      )}

      <div className="actions">
        <button className="action" onClick={() => send({ type: 'expand', answerId: result.answer_id })}>
          Explain dependencies
        </button>
        <button className="action" onClick={() => send({ type: 'impact', target: '' })}>
          What breaks if changed?
        </button>
      </div>
    </motion.div>
  );
}

// ─── Timeline / Decision Replay tab ──────────────────────────────────────────
export function ReplayTab(props: { pending: boolean; steps: ReplayStep[] }) {
  if (props.pending && !props.steps.length) {
    return (
      <>
        <div className="status-line"><span className="dot-pulse" /> Reconstructing the evolution…</div>
        <Shimmer />
      </>
    );
  }
  if (!props.steps.length) {
    return (
      <div className="empty">
        <div className="big">🎬</div>
        Run <b>Replay Evolution</b> to watch why this code changed over time.
      </div>
    );
  }
  return (
    <div className="card">
      <div className="card-title">Decision Replay</div>
      <div className="timeline">
        {props.steps.map((step, i) => (
          <motion.div
            className="tl-row"
            key={step.order}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.35, duration: 0.4 }}
          >
            <div className="tl-date">{step.date}</div>
            <div className="tl-rail">
              <span className={`tl-dot ${step.is_incident ? 'incident' : ''}`} />
              <span className="tl-line" />
            </div>
            <div className="tl-body">
              <div className={`tl-title ${step.is_incident ? 'incident' : ''}`}>{step.title}</div>
              <div className="tl-narration">{step.narration}</div>
              {step.sources.length > 0 && (
                <div style={{ marginTop: 6 }}>
                  {step.sources.map((src) => (
                    <button
                      key={src.ref}
                      className="chip"
                      style={{ display: 'inline-flex', marginRight: 6 }}
                      onClick={() => send({ type: 'openSource', source: src })}
                    >
                      <span className={`chip-icon ${src.kind}`}>{sourceIcon(src.kind)}</span>
                      <span className="chip-label">{src.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

// ─── Impact tab ───────────────────────────────────────────────────────────────
export function ImpactTab(props: { pending: boolean; target: string; report: ImpactReport | null }) {
  if (props.pending && !props.report) {
    return (
      <>
        <div className="status-line"><span className="dot-pulse" /> Analysing the blast radius of {props.target}…</div>
        <Shimmer />
      </>
    );
  }
  if (!props.report) {
    return (
      <div className="empty">
        <div className="big">💥</div>
        Run <b>Impact Analysis</b> to see what breaks if you remove or change something.
      </div>
    );
  }
  const r = props.report;
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="card">
        <div className="card-title">
          Impact: {r.target}
          <span className={`risk ${r.risk}`} style={{ marginLeft: 'auto' }}>{r.risk}</span>
        </div>
        <div className="summary" dangerouslySetInnerHTML={{ __html: mdBold(r.summary) }} />
        <div className="section-label">Confidence {Math.round(r.confidence * 100)}%</div>
      </div>

      {r.likely_failures.length > 0 && (
        <div className="card">
          <div className="card-title">Likely failures</div>
          <div className="list">
            {r.likely_failures.map((f, i) => (
              <div className="row" key={i}><span className="bullet">▸</span><span dangerouslySetInnerHTML={{ __html: mdCode(f) }} /></div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-title">Affected surface</div>
        {r.files_affected.length > 0 && <FileList label="Files" items={r.files_affected} />}
        {r.services_affected.length > 0 && <FileList label="Services" items={r.services_affected} />}
        {r.tests_affected.length > 0 && <FileList label="Tests" items={r.tests_affected} />}
      </div>

      {r.migration.length > 0 && (
        <div className="card">
          <div className="card-title">Migration path</div>
          <div className="list">
            {r.migration.map((m, i) => (
              <div className="row" key={i}><span className="bullet">{i + 1}.</span><span>{m}</span></div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

function FileList({ label, items }: { label: string; items: string[] }) {
  return (
    <>
      <div className="section-label">{label}</div>
      <div className="pill-list">
        {items.map((it, i) => <span className="pill mono" key={i}>{it}</span>)}
      </div>
    </>
  );
}

function mdBold(s: string): string {
  return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
}
function mdCode(s: string): string {
  return escapeHtml(s).replace(/`(.+?)`/g, '<span class="mono">$1</span>');
}
function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
