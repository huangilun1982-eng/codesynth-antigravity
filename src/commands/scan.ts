import * as vscode from 'vscode';
import * as path from 'path';
import axios from 'axios';
import { CockpitPanel } from '../ui/cockpit_panel';

export async function scanProjectCmd(context: vscode.ExtensionContext) {
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
