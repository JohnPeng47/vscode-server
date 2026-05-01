import * as vscode from "vscode";
import { refreshAnchors } from "./anchor-cache";
import {
	type Anchor,
	isDiagramLanguage,
	loadAnchors,
	resolveAnchorsUri,
	serializeAnchors,
} from "./anchors";

/**
 * "Select Link Target" mode.
 *
 * Flow:
 *   1. User selects diagram text and runs `diagfren.createLink`.
 *   2. We capture the source doc + range + anchor text, set the
 *      `diagfren.selectLinkMode` context, decorate the source highlight,
 *      and start listening to selection changes across all editors.
 *   3. User navigates to a target file using any native means
 *      (Go to Definition, quick-open, etc.) and clicks a line.
 *   4. The mouse-click handler writes the anchor, jumps focus back
 *      to the source diagram, and exits the mode.
 *   5. Esc cancels; Alt+Enter commits at the current cursor (keyboard).
 */

interface LinkCreationState {
	sourceDocUri: vscode.Uri;
	sourceRange: vscode.Range;
	anchorText: string;
	highlight: vscode.TextEditorDecorationType;
	cursorLine: vscode.TextEditorDecorationType;
	statusItem: vscode.StatusBarItem;
	selectionListener: vscode.Disposable;
	editorListener: vscode.Disposable;
	pending: boolean;
}

let active: LinkCreationState | null = null;

export function registerLinkCreator(context: vscode.ExtensionContext): void {
	context.subscriptions.push(
		vscode.commands.registerCommand("diagfren.createLink", startLinkCreation),
		vscode.commands.registerCommand("diagfren.confirmLink", confirmAtCursor),
		vscode.commands.registerCommand("diagfren.cancelLink", cancelLinkCreation),
	);
}

async function startLinkCreation(): Promise<void> {
	if (active) {
		vscode.window.showInformationMessage("diagfren: already in link-creation mode (Esc to cancel).");
		return;
	}

	const editor = vscode.window.activeTextEditor;
	if (!editor) return;
	if (!isDiagramLanguage(editor.document.languageId)) {
		vscode.window.showErrorMessage("diagfren: active file is not a diagram.");
		return;
	}
	if (editor.selection.isEmpty) {
		vscode.window.showErrorMessage("diagfren: select the text to link first.");
		return;
	}

	const sel = editor.selection;
	const anchorText = editor.document.getText(sel);
	if (anchorText.includes("\n")) {
		vscode.window.showErrorMessage("diagfren: anchor text cannot span multiple lines.");
		return;
	}

	const highlight = vscode.window.createTextEditorDecorationType({
		backgroundColor: new vscode.ThemeColor("editor.findMatchHighlightBackground"),
		borderRadius: "2px",
	});
	editor.setDecorations(highlight, [sel]);

	// Whole-line stripe that follows the cursor in any non-source editor —
	// signals "click here / press Alt+Enter and this is the line that commits."
	const cursorLine = vscode.window.createTextEditorDecorationType({
		isWholeLine: true,
		backgroundColor: new vscode.ThemeColor("editor.selectionHighlightBackground"),
		borderWidth: "1px 0",
		borderStyle: "dashed",
		borderColor: new vscode.ThemeColor("focusBorder"),
		overviewRulerColor: new vscode.ThemeColor("focusBorder"),
		overviewRulerLane: vscode.OverviewRulerLane.Full,
	});

	const statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 1000);
	statusItem.text = `$(link) diagfren: pick link target — click a line · Alt+Enter to confirm · Esc to cancel`;
	statusItem.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
	statusItem.show();

	await vscode.commands.executeCommand("setContext", "diagfren.selectLinkMode", true);

	const selectionListener = vscode.window.onDidChangeTextEditorSelection(handleSelectionChange);
	const editorListener = vscode.window.onDidChangeActiveTextEditor((ed) => {
		if (ed) updateCursorLineIndicator(ed);
	});

	active = {
		sourceDocUri: editor.document.uri,
		sourceRange: new vscode.Range(sel.start, sel.end),
		anchorText,
		highlight,
		cursorLine,
		statusItem,
		selectionListener,
		editorListener,
		pending: false,
	};
}

