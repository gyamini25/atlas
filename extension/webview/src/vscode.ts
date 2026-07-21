// Thin wrapper over the VS Code webview messaging API.

interface VsCodeApi {
  postMessage(message: unknown): void;
  getState(): unknown;
  setState(state: unknown): void;
}

declare function acquireVsCodeApi(): VsCodeApi;

// `acquireVsCodeApi` can only be called once per webview.
export const vscode: VsCodeApi = acquireVsCodeApi();

export function send(message: Record<string, unknown>): void {
  vscode.postMessage(message);
}
