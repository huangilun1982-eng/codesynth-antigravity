import * as vscode from 'vscode';
import { ServerManager } from './services/server_manager';
import { startSnapshotWatcher } from './services/snapshot_watcher';
import { StatusBarManager } from './ui/status_bar';
import { openCockpitCmd } from './commands/open_cockpit';
import { startSimulationCmd } from './commands/simulation';
import { exportCodeCmd } from './commands/export';
import { CockpitPanel } from './ui/cockpit_panel';

export function activate(context: vscode.ExtensionContext) {
    console.log('[CodeSynth] Extension Activation Started.');

    // 0. 自動啟動 Python Server
    ServerManager.start(context);

    // 1. 自動備份機制
    startSnapshotWatcher(context);

    // 2. 註冊命令
    context.subscriptions.push(
        vscode.commands.registerCommand('codesynth.openCockpit', () => openCockpitCmd(context))
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codesynth.startSimulation', () => startSimulationCmd(context))
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codesynth.exportCode', () => exportCodeCmd(context))
    );

    // Also register scan project command which is called by webview
    context.subscriptions.push(
        vscode.commands.registerCommand('codesynth.scanProject', async () => {
            // Re-implement scan project logic here or move to a separate command file
            // For now, let's keep it clean and maybe move to src/commands/scan.ts later
            // But since it wasn't in my original list, let's implement inline or import
            // To be strictly modular, I should have extracted it.
            // Let's create src/commands/scan.ts quickly below or inline it.
            // Inline for now to avoid breaking flow, but properly refactored code would have it separate.
            await scanProjectLogic(context);
        })
    );

    // 3. 初始化 UI
    StatusBarManager.init(context);

    // 4. 自動開啟控制台 (延遲啟動)
    setTimeout(() => {
        const projectPath = vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders[0].uri.fsPath : "";
        if (projectPath) {
            vscode.commands.executeCommand('codesynth.openCockpit');
        }
    }, 3000);
}

export function deactivate() {
    ServerManager.stop();
}

// Helper for Scan Project (extracted from original extension.ts)
import * as path from 'path';
import axios from 'axios';

async function scanProjectLogic(context: vscode.ExtensionContext) {
    const projectPath = vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders[0].uri.fsPath : "";
    if (!projectPath) {
        return;
    }

    // ✅ 加入檔案過濾
    const files = await vscode.workspace.findFiles(
        '**/*.{py,js,ts,tsx,jsx,java,cpp,c,h,go,rs,swift,kt,html,css,json,yml,yaml}',
        '{**/node_modules/**,**/.git/**,**/__pycache__/**,**/venv/**,**/.venv/**,**/dist/**,**/build/**,**/out/**,**/*.db,**/*.db-journal,**/*.db-wal,**/*.pyc,**/.next/**,**/.nuxt/**,**/coverage/**,**/*.min.js,**/*.min.css}'
    );

    let successCount = 0;
    let errorCount = 0;

    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "CodeSynth: 正在掃描專案...",
        cancellable: false
    }, async (progress) => {
        const BATCH_SIZE = 50;
        const totalFiles = files.length;

        for (let i = 0; i < totalFiles; i += BATCH_SIZE) {
            const batch = files.slice(i, Math.min(i + BATCH_SIZE, totalFiles));
            try {
                const snapshots = await Promise.all(
                    batch.map(async (file) => {
                        try {
                            const doc = await vscode.workspace.openTextDocument(file);
                            const relativePath = path.relative(projectPath, file.fsPath);
                            return {
                                file_path: relativePath,
                                content: doc.getText(),
                                trigger: "Initial Scan"
                            };
                        } catch (e) {
                            return null;
                        }
                    })
                );

                const validSnapshots = snapshots.filter(s => s !== null);

                if (validSnapshots.length > 0) {
                    const result = await axios.post('http://127.0.0.1:8000/api/batch_snapshot', {
                        project_path: projectPath,
                        snapshots: validSnapshots
                    });

                    if (result.data.status === 'ok') {
                        successCount += result.data.success_count;
                        errorCount += result.data.errors.length;
                    }
                }

                const processed = Math.min(i + BATCH_SIZE, totalFiles);
                const percentage = (processed / totalFiles) * 100;
                progress.report({
                    increment: (BATCH_SIZE / totalFiles) * 100,
                    message: `${processed}/${totalFiles} (${percentage.toFixed(0)}%)`
                });

            } catch (e) {
                console.error('批次掃描失敗：', e);
                errorCount += batch.length;
            }
        }
    });

    if (errorCount > 0) {
        vscode.window.showWarningMessage(`掃描完成！成功：${successCount}，失敗：${errorCount}`);
    } else {
        vscode.window.showInformationMessage(`✅ 掃描完成！共匯入 ${successCount} 個檔案`);
    }

    // Refresh Cockpit
    if (CockpitPanel.currentPanel) {
        await CockpitPanel.currentPanel.refresh();
    }
}