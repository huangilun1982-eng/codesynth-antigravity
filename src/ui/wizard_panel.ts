import * as vscode from 'vscode';
import * as path from 'path';
import axios from 'axios';
import { getWizardHTML } from './html_templates';
import { API } from '../config';

export class WizardPanel {
    public static currentPanel: WizardPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._extensionUri = extensionUri;

        this._panel.webview.html = getWizardHTML();

        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        this._panel.webview.onDidReceiveMessage(
            message => this._handleMessage(message),
            null,
            this._disposables
        );
    }

    public static createOrShow(extensionUri: vscode.Uri) {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        if (WizardPanel.currentPanel) {
            WizardPanel.currentPanel._panel.reveal(column);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'codeSynthWizard',
            'Create New Project',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')]
            }
        );

        WizardPanel.currentPanel = new WizardPanel(panel, extensionUri);
    }

    public dispose() {
        WizardPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }

    private async _handleMessage(message: any) {
        switch (message.command) {
            case 'select_folder':
                const result = await vscode.window.showOpenDialog({
                    canSelectFiles: false,
                    canSelectFolders: true,
                    canSelectMany: false,
                    openLabel: 'Select Project Root'
                });
                if (result && result.length > 0) {
                    this._panel.webview.postMessage({ command: 'set_path', path: result[0].fsPath });
                }
                break;
            case 'get_skills':
                await this.getSkills();
                break;
            case 'create_project':
                await this.createProject(message.data);
                break;
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

    private async createProject(data: any) {
        try {
            // Call Python API
            const res = await axios.post(API.WIZARD_CREATE, {
                name: data.name,
                path: data.path,
                template_id: data.template,
                skills: data.skills
            });

            if (res.data.status === 'success') {
                vscode.window.showInformationMessage(`✅ ${res.data.message}`);

                // Close Wizard
                this.dispose();

                // Open the new project
                const projectPath = res.data.path;
                const uri = vscode.Uri.file(projectPath);
                await vscode.commands.executeCommand('vscode.openFolder', uri);

            } else {
                vscode.window.showErrorMessage(`❌ 建立失敗: ${res.data.message}`);
            }
        } catch (e) {
            vscode.window.showErrorMessage(`❌ 錯誤: ${e}`);
        }
    }
}