function updateCursorLineIndicator(editor: vscode.TextEditor): void {
	if (!active) return;
	if (editor.document.uri.toString() === active.sourceDocUri.toString()) {
		editor.setDecorations(active.cursorLine, []);
		return;
	}
	const line = editor.selection.active.line;
	editor.setDecorations(active.cursorLine, [new vscode.Range(line, 0, line, 0)]);
}

function handleSelectionChange(e: vscode.TextEditorSelectionChangeEvent): void {
	if (!active) return;
	// Always update the line indicator so the user sees what would commit.
	updateCursorLineIndicator(e.textEditor);
	// Ignore activity inside the source diagram — user may be re-reading it.
	if (e.textEditor.document.uri.toString() === active.sourceDocUri.toString()) return;
	// Only commit on real mouse clicks. Keyboard navigation just moves the cursor.
	if (e.kind !== vscode.TextEditorSelectionChangeKind.Mouse) return;

	const sel = e.selections[0];
	if (!sel) return;

	const startLine = sel.start.line + 1;
	const endLine = sel.start.line === sel.end.line ? null : sel.end.line + 1;
	void commitLink(e.textEditor.document.uri, startLine, endLine);
}

async function confirmAtCursor(): Promise<void> {
	if (!active) return;
	const editor = vscode.window.activeTextEditor;
	if (!editor) return;
	if (editor.document.uri.toString() === active.sourceDocUri.toString()) {
		vscode.window.showErrorMessage("diagfren: navigate to the target file first.");
		return;
	}
	const sel = editor.selection;
	const startLine = sel.start.line + 1;
	const endLine = sel.start.line === sel.end.line ? null : sel.end.line + 1;
	await commitLink(editor.document.uri, startLine, endLine);
}

async function commitLink(targetUri: vscode.Uri, startLine: number, endLine: number | null): Promise<void> {
	if (!active || active.pending) return;

	const filePath = vscode.workspace.asRelativePath(targetUri, false);
	const range = endLine ? `${startLine}-${endLine}` : `${startLine}`;

	active.pending = true;
	const choice = await vscode.window.showInformationMessage(
		`Link "${active.anchorText}"?`,
		{ modal: true, detail: `→ ${filePath}:${range}` },
		"Link",
	);
	if (!active) return; // cancelled while modal was open
	active.pending = false;
	if (choice !== "Link") return;

	const newAnchor: Anchor = {
		text: active.anchorText,
		filePath,
		startLine,
		endLine,
		label: active.anchorText,
	};

	const existing = await loadAnchors(active.sourceDocUri);
	const merged = existing.filter(a => a.text !== newAnchor.text);
	merged.push(newAnchor);

	const anchorsUri = resolveAnchorsUri(active.sourceDocUri);
	if (!anchorsUri) {
		vscode.window.showErrorMessage("diagfren: cannot resolve sidecar path.");
		cleanup();
		return;
	}

	try {
		await vscode.workspace.fs.createDirectory(vscode.Uri.joinPath(anchorsUri, ".."));
	} catch {
		// Already exists
	}
	await vscode.workspace.fs.writeFile(anchorsUri, Buffer.from(serializeAnchors(merged), "utf-8"));
	await refreshAnchors(active.sourceDocUri);

	const sourceDoc = await vscode.workspace.openTextDocument(active.sourceDocUri);
	const sourceEditor = await vscode.window.showTextDocument(sourceDoc);
	sourceEditor.selection = new vscode.Selection(active.sourceRange.start, active.sourceRange.end);
	sourceEditor.revealRange(active.sourceRange);

	vscode.window.setStatusBarMessage(`diagfren: linked "${active.anchorText}" → ${filePath}:${range}`, 4000);
	cleanup();
}

function cancelLinkCreation(): void {
	if (!active) return;
	cleanup();
	vscode.window.setStatusBarMessage("diagfren: link creation cancelled", 2000);
}

function cleanup(): void {
	if (!active) return;
	active.highlight.dispose();
	active.cursorLine.dispose();
	active.statusItem.dispose();
	active.selectionListener.dispose();
	active.editorListener.dispose();
	active = null;
	void vscode.commands.executeCommand("setContext", "diagfren.selectLinkMode", false);
}
