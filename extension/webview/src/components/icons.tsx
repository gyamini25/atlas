import type { SourceKind } from '../types';

// Minimal inline SVG icon set (no external icon dependency, CSP-safe).

const s = { width: 13, height: 13, viewBox: '0 0 16 16', fill: 'currentColor' } as const;

export function SparkIcon() {
  return (
    <svg {...s}>
      <path d="M8 0l1.6 4.9L14.5 6.5 9.6 8.1 8 13 6.4 8.1 1.5 6.5 6.4 4.9z" />
    </svg>
  );
}

export function CheckIcon() {
  return (
    <svg {...s} fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M13 4L6 12 3 8.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function SendIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
      <path d="M1.5 8L14 2 9.5 14 7.5 9z" />
    </svg>
  );
}

export function PrIcon() {
  return (
    <svg {...s} fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="4" cy="4" r="1.6" /><circle cx="4" cy="12" r="1.6" /><circle cx="12" cy="12" r="1.6" />
      <path d="M4 5.6v4.8M12 10.4V8a2 2 0 00-2-2H6.5" />
    </svg>
  );
}

export function IncidentIcon() {
  return (
    <svg {...s}>
      <path d="M8 1L15 14H1z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M8 6v3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="8" cy="11.5" r="0.9" />
    </svg>
  );
}

export function AdrIcon() {
  return (
    <svg {...s} fill="none" stroke="currentColor" strokeWidth="1.4">
      <path d="M4 1.5h5L12.5 5v9.5H4z" strokeLinejoin="round" />
      <path d="M6 8h4M6 10.5h4" strokeLinecap="round" />
    </svg>
  );
}

export function SlackIcon() {
  return (
    <svg {...s}>
      <path d="M3.5 9.5a1.5 1.5 0 11-1.5-1.5h1.5zM4.5 9.5A1.5 1.5 0 016 8h3.5A1.5 1.5 0 0111 9.5v3.5A1.5 1.5 0 019.5 14.5 1.5 1.5 0 018 13v-3.5z" opacity="0.9" />
      <path d="M6.5 3.5A1.5 1.5 0 118 2v1.5zM6.5 4.5A1.5 1.5 0 018 6v0H4.5A1.5 1.5 0 013 4.5 1.5 1.5 0 014.5 3H6.5z" opacity="0.6" />
    </svg>
  );
}

export function CommitIcon() {
  return (
    <svg {...s} fill="none" stroke="currentColor" strokeWidth="1.4">
      <circle cx="8" cy="8" r="2.6" /><path d="M8 1v2.8M8 12.2V15" strokeLinecap="round" />
    </svg>
  );
}

export function IssueIcon() {
  return (
    <svg {...s} fill="none" stroke="currentColor" strokeWidth="1.4">
      <circle cx="8" cy="8" r="6" /><circle cx="8" cy="8" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function sourceIcon(kind: SourceKind) {
  switch (kind) {
    case 'pull_request': return <PrIcon />;
    case 'incident': return <IncidentIcon />;
    case 'adr': return <AdrIcon />;
    case 'slack': return <SlackIcon />;
    case 'commit': return <CommitIcon />;
    case 'issue': return <IssueIcon />;
    default: return <AdrIcon />;
  }
}
