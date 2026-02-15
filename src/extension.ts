import * as vscode from 'vscode';
import { ServerManager } from './services/server_manager';
import { startSnapshotWatcher } from './services/snapshot_watcher';
import { StatusBarManager } from './ui/status_bar';
import { openCockpitCmd } from './commands/open_cockpit';
import { startSimulationCmd } from './commands/simulation';
import { exportCodeCmd } from './commands/export';
import { scanProjectCmd } from './commands/scan';
import { CockpitPanel } from './ui/cockpit_panel';
import { WizardPanel } from './ui/wizard_panel';
import * as path from 'path';
import axios from 'axios';

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
            await scanProjectCmd(context);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codesynth.openWizard', () => {
            WizardPanel.createOrShow(context.extensionUri);
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