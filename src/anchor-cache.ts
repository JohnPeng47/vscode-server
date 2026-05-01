import * as path from "path";
import * as vscode from "vscode";
import { type Anchor, DIAGRAM_EXTENSIONS, extractDiagramContent, findDiagramBlockRange, getSidecarPath, isDiagramFile, isDiagramLanguage, loadAnchors, parseAnchorsContent, resolveAnchorsUri, serializeAnchors } from "./anchors";

/**
 * Cache of parsed anchors per document URI, loaded from `.diagfren/` sidecar files.
 *
 * Providers call `getAnchors()` which returns from cache or loads on demand.
 * The `onDidChange` emitter notifies the DocumentLinkProvider to re-query.
 */
const cache = new Map<string, Anchor[]>();

/** Fires when cached anchors change — link provider listens to re-provide links. */
export const onDidChangeAnchors = new vscode.EventEmitter<void>();

/** Get anchors for a document, loading from sidecar if not cached. */
export async function getAnchors(documentUri: vscode.Uri): Promise<Anchor[]> {
	const key = documentUri.toString();
	const cached = cache.get(key);
	if (cached !== undefined) return cached;

	const anchors = await loadAnchors(documentUri);
	cache.set(key, anchors);
	return anchors;
}

/** Get cached anchors synchronously. Returns empty array if not yet loaded. */
export function getCachedAnchors(documentUri: vscode.Uri): Anchor[] {
	return cache.get(documentUri.toString()) ?? [];
}

/** Refresh the cache for a single document and fire change event. */
export async function refreshAnchors(documentUri: vscode.Uri): Promise<void> {
	const anchors = await loadAnchors(documentUri);
	const key = documentUri.toString();
	const prev = cache.get(key);
	cache.set(key, anchors);

	// Only fire if the result actually changed
	const changed = prev === undefined
		|| prev.length !== anchors.length
		|| JSON.stringify(prev) !== JSON.stringify(anchors);
	if (changed) {
		onDidChangeAnchors.fire();
	}
}

/** Returns true if the cache has anchors for this document. */
export function hasCachedAnchors(documentUri: vscode.Uri): boolean {
	const entry = cache.get(documentUri.toString());
	return entry !== undefined && entry.length > 0;
}

/** Register listeners that keep the cache warm. */
export function registerAnchorCache(context: vscode.ExtensionContext): void {
	// Load on activation for currently open editors
	for (const editor of vscode.window.visibleTextEditors) {
		if (isDiagramLanguage(editor.document.languageId)) {
			refreshAnchors(editor.document.uri);
		}
	}

	// Sweep orphaned sidecars whose source diagrams no longer exist
	pruneOrphanedSidecars();

	context.subscriptions.push(
		onDidChangeAnchors,
		vscode.window.onDidChangeActiveTextEditor((editor) => {
			if (editor?.document.languageId === "plaintext") {
				refreshAnchors(editor.document.uri);
			}
		}),
		vscode.workspace.onDidOpenTextDocument((doc) => {
			if (isDiagramLanguage(doc.languageId)) {
				refreshAnchors(doc.uri);
			}
		}),
	);

	// Watch sidecar folder for changes so edits to sidecar files refresh the cache
	const anchorsWatcher = vscode.workspace.createFileSystemWatcher(`**/${getSidecarPath()}/**/*.anchors`);
	context.subscriptions.push(
		anchorsWatcher,
		anchorsWatcher.onDidChange(() => refreshAllVisible()),
		anchorsWatcher.onDidCreate(() => refreshAllVisible()),
		anchorsWatcher.onDidDelete(() => refreshAllVisible()),
	);

	// Handle file renames — move sidecars and update code-refs
	context.subscriptions.push(
		vscode.workspace.onDidRenameFiles((e) => {
			for (const { oldUri, newUri } of e.files) {
				handleFileRenamed(oldUri, newUri);
			}
		}),
	);

	// Watch diagram files (.txt and .md) for changes and deletion
	const diagramWatchers = [
		vscode.workspace.createFileSystemWatcher("**/*.txt"),
		vscode.workspace.createFileSystemWatcher("**/*.md"),
	];
	for (const watcher of diagramWatchers) {
		context.subscriptions.push(
			watcher,
			watcher.onDidChange((changedUri) => pruneStaleAnchors(changedUri)),
			watcher.onDidDelete(async (deletedUri) => {
				const anchorsUri = resolveAnchorsUri(deletedUri);
				if (!anchorsUri) return;

				try {
					await vscode.workspace.fs.delete(anchorsUri);
				} catch {
					// Sidecar didn't exist — nothing to clean up
				}

				// Evict from cache
				const key = deletedUri.toString();
				if (cache.delete(key)) {
					onDidChangeAnchors.fire();
				}
			}),
		);
	}
}

