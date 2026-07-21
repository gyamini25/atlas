/**
 * Typed client for the Atlas backend. Runs in the extension host (Node), not the
 * webview — the webview talks to this indirectly via postMessage so it never
 * needs network access itself.
 */

export interface AskRequest {
  repo: string;
  symbol: string;
  file?: string;
  line?: number;
  question?: string;
}

export interface Source {
  kind: string;
  label: string;
  ref: string;
  url?: string | null;
  detail?: string | null;
}

export interface KeyReason {
  label: string;
  text: string;
  kind?: string | null;
}

export interface TimelineEntry {
  date: string;
  title: string;
  detail: string;
  kind?: string | null;
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
  kind?: string | null;
  is_incident: boolean;
  sources: Source[];
}

export interface ImpactReport {
  target: string;
  risk: string;
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

export class AtlasClient {
  constructor(private readonly baseUrl: string) {}

  private async post<T>(path: string, body: unknown): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      throw new Error(`Atlas ${path} failed (${res.status}): ${await res.text()}`);
    }
    return (await res.json()) as T;
  }

  private async get<T>(path: string): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`);
    if (!res.ok) {
      throw new Error(`Atlas ${path} failed (${res.status}): ${await res.text()}`);
    }
    return (await res.json()) as T;
  }

  health() {
    return this.get<{ status: string; llm_mode: string; model: string }>('/health');
  }

  repos() {
    return this.get<{ repos: string[] }>('/api/repos');
  }

  index(repoPath: string) {
    return this.post<IndexJob>('/api/index', { repo_path: repoPath });
  }

  indexStatus(jobId: string) {
    return this.get<IndexJob>(`/api/index/${jobId}`);
  }

  ask(req: AskRequest) {
    return this.post<AskResult>('/api/ask', req);
  }

  expand(answerId: string) {
    return this.get<AskExpansion>(`/api/ask/${answerId}/expand`);
  }

  replay(repo: string, symbol: string, file?: string) {
    return this.post<ReplayStep[]>('/api/replay', { repo, symbol, file });
  }

  impact(repo: string, target: string) {
    return this.post<ImpactReport>('/api/impact', { repo, target });
  }

  subgraph(repo: string, symbol: string, file?: string) {
    const params = new URLSearchParams({ repo, symbol });
    if (file) params.set('file', file);
    return this.get<Subgraph>(`/api/graph/subgraph?${params.toString()}`);
  }
}

export interface SubgraphNode {
  id: string;
  kind: string;
  label: string;
  meta: Record<string, string>;
}

export interface SubgraphEdge {
  source: string;
  target: string;
  kind: string;
}

export interface Subgraph {
  root: string;
  nodes: SubgraphNode[];
  edges: SubgraphEdge[];
}
