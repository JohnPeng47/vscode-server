import * as vscode from "vscode";
import { registerAnchorCache } from "./anchor-cache";
import { registerCopyProvider } from "./copy-provider";
import { DiagramDefinitionProvider } from "./definition-provider";
import { DiagramHoverProvider } from "./hover-provider";
import { DiagramLinkProvider } from "./link-provider";
import { registerLinkCreator } from "./link-creator";
import { showStatusPage } from "./status-page";

const DIAGRAM_SELECTOR: vscode.DocumentSelector = [
	{ language: "plaintext", scheme: "file" },
	{ language: "markdown", scheme: "file" },
];

export function activate(context: vscode.ExtensionContext): void {
	registerAnchorCache(context);

	context.subscriptions.push(
		vscode.languages.registerDocumentLinkProvider(DIAGRAM_SELECTOR, new DiagramLinkProvider()),
		vscode.languages.registerDefinitionProvider(DIAGRAM_SELECTOR, new DiagramDefinitionProvider()),
		vscode.languages.registerHoverProvider(DIAGRAM_SELECTOR, new DiagramHoverProvider()),
		vscode.commands.registerCommand("diagfren.statusPage", () => showStatusPage(context.extensionUri)),
	);

	registerCopyProvider(context);
	registerLinkCreator(context);
}

export function deactivate(): void {}