/**
 * Reconcile orphaned `.diagfren/` sidecars whose source diagrams moved or were deleted.
 *
 * For each orphaned sidecar, tries to find a matching unmatched `.txt` diagram by:
 *   1. Basename match (e.g. `01-overview.anchors` → `01-overview.txt`)
 *   2. Anchor identity — every anchor text from the sidecar must appear in the
 *      candidate diagram's ``` diagram ``` block
 *
 * If exactly one candidate passes both checks, the sidecar is moved and
 * cross-diagram code-refs are rewritten. Otherwise the orphan is deleted.
 */
export async function pruneOrphanedSidecars(): Promise<void> {
	const workspaceFolders = vscode.workspace.workspaceFolders;
	if (!workspaceFolders?.[0]) return;

	const root = workspaceFolders[0].uri;

	// Collect all sidecars and classify as matched or orphaned
	const sidecar = getSidecarPath();
	const anchorsFiles = await vscode.workspace.findFiles(`${sidecar}/**/*.anchors`, "**/node_modules/**", 500);

	interface OrphanInfo {
		anchorsFile: vscode.Uri;
		oldDiagramRelative: string;
		basename: string;
		anchorTexts: string[];
	}

	const orphans: OrphanInfo[] = [];

	for (const anchorsFile of anchorsFiles) {
		const relative = vscode.workspace.asRelativePath(anchorsFile, false);
		const sidecarPrefix = new RegExp(`^${sidecar.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/`);
		const baseRelative = relative.replace(sidecarPrefix, "").replace(/\.anchors$/, "");

		// Try each diagram extension to find the source file
		let found = false;
		for (const ext of DIAGRAM_EXTENSIONS) {
			const diagramRelative = baseRelative + ext;
			const diagramUri = vscode.Uri.joinPath(root, diagramRelative);
			try {
				await vscode.workspace.fs.stat(diagramUri);
				found = true;
				break;
			} catch {
				// Try next extension
			}
		}

		if (!found) {
			// Parse anchor texts for identity matching
			let anchorTexts: string[] = [];
			try {
				const bytes = await vscode.workspace.fs.readFile(anchorsFile);
				const anchors = parseAnchorsContent(Buffer.from(bytes).toString("utf-8"));
				anchorTexts = anchors.map((a) => a.text);
			} catch {
				// Unreadable — will be deleted below
			}

			orphans.push({
				anchorsFile,
				oldDiagramRelative: baseRelative + ".txt", // Use .txt as canonical for matching
				basename: path.basename(baseRelative),
				anchorTexts,
			});
		}
	}

	if (orphans.length === 0) return;

	// Find all diagram files (.txt and .md) with a ```diagram block that DON'T have a sidecar
	const excludePattern = `{**/node_modules/**,${sidecar}/**}`;
	const allDiagramFiles = (await Promise.all(
		DIAGRAM_EXTENSIONS.map(ext => vscode.workspace.findFiles(`**/*${ext}`, excludePattern, 1000))
	)).flat();

	interface CandidateInfo {
		uri: vscode.Uri;
		relative: string;
		basename: string;
		diagramContent: string;
	}

	const candidates: CandidateInfo[] = [];
	for (const diagramFile of allDiagramFiles) {
		const relative = vscode.workspace.asRelativePath(diagramFile, false);
		// Skip if it already has a sidecar
		const sidecarUri = resolveAnchorsUri(diagramFile);
		if (sidecarUri) {
			try {
				await vscode.workspace.fs.stat(sidecarUri);
				continue; // Has sidecar — not a candidate
			} catch {
				// No sidecar — potential candidate
			}
		}

		// Check if it has a diagram block
		try {
			const bytes = await vscode.workspace.fs.readFile(diagramFile);
			const text = Buffer.from(bytes).toString("utf-8");
			const content = extractDiagramContent(text);
			if (content) {
				const ext = DIAGRAM_EXTENSIONS.find(e => relative.endsWith(e)) ?? ".txt";
				candidates.push({
					uri: diagramFile,
					relative,
					basename: path.basename(relative, ext),
					diagramContent: content,
				});
			}
		} catch {
			continue;
		}
	}

	// Track old→new path mappings for cross-diagram ref rewriting
	const pathMappings: Array<{ oldPath: string; newPath: string }> = [];

	for (const orphan of orphans) {
		// Find candidates matching by basename AND anchor identity
		const matches = candidates.filter((c) => {
			if (c.basename !== orphan.basename) return false;
			// Every anchor text must appear in the diagram content
			if (orphan.anchorTexts.length === 0) return false;
			return orphan.anchorTexts.every((text) => c.diagramContent.includes(text));
		});

		if (matches.length === 1) {
			// Unique match — relocate the sidecar
			const match = matches[0]!;
			const newAnchorsUri = resolveAnchorsUri(match.uri);
			if (newAnchorsUri) {
				try {
					await vscode.workspace.fs.rename(orphan.anchorsFile, newAnchorsUri, { overwrite: true });
					pathMappings.push({
						oldPath: orphan.oldDiagramRelative,
						newPath: match.relative,
					});
					// Remove from candidates so it can't double-match
					const idx = candidates.indexOf(match);
					if (idx !== -1) candidates.splice(idx, 1);
					continue;
				} catch {
					// Fall through to delete
				}
			}
		}

		// No unique match — delete the orphan
		try {
			await vscode.workspace.fs.delete(orphan.anchorsFile);
		} catch {
			// Already gone
		}
	}

	// Rewrite cross-diagram code-refs for all relocated sidecars
	for (const { oldPath, newPath } of pathMappings) {
		await updateCodeRefsInAllSidecars(oldPath, newPath);
	}
}

