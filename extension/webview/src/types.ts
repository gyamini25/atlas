// Mirror of the backend API schemas (atlas.models.schemas) consumed by the webview.

export type SourceKind =
  | 'pull_request'
  | 'commit'
  | 'issue'
  | 'adr'
  | 'doc'
  | 'incident'
  | 'slack';

export interface Source {
  kind: SourceKind;
  label: string;
  ref: string;
  url?: string | null;
  detail?: string | null;
}

export interface KeyReason {
  label: string;
  text: string;
  kind?: SourceKind | null;
}

export interface TimelineEntry {
  date: string;
  title: string;
  detail: string;
  kind?: SourceKind | null;
  is_incident: boolean;
  sources: Source[];
}

export interface AskResult {
  answer_id: string;
  question: string;
  target: string;
  summary: string;
  confidence: number;
  key_reasons: KeyReason[];
  sources: Source[];
  timeline_preview: TimelineEntry[];
}

export interface AskExpansion {
  answer_id: string;
  reasoning: string;
  alternatives: string[];
  timeline: TimelineEntry[];
  dependencies: string[];
  impact_summary: string;
  related_discussions: Source[];
}

export interface ReplayStep {
  order: number;
  date: string;
  title: string;
  narration: string;
  kind?: SourceKind | null;
  is_incident: boolean;
  sources: Source[];
}

export interface ImpactReport {
  target: string;
  risk: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  summary: string;
  files_affected: string[];
  services_affected: string[];
  tests_affected: string[];
  likely_failures: string[];
  migration: string[];
}

export interface IndexJob {
  job_id: string;
  repo: string;
  status: string;
  progress: number;
  detail: string;
  counts: Record<string, number>;
  error?: string | null;
}

export interface EditorCtx {
  repo: string;
  repoPath: string;
  file: string;
  symbol: string;
  line: number;
}

export type Tab = 'ask' | 'timeline' | 'graph' | 'impact';
