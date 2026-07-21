import * as path from 'path';
import * as vscode from 'vscode';
import { AtlasClient } from '../api';

interface EditorContext {
  repo: string;
  repoPath: string;
  file: string;
  symbol: string;
  line: number;
}

/**
 * Hosts the Atlas webview and bridges it to the backend.
 *
 * The webview is a pure view: it renders state and emits intents (ask, expand,
 * replay, impact, openSource). All backend I/O and editor access happen here in
 * the extension host, so the webview needs no network or workspace permissions.
 */
export class AtlasViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'atlas.panel';

  private view?: vscode.WebviewView;
  private client: AtlasClient;
  private ctx?: EditorContext;
  private lastAnswerId?: string;
  private indexedRepos = new Set<string>();

  constructor(private readonly extensionContext: vscode.ExtensionContext) {
    this.client = new AtlasClient(this.backendUrl());
  }

  private backendUrl(): string {
    return vscode.workspace.getConfiguration('atlas').get('backendUrl', 'http://127.0.0.1:8787');
  }

  // ── webview lifecycle ──────────────────────────────────────────────────────
  resolveWebviewView(view: vscode.WebviewView) {
    this.view = view;
    view.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.extensionContext.extensionUri, 'media')],
    };
    view.webview.html = this.html(view.webview);
    view.webview.onDidReceiveMessage((msg) => this.onMessage(msg));
  }

  private post(message: unknown) {
    this.view?.webview.postMessage(message);
  }

  // ── commands ────────────────────────────────────────────────────────────────
  async askFromEditor(arg?: { symbol?: string; line?: number }) {
    const ctx = this.readEditorContext(arg);
    if (!ctx) {
      vscode.window.showWarningMessage('Atlas: open a file and place the cursor on a symbol first.');
      return;
    }
    this.ctx = ctx;
    await this.reveal();
    this.post({ type: 'context', ctx });
    await this.ask('Why is this function implemented this way?');
  }

  async replayFromEditor() {
    if (!this.ctx) {
      await this.askFromEditor();
    }
    if (!this.ctx) return;
    await this.reveal();
    this.post({ type: 'tab', tab: 'timeline' });
    this.post({ type: 'replay:pending' });
    try {
      await this.ensureIndexed(this.ctx);
      const steps = await this.client.replay(this.ctx.repo, this.ctx.symbol, this.ctx.file);
      this.post({ type: 'replay:result', steps });
    } catch (err) {
      this.post({ type: 'error', message: String(err) });
    }
  }

  async impactFromInput() {
    const target = await vscode.window.showInputBox({
      prompt: 'Atlas: what would you remove or change?',
      placeHolder: 'e.g. Redis',
    });
    if (!target) return;
    await this.reveal();
    this.post({ type: 'tab', tab: 'impact' });
    await this.impact(target);
  }

  async indexWorkspace() {
    const folder = vscode.workspace.workspaceFolders?.[0];
    if (!folder) {
      vscode.window.showWarningMessage('Atlas: open a folder to index.');
      return;
    }
    await this.reveal();
    await this.runIndex(folder.uri.fsPath);
  }

  // ── intents from the webview ────────────────────────────────────────────────
  private async onMessage(msg: any) {
    switch (msg?.type) {
      case 'ready':
        this.post({ type: 'context', ctx: this.ctx ?? null });
        this.health();
        break;
      case 'ask':
        await this.ask(msg.question ?? 'Why does this code exist?');
        break;
      case 'expand':
        await this.expand(msg.answerId);
        break;
      case 'replay':
        await this.replayFromEditor();
        break;
      case 'impact':
        await this.impact(msg.target ?? inferTargetFromCtx(this.ctx));
        break;
      case 'index':
        await this.indexWorkspace();
        break;
      case 'graph':
        await this.loadGraph();
        break;
      case 'openSource':
        await this.openSource(msg.source);
        break;
    }
  }

  // ── backend operations ──────────────────────────────────────────────────────
  private async health() {
    try {
      const h = await this.client.health();
      this.post({ type: 'health', health: h });
    } catch {
      this.post({ type: 'health', health: null });
    }
  }

  private async ask(question: string) {
    if (!this.ctx) return;
    this.post({ type: 'tab', tab: 'ask' });
    this.post({ type: 'ask:pending', target: `${this.ctx.symbol}`, question });
    try {
      await this.ensureIndexed(this.ctx);
      const result = await this.client.ask({
        repo: this.ctx.repo,
        symbol: this.ctx.symbol,
        file: this.ctx.file,
        line: this.ctx.line,
        question,
      });
      this.lastAnswerId = result.answer_id;
      this.post({ type: 'ask:result', result });
    } catch (err) {
      this.post({ type: 'error', message: String(err) });
    }
  }

  private async expand(answerId: string) {
    try {
      const expansion = await this.client.expand(answerId ?? this.lastAnswerId ?? '');
      this.post({ type: 'ask:expansion', expansion });
    } catch (err) {
      this.post({ type: 'error', message: String(err) });
    }
  }

  private async impact(target: string) {
    // Mirror replayFromEditor: the Impact tab's button can be the first thing a
    // user clicks, so pick up editor context rather than silently doing nothing.
    if (!this.ctx) {
      await this.askFromEditor();
    }
    if (!this.ctx) return;
    this.post({ type: 'impact:pending', target });
    try {
      await this.ensureIndexed(this.ctx);
      const report = await this.client.impact(this.ctx.repo, target);
      this.post({ type: 'impact:result', report });
    } catch (err) {
      this.post({ type: 'error', message: String(err) });
    }
  }

  private async loadGraph() {
    if (!this.ctx) return;
    try {
      await this.ensureIndexed(this.ctx);
      const subgraph = await this.client.subgraph(this.ctx.repo, this.ctx.symbol, this.ctx.file);
      this.post({ type: 'graph:result', subgraph });
    } catch (err) {
      this.post({ type: 'error', message: String(err) });
    }
  }

  private async ensureIndexed(ctx: EditorContext) {
    if (this.indexedRepos.has(ctx.repo)) return;
    // If the backend already knows this repo (e.g. a hosted deployment that
    // pre-indexed the demo), skip local indexing — a remote backend can't read
    // the client's filesystem anyway.
    try {
      const { repos } = await this.client.repos();
      if (repos.includes(ctx.repo)) {
        this.indexedRepos.add(ctx.repo);
        return;
      }
    } catch {
      /* backend may be down; runIndex will surface a clear error */
    }
    await this.runIndex(ctx.repoPath);
  }

  private async runIndex(repoPath: string) {
    this.post({ type: 'index:pending', repo: path.basename(repoPath) });
    const job = await this.client.index(repoPath);
    // Poll to completion, streaming status into the webview.
    for (let i = 0; i < 120; i++) {
      const status = await this.client.indexStatus(job.job_id);
      this.post({ type: 'index:status', job: status });
      if (status.status === 'done') {
        this.indexedRepos.add(status.repo);
        return;
      }
      if (status.status === 'error') {
        throw new Error(status.error ?? 'indexing failed');
      }
      await sleep(500);
    }
    throw new Error('indexing timed out');
  }

  private async openSource(source: { url?: string | null; ref: string }) {
    if (!source?.url) return;
    if (source.url.startsWith('http')) {
      vscode.env.openExternal(vscode.Uri.parse(source.url));
      return;
    }
    // Treat as a repo-relative path.
    const folder = vscode.workspace.workspaceFolders?.[0];
    if (folder) {
      const uri = vscode.Uri.joinPath(folder.uri, source.url);
      try {
        await vscode.window.showTextDocument(uri);
      } catch {
        /* file may not exist locally */
      }
    }
  }

  // ── editor context ──────────────────────────────────────────────────────────
  private readEditorContext(arg?: { symbol?: string; line?: number }): EditorContext | undefined {
    const editor = vscode.window.activeTextEditor;
    const folder = vscode.workspace.workspaceFolders?.[0];
    if (!editor || !folder) return undefined;

    const line = arg?.line ?? editor.selection.active.line;
    let symbol = arg?.symbol;
    if (!symbol) {
      const selected = editor.document.getText(editor.selection).trim();
      symbol = selected || editor.document.getText(editor.document.getWordRangeAtPosition(editor.selection.active));
    }
    if (!symbol) return undefined;

    const file = path.relative(folder.uri.fsPath, editor.document.uri.fsPath);
    return {
      repo: path.basename(folder.uri.fsPath),
      repoPath: folder.uri.fsPath,
      file,
      symbol,
      line,
    };
  }

  private async reveal() {
    if (!this.view) {
      await vscode.commands.executeCommand('atlas.panel.focus');
    }
    this.view?.show?.(true);
  }

  // ── html ───────────────────────────────────────────────────────────────────
  private html(webview: vscode.Webview): string {
    const asset = (...p: string[]) =>
      webview.asWebviewUri(
        vscode.Uri.joinPath(this.extensionContext.extensionUri, 'media', 'webview', ...p),
      );
    const scriptUri = asset('assets', 'webview.js');
    const styleUri = asset('assets', 'webview.css');
    const nonce = makeNonce();
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'none'; img-src ${webview.cspSource} https: data:; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';" />
  <link href="${styleUri}" rel="stylesheet" />
  <title>Atlas</title>
</head>
<body>
  <div id="root"></div>
  <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
  }
}

function inferTargetFromCtx(ctx?: EditorContext): string {
  return ctx?.symbol ?? 'Redis';
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function makeNonce(): string {
  let text = '';
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  for (let i = 0; i < 32; i++) text += chars.charAt(Math.floor(Math.random() * chars.length));
  return text;
}
