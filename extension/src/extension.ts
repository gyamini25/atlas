import * as vscode from 'vscode';
import { AtlasViewProvider } from './panel/AtlasViewProvider';

export function activate(context: vscode.ExtensionContext) {
  const provider = new AtlasViewProvider(context);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(AtlasViewProvider.viewType, provider, {
      webviewOptions: { retainContextWhenHidden: true },
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('atlas.ask', () => provider.askFromEditor()),
    vscode.commands.registerCommand('atlas.replay', () => provider.replayFromEditor()),
    vscode.commands.registerCommand('atlas.impact', () => provider.impactFromInput()),
    vscode.commands.registerCommand('atlas.indexRepository', () => provider.indexWorkspace()),
  );

  // A CodeLens above every symbol-like line gives the inline "✨ Ask Atlas ⌘K"
  // affordance shown in the product mockup.
  context.subscriptions.push(
    vscode.languages.registerCodeLensProvider(
      { scheme: 'file' },
      new AtlasCodeLensProvider(),
    ),
  );
}

export function deactivate() {}

/** Emits an "Ask Atlas" CodeLens on function/method declarations. */
class AtlasCodeLensProvider implements vscode.CodeLensProvider {
  private static readonly DECL =
    /\b(?:async\s+)?(?:function\s+|def\s+|public\s+|private\s+|protected\s+)?([a-zA-Z_]\w+)\s*\(/;

  provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
    const lenses: vscode.CodeLens[] = [];
    const max = Math.min(document.lineCount, 2000);
    for (let i = 0; i < max; i++) {
      const text = document.lineAt(i).text;
      const match = AtlasCodeLensProvider.DECL.exec(text);
      if (match && !text.trim().startsWith('//') && !text.includes('=>')) {
        const range = new vscode.Range(i, 0, i, 0);
        lenses.push(
          new vscode.CodeLens(range, {
            title: '✨ Ask Atlas',
            command: 'atlas.ask',
            arguments: [{ symbol: match[1], line: i }],
          }),
        );
      }
    }
    return lenses;
  }
}
