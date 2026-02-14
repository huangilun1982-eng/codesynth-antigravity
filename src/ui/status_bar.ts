import * as vscode from 'vscode';

export class StatusBarManager {
    private static _items: vscode.StatusBarItem[] = [];

    public static init(context: vscode.ExtensionContext) {
        // 4. 狀態列按鈕 (控制台) - 左側
        const btnCockpit = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
        btnCockpit.command = 'codesynth.openCockpit';
        btnCockpit.text = "$(settings-gear) CodeSynth 控制台";
        btnCockpit.tooltip = "開啟 CodeSynth 管理介面";
        btnCockpit.show();
        context.subscriptions.push(btnCockpit);
        this._items.push(btnCockpit);

        // 5. 狀態列按鈕 (執行測試) - 左側
        const btnRun = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 90);
        btnRun.command = 'codesynth.startSimulation';
        btnRun.text = "$(play) Test Execution";
        btnRun.tooltip = "在沙盒中執行測試";
        btnRun.color = "#4EC9B0"; // Accent color
        btnRun.show();
        context.subscriptions.push(btnRun);
        this._items.push(btnRun);

        // 6. 程式碼導出按鈕 - 左側
        const btnExport = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 80);
        btnExport.command = 'codesynth.exportCode';
        btnExport.text = "$(export) 導出程式碼";
        btnExport.tooltip = "導出選定版本的程式碼";
        btnExport.show();
        context.subscriptions.push(btnExport);
        this._items.push(btnExport);
    }

    public static dispose() {
        this._items.forEach(i => i.dispose());
        this._items = [];
    }
}
