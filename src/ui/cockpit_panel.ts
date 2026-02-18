// ui/cockpit_panel.ts
import * as vscode from 'vscode';
import * as path from 'path';
import axios from 'axios';
import { getCockpitHTML } from './html_templates';
import { API, SERVER_URL } from '../config';

export class CockpitPanel {
    public static currentPanel: CockpitPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _projectPath: string;
    private _disposables: vscode.Disposable[] = [];
    public versionSelection: Map<string, number> = new Map();

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, projectPath: string) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._projectPath = projectPath;

        // Set the webview's initial html content
        this._update();

        // Listen for when the panel is disposed
        // This happens when the user closes the panel or when the panel is closed programmatically
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        // Handle messages from the webview
        this._panel.webview.onDidReceiveMessage(
            message => this._handleMessage(message),
            null,
            this._disposables
        );
    }

    public static createOrShow(extensionUri: vscode.Uri, projectPath: string) {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        // If we already have a panel, show it.
        if (CockpitPanel.currentPanel) {
            CockpitPanel.currentPanel._panel.reveal(column);
            return;
        }

        // Otherwise, create a new panel.
        const panel = vscode.window.createWebviewPanel(
            'codeSynthCockpit',
            'CodeSynth 控制台',
            column || vscode.ViewColumn.Two,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')]
            }
        );

        CockpitPanel.currentPanel = new CockpitPanel(panel, extensionUri, projectPath);
    }

    public static revive(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, projectPath: string) {
        CockpitPanel.currentPanel = new CockpitPanel(panel, extensionUri, projectPath);
    }

    public dispose() {
        CockpitPanel.currentPanel = undefined;

        // Clean up our resources
        this._panel.dispose();

        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }

    public async refresh() {
        await this._update();
    }

    private async _update() {
        try {
            console.log(`[CodeSynth] Refreshing cockpit...`);
            const res = await axios.post(API.DASHBOARD, {
                project_path: this._projectPath
            });
            this._panel.webview.html = getCockpitHTML(res.data.files, this._projectPath);
        } catch (error) {
            this._panel.webview.html = `
            <html><body>
            <h1>無法連線 Server</h1>
            <p>請確認 python server/main.py 有在跑。</p>
            <p>錯誤: ${error}</p>
            </body></html>`;
        }
    }

    private async _handleMessage(message: any) {
        switch (message.command) {
            case 'refresh':
                await this.refresh();
                break;
            case 'open_file':
                await this.openFile(message.file_path);
                break;
            case 'restore_file':
                await this.restoreFile(message.file_path, message.version_id);
                break;
            case 'select_version':
                this.versionSelection.set(message.file_path, message.version_id);
                break;
            case 'scan_project':
                await vscode.commands.executeCommand('codesynth.scanProject');
                break;
            case 'start_simulation':
                await vscode.commands.executeCommand('codesynth.startSimulation');
                break;
            case 'run_file':
                await this.runFile(message.file_path);
                break;
            case 'update_status':
                await this.updateStatus(message.version_id, message.status);
                break;
            case 'update_tag':
                await this.updateTag(message.version_id, message.feature_tag);
                break;
            case 'check_screenshots':
                await this.checkScreenshots(message.file_path, message.version_id);
                break;
            case 'get_ai_log':
                await this.sendAIContext();
                break;
            case 'get_memory_status':
                await this.sendMemoryStatus();
                break;
            case 'condense_memory':
                await this.triggerCondenseMemory();
                break;
            case 'create_stage':
                await this.createStage(message.name, message.description);
                break;
            case 'get_stages':
                await this.getStages();
                break;
            case 'get_stage_items':
                await this.getStageItems(message.stage_id);
                break;
            case 'open_preview':
                try {
                    // PREVIEW-05: 安全預覽挂載流程
                    // 1. 請求後端建立預覽 Session
                    const pRes = await axios.post(API.PREVIEW_INIT, {
                        project_path: this._projectPath
                    });
                    const sessionId = pRes.data.session_id;

                    // 2. 開啟對應 Session 的 index.html
                    const previewUrl = `${API.PREVIEW_BASE}/${sessionId}/index.html`;
                    await vscode.commands.executeCommand('simpleBrowser.show', previewUrl);
                } catch (e) {
                    vscode.window.showErrorMessage(`無法啟動預覽: ${e}`);
                }
                break;
            case 'get_skills':
                await this.getSkills();
                break;
            case 'install_skill':
                await this.installSkill(message.skill_id, message.params);
                break;
        }
    }

    private async sendAIContext() {
        try {
            const res = await axios.post(API.AI_CONTEXT, {
                project_path: this._projectPath,
                limit: 50
            });

            this._panel.webview.postMessage({
                command: 'update_ai_log',
                logs: res.data.recent_logs
            });
        } catch (e) {
            console.error(e);
        }
    }

    private async sendMemoryStatus() {
        try {
            const res = await axios.get(API.AI_MEMORY);
            this._panel.webview.postMessage({
                command: 'update_memory_status',
                memory: res.data
            });
        } catch (e) {
            console.error(e);
            vscode.window.showErrorMessage(`讀取記憶失敗: ${e}`);
        }
    }

    private async triggerCondenseMemory() {
        try {
            vscode.window.showInformationMessage('正在整理記憶...');
            await axios.post(API.AI_CONDENSE);
            vscode.window.showInformationMessage('記憶整理完成！');
            await this.sendMemoryStatus(); // Refresh UI
        } catch (e) {
            vscode.window.showErrorMessage(`記憶整理失敗: ${e}`);
        }
    }

    private async openFile(filePath: string) {
        const fullPath = path.join(this._projectPath, filePath);
        const doc = await vscode.workspace.openTextDocument(fullPath);
        await vscode.window.showTextDocument(doc);
    }

    private async checkScreenshots(filePath: string, versionId: number) {
        try {
            const res = await axios.post(API.SCREENSHOTS, {
                project_path: this._projectPath,
                version_id: versionId
            });

            const screenshots = res.data.screenshots;
            if (!screenshots || screenshots.length === 0) {
                vscode.window.showInformationMessage(`此版本沒有相關截圖`);
                return;
            }

            // Show screenhsots (For now, just open the first one or list them)
            // Opening image in VS Code
            for (const shot of screenshots) {
                if (shot.image_path && shot.image_path.trim() !== "") {
                    const uri = vscode.Uri.file(shot.image_path);
                    await vscode.commands.executeCommand('vscode.open', uri);
                }
            }
        } catch (e) {
            vscode.window.showErrorMessage(`讀取截圖失敗: ${e}`);
        }
    }

    private async restoreFile(filePath: string, versionId: number) {
        try {
            const verRes = await axios.post(API.GET_VERSION, {
                project_path: this._projectPath,
                id: versionId
            });
            const code = verRes.data.content;
            const fullPath = path.join(this._projectPath, filePath);
            const uri = vscode.Uri.file(fullPath);
            await vscode.workspace.fs.writeFile(uri, Buffer.from(code, 'utf8'));
            vscode.window.showInformationMessage(`✅ ${filePath} 已還原！`);
        } catch (e) {
            vscode.window.showErrorMessage(`還原失敗: ${e}`);
        }
    }

    private async runFile(filePath: string) {
        const fullPath = path.join(this._projectPath, filePath);
        let terminal = vscode.window.terminals.find(t => t.name === "CodeSynth Execution");
        if (!terminal) {
            terminal = vscode.window.createTerminal("CodeSynth Execution");
        }
        terminal.show();

        const ext = path.extname(fullPath).toLowerCase();
        let cmd = "";
        if (ext === '.py') {
            cmd = `python "${fullPath}"`;
        } else if (ext === '.js') {
            cmd = `node "${fullPath}"`;
        } else if (ext === '.ts') {
            cmd = `npx ts-node "${fullPath}"`;
        } else {
            cmd = `echo "尚未支援此檔案類型: ${ext}"`;
        }
        terminal.sendText(cmd);
    }

    private async updateStatus(versionId: number, status: string) {
        await axios.post(API.UPDATE_STATUS, {
            project_path: this._projectPath,
            id: versionId,
            status: status
        });
        await this.refresh();
    }

    private async updateTag(versionId: number, featureTag: string) {
        await axios.post(API.UPDATE_TAG, {
            project_path: this._projectPath,
            version_id: versionId,
            feature_tag: featureTag
        });
        await this.refresh();
    }

    private async createStage(name: string, description: string) {
        try {
            // Get current version selection
            const items = [];
            for (const [file, verId] of this.versionSelection.entries()) {
                items.push({ file_path: file, version_id: verId });
            }

            if (items.length === 0) {
                vscode.window.showWarningMessage('請至少選擇一個檔案版本來建立階段');
                return;
            }

            const res = await axios.post(API.STAGE_CREATE, {
                project_path: this._projectPath,
                name: name,
                description: description,
                items: items
            });

            if (res.data.status === 'success') {
                vscode.window.showInformationMessage(`階段 '${name}' 建立成功！`);
                await this.getStages(); // Refresh list
            } else {
                vscode.window.showErrorMessage(`建立失敗: ${res.data.message}`);
            }
        } catch (e) {
            vscode.window.showErrorMessage(`建立階段錯誤: ${e}`);
        }
    }

    private async getStages() {
        try {
            const res = await axios.post(API.STAGE_LIST, {
                project_path: this._projectPath
            });
            this._panel.webview.postMessage({
                command: 'update_stages',
                stages: res.data.stages
            });
        } catch (e) {
            console.error(e);
        }
    }

    private async getStageItems(stageId: number) {
        try {
            const res = await axios.post(API.STAGE_ITEMS, {
                project_path: this._projectPath,
                stage_id: stageId
            });
            this._panel.webview.postMessage({
                command: 'update_stage_items',
                items: res.data.items
            });
        } catch (e) {
            console.error(e);
        }
    }

    private async getSkills() {
        try {
            const res = await axios.get(API.SKILL_LIST);
            this._panel.webview.postMessage({
                command: 'update_skills',
                skills: res.data.skills
            });
        } catch (e) {
            console.error(e);
        }
    }

    private async installSkill(skillId: string, params: any) {
        try {
            const res = await axios.post(API.SKILL_INSTALL, {
                project_path: this._projectPath,
                skill_id: skillId,
                params: params
            });

            if (res.data.status === 'success') {
                vscode.window.showInformationMessage(`✅ ${res.data.message}`);
                // Refresh to show changes if any
                await this.refresh();
            } else {
                vscode.window.showErrorMessage(`❌ 安裝失敗: ${res.data.message}`);
            }
        } catch (e) {
            vscode.window.showErrorMessage(`❌ 錯誤: ${e}`);
        }
    }
}
