import type { Source, TimelineEntry } from '../types';
import { CheckIcon, sourceIcon } from './icons';
import { send } from '../vscode';

// ── source chips ─────────────────────────────────────────────────────────────
export function SourceChips({ sources }: { sources: Source[] }) {
  if (!sources.length) return null;
  return (
    <>
      <div className="section-label">Sources ({sources.length})</div>
      <div className="sources">
        {sources.map((src) => (
          <button
            key={src.ref + src.label}
            className="chip"
            title={src.detail ?? src.label}
            onClick={() => send({ type: 'openSource', source: src })}
          >
            <span className={`chip-icon ${src.kind}`}>{sourceIcon(src.kind)}</span>
            <span className="chip-label">{src.label}</span>
          </button>
        ))}
      </div>
    </>
  );
}

// ── vertical timeline (preview + expansion share this) ───────────────────────
export function Timeline({ entries }: { entries: TimelineEntry[] }) {
  return (
    <div className="timeline">
      {entries.map((e, i) => (
        <div className="tl-row" key={i}>
          <div className="tl-date">{e.date}</div>
          <div className="tl-rail">
            <span className={`tl-dot ${e.is_incident ? 'incident' : ''}`} />
            <span className="tl-line" />
          </div>
          <div className="tl-body">
            <div className={`tl-title ${e.is_incident ? 'incident' : ''}`}>{e.title}</div>
            <div className="tl-detail">{e.detail}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function Reason({ label, text }: { label: string; text: string }) {
  return (
    <div className="reason">
      <span className="check"><CheckIcon /></span>
      <span>
        <b>{label}:</b> {text}
      </span>
    </div>
  );
}

export function Shimmer() {
  return (
    <div className="card">
      <div className="shimmer" style={{ width: '40%', marginBottom: 12 }} />
      <div className="shimmer" style={{ width: '92%', marginBottom: 8 }} />
      <div className="shimmer" style={{ width: '80%', marginBottom: 8 }} />
      <div className="shimmer" style={{ width: '60%' }} />
    </div>
  );
}
