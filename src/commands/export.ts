import * as vscode from 'vscode';
import axios from 'axios';
import * as path from 'path';
import * as fs from 'fs';
import { API } from '../config';

export async function exportCodeCmd(context: vscode.ExtensionContext) {
    const projectPath = vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders[0].uri.fsPath : "";
    if (!projectPath) {
        vscode.window.showErrorMessage("請先開啟一個資料夾！");
        return;
    }

    vscode.window.setStatusBarMessage("CodeSynth: 正在導出程式碼...", 2000);

    try {
        // 取得專案資料
        const dashRes = await axios.post(API.DASHBOARD, { project_path: projectPath });
        const filesData = dashRes.data.files;

        // 建立導出目錄
        const exportDir = path.join(projectPath, '_codesynth_export');
        if (!fs.existsSync(exportDir)) {
            fs.mkdirSync(exportDir);
        }

        // 導出每個檔案的最新版本
        let exportedFiles = 0;
        for (const [filePath, versions] of Object.entries(filesData as any)) {
            if (versions && Array.isArray(versions) && versions.length > 0) {
                // QUA-06: 路徑遍歷防護
                const normalized = path.normalize(filePath);
                if (normalized.startsWith('..') || path.isAbsolute(normalized)) {
                    console.warn(`[CodeSynth] 跳過不安全路徑: ${filePath}`);
                    continue;
                }

                const latestVersion = versions[0] as any; // 最新版本

                // 取得內容
                const contentRes = await axios.post(API.GET_VERSION, {
                    project_path: projectPath,
                    id: latestVersion.id
                });

                // 寫入檔案
                const exportPath = path.join(exportDir, normalized);

                // 再次確認解析後的路徑仍在 exportDir 內
                const resolvedExport = path.resolve(exportPath);
                if (!resolvedExport.startsWith(path.resolve(exportDir))) {
                    console.warn(`[CodeSynth] 路徑逃逸偵測: ${filePath}`);
                    continue;
                }

                const exportFileDir = path.dirname(exportPath);

                // 建立子目錄
                if (!fs.existsSync(exportFileDir)) {
                    fs.mkdirSync(exportFileDir, { recursive: true });
                }

                fs.writeFileSync(exportPath, contentRes.data.content, 'utf-8');
                exportedFiles++;
            }
        }

        vscode.window.showInformationMessage(
            `✅ 導出完成！已導出 ${exportedFiles} 個檔案到 _codesynth_export 目錄`,
            { modal: false },
            '開啟資料夾'
        ).then(selection => {
            if (selection === '開啟資料夾') {
                vscode.commands.executeCommand('revealFileInOS', vscode.Uri.file(exportDir));
            }
        });

    } catch (e: any) {
        vscode.window.showErrorMessage(`❌ 導出失敗: ${e.message || 'Server 未回應'}`);
    }
}