/**
 * When a diagram file changes, remove any anchors whose text
 * no longer appears anywhere in the document.
 */
async function pruneStaleAnchors(diagramUri: vscode.Uri): Promise<void> {
	const anchorsUri = resolveAnchorsUri(diagramUri);
	if (!anchorsUri) return;

	// Load current anchors — bail if no sidecar exists
	const anchors = await loadAnchors(diagramUri);
	if (anchors.length === 0) return;

	// Read the file content
	let documentText: string;
	try {
		const bytes = await vscode.workspace.fs.readFile(diagramUri);
		documentText = Buffer.from(bytes).toString("utf-8");
	} catch {
		return;
	}

	// Keep anchors whose text still appears anywhere in the document
	const kept = anchors.filter((a) => documentText.includes(a.text));

	if (kept.length === anchors.length) return; // Nothing to prune

	const content = serializeAnchors(kept);
	await vscode.workspace.fs.writeFile(anchorsUri, Buffer.from(content, "utf-8"));
	await refreshAnchors(diagramUri);
}

/**
 * Handle a file or directory rename:
 * - Single .txt file → move its sidecar
 * - Directory → move all sidecars under the old prefix
 * - Then rewrite code-refs across all sidecars for old→new path
 */
async function handleFileRenamed(oldUri: vscode.Uri, newUri: vscode.Uri): Promise<void> {
	const workspaceFolders = vscode.workspace.workspaceFolders;
	if (!workspaceFolders?.[0]) return;

	const root = workspaceFolders[0].uri;
	const oldRelative = vscode.workspace.asRelativePath(oldUri, false);
	const newRelative = vscode.workspace.asRelativePath(newUri, false);

	if (isDiagramFile(oldRelative)) {
		// Single file rename → move one sidecar
		const oldAnchorsUri = resolveAnchorsUri(oldUri);
		const newAnchorsUri = resolveAnchorsUri(newUri);
		if (oldAnchorsUri && newAnchorsUri) {
			try {
				await vscode.workspace.fs.stat(oldAnchorsUri);
				await vscode.workspace.fs.rename(oldAnchorsUri, newAnchorsUri, { overwrite: true });
				cache.delete(oldUri.toString());
				await refreshAnchors(newUri);
			} catch {
				// Old sidecar didn't exist
			}
		}
	} else {
		// Directory rename → move all sidecars under the old prefix
		const sidecar = getSidecarPath();
		const oldSidecarPrefix = `${sidecar}/${oldRelative}/`;
		const anchorsFiles = await vscode.workspace.findFiles(`${sidecar}/**/*.anchors`, "**/node_modules/**", 500);

		for (const anchorsFile of anchorsFiles) {
			const anchorsRelative = vscode.workspace.asRelativePath(anchorsFile, false);
			if (!anchorsRelative.startsWith(oldSidecarPrefix)) continue;

			// Compute new sidecar path by replacing the prefix
			const suffix = anchorsRelative.slice(oldSidecarPrefix.length);
			const newAnchorsRelative = `${sidecar}/${newRelative}/${suffix}`;
			const newAnchorsUri = vscode.Uri.joinPath(root, newAnchorsRelative);

			try {
				await vscode.workspace.fs.rename(anchorsFile, newAnchorsUri, { overwrite: true });
			} catch {
				// Target dir may not exist yet — create and retry
				try {
					const parentDir = vscode.Uri.joinPath(newAnchorsUri, "..");
					await vscode.workspace.fs.createDirectory(parentDir);
					await vscode.workspace.fs.rename(anchorsFile, newAnchorsUri, { overwrite: true });
				} catch {
					// Give up on this file
				}
			}

			// Evict old cache entries for all possible diagram extensions
			const sidecarPrefixRe = new RegExp(`^${sidecar.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/`);
			const baseRelative = anchorsRelative.replace(sidecarPrefixRe, "").replace(/\.anchors$/, "");
			for (const ext of DIAGRAM_EXTENSIONS) {
				const oldDiagramUri = vscode.Uri.joinPath(root, baseRelative + ext);
				cache.delete(oldDiagramUri.toString());
			}
		}
	}

	// Rewrite code-refs across all sidecars: old path prefix → new
	await updateCodeRefsInAllSidecars(oldRelative, newRelative);
}

