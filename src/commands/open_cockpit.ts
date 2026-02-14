import * as vscode from 'vscode';
import { CockpitPanel } from '../ui/cockpit_panel';
import { ServerManager } from '../services/server_manager';

export async function openCockpitCmd(context: vscode.ExtensionContext) {
    const projectPath = vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders[0].uri.fsPath : "";
    if (!projectPath) {
        vscode.window.showErrorMessage("請先開啟一個資料夾！");
        return;
    }

    // 嘗試啟動或確認伺服器
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: "CodeSynth",
        cancellable: false
    }, async (progress) => {
        progress.report({ message: "正在啟動後端服務..." });

        // Check health first to avoid restart if already running
        const healthy = await ServerManager.checkHealth();
        if (!healthy) {
            await ServerManager.start(context);
        }
    });

    const isHealthy = await ServerManager.checkHealth();
    if (!isHealthy) {
        const sel = await vscode.window.showErrorMessage(
            "無法連接 CodeSynth Server，請檢查 Output 面板。",
            "查看 Output", "重試"
        );
        if (sel === "查看 Output") {
            // Ideally expose a method to show output, but it's likely already shown if start failed
        }
        return;
    }

    CockpitPanel.createOrShow(context.extensionUri, projectPath);
}
