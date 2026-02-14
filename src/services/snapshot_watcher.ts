import * as vscode from 'vscode';
import * as path from 'path';
import axios from 'axios';
import { CockpitPanel } from '../ui/cockpit_panel';

export function startSnapshotWatcher(context: vscode.ExtensionContext) {
    const watcher = vscode.workspace.onDidSaveTextDocument(async (document) => {
        console.log(`[CodeSynth] 檔案保存觸發: ${document.fileName}`);

        // 忽略 .db 檔案
        if (document.fileName.endsWith(".db") || document.fileName.includes(".db-journal")) {
            return;
        }

        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            return;
        }

        const projectPath = workspaceFolders[0].uri.fsPath;
        const relativePath = path.relative(projectPath, document.fileName);

        // 忽略工作區外的檔案
        if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
            return;
        }

        // 忽略特定目錄 (簡單過濾)
        if (relativePath.includes('python_server') && relativePath.endsWith('.pyc')) { return; }
        if (relativePath.includes('__pycache__')) { return; }
        if (relativePath.includes('.git')) { return; }
        if (relativePath.includes('node_modules')) { return; }

        try {
            console.log(`[CodeSynth] 開始備份: ${relativePath}`);

            await axios.post('http://127.0.0.1:8000/api/snapshot', {
                project_path: projectPath,
                file_path: relativePath,
                content: document.getText(),
                trigger: 'Auto-Save'
            });

            console.log(`[CodeSynth] 備份成功: ${relativePath}`);
            vscode.window.setStatusBarMessage(`✅ CodeSynth: 已備份 ${relativePath}`, 3000);

            // 自動刷新控制台（如果已開啟）
            if (CockpitPanel.currentPanel) {
                await CockpitPanel.currentPanel.refresh();
            }
        } catch (error) {
            console.error(`[CodeSynth] 保存失敗:`, error);
            vscode.window.setStatusBarMessage(`❌ CodeSynth: 備份失敗 ${relativePath}`, 3000);
        }
    });

    context.subscriptions.push(watcher);
}