/**
 * Scan all `.anchors` sidecar files and replace any code-ref paths
 * matching `oldPath` with `newPath`. Operates on raw text to preserve formatting.
 *
 * Matches both:
 *  - `oldPath:` (file rename, e.g. `src/foo.ts:10`)
 *  - `oldPath/` (directory rename, e.g. `src/old-dir/foo.ts:10` → `src/new-dir/foo.ts:10`)
 */
async function updateCodeRefsInAllSidecars(oldPath: string, newPath: string): Promise<void> {
	const anchorsFiles = await vscode.workspace.findFiles(`${getSidecarPath()}/**/*.anchors`, "**/node_modules/**", 500);
	let anyChanged = false;

	// For file renames, match "path:" — for directory renames, match "path/"
	const fileNeedle = oldPath + ":";
	const dirNeedle = oldPath + "/";

	for (const anchorsFile of anchorsFiles) {
		let content: string;
		try {
			const bytes = await vscode.workspace.fs.readFile(anchorsFile);
			content = Buffer.from(bytes).toString("utf-8");
		} catch {
			continue;
		}

		if (!content.includes(fileNeedle) && !content.includes(dirNeedle)) continue;

		let updated = content;
		updated = updated.replaceAll(fileNeedle, newPath + ":");
		updated = updated.replaceAll(dirNeedle, newPath + "/");
		if (updated !== content) {
			await vscode.workspace.fs.writeFile(anchorsFile, Buffer.from(updated, "utf-8"));
			anyChanged = true;
		}
	}

	if (anyChanged) {
		refreshAllVisible();
		onDidChangeAnchors.fire();
	}
}

function refreshAllVisible(): void {
	for (const editor of vscode.window.visibleTextEditors) {
		if (isDiagramLanguage(editor.document.languageId)) {
			refreshAnchors(editor.document.uri);
		}
	}
}
