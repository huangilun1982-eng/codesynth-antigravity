import * as vscode from 'vscode';
import axios from 'axios';
import { CockpitPanel } from '../ui/cockpit_panel';
import { API } from '../config';

export async function startSimulationCmd(context: vscode.ExtensionContext) {
    vscode.window.showInformationMessage("CodeSynth: 正在啟動測試指令...");
    console.log("[CodeSynth] startSimulationCmd triggered");
    const projectPath = vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders[0].uri.fsPath : "";
    if (!projectPath) {
        vscode.window.showErrorMessage("請先開啟一個資料夾！");
        return;
    }

    // 取得目前 Dashboard 的選擇狀態 (from CockpitPanel)
    if (!CockpitPanel.currentPanel) {
        vscode.window.showWarningMessage("請先開啟 CodeSynth 控制台以確認版本選擇。");
        // We could proceed with default choices or force open panel
        // For better UX, let's just warn or open panel.
        // Let's try to fetch dashboard data anyway if possible, but selection lives in Panel memory.
        // If panel is closed, versionSelection is empty/lost.
        return;
    }

    vscode.window.setStatusBarMessage("CodeSynth: 正在準備執行環境...", 2000);

    try {
        // 先取得 dashboard 資料以獲取當前檔案清單
        const dashRes = await axios.post(API.DASHBOARD, { project_path: projectPath });
        const filesData = dashRes.data.files;
        const versionSelection = CockpitPanel.currentPanel.versionSelection;

        // 建立 selection 物件 {file_path: version_id}
        const selection: { [key: string]: number } = {};

        // 使用用戶選中的版本，沒有選擇的使用最新版本
        for (const [filePath, versions] of Object.entries(filesData as any)) {
            if (versions && Array.isArray(versions) && versions.length > 0) {
                if (versionSelection.has(filePath)) {
                    // 使用用戶選中的版本
                    selection[filePath] = versionSelection.get(filePath)!;
                } else {
                    // 預設使用最新版本
                    selection[filePath] = (versions[0] as any).id;
                }
            }
        }

        // 顯示使用的版本組合
        const versionInfo = Object.entries(selection)
            .map(([file, verId]) => {
                const versions = (filesData as any)[file];
                const versionIndex = versions.findIndex((v: any) => v.id === verId);
                const versionNumber = versions.length - versionIndex;
                return `${file}: V${versionNumber}`;
            })
            .join(', ');

        console.log(`使用版本組合: ${versionInfo}`);

        // 檢查標籤一致性
        const tagCheck = await checkTagConsistency(filesData, selection);
        if (tagCheck.hasMixedTags) {
            const answer = await vscode.window.showWarningMessage(
                `⚠️ 檢測到不同的功能標籤：\n\n${tagCheck.summary}\n\n這可能導致功能不相容，要繼續測試嗎？`,
                { modal: true },
                '繼續測試',
                '統一為主要標籤',
                '取消'
            );

            if (answer === '統一為主要標籤' && tagCheck.primaryTag) {
                await unifyToTag(projectPath, filesData, tagCheck.primaryTag, versionSelection);
                vscode.window.showInformationMessage(`✅ 已統一為「${tagCheck.primaryTag}」`);
                return; // 重新執行 - logic needs restart
            } else if (answer === '取消') {
                return;
            }
        }

        vscode.window.setStatusBarMessage("CodeSynth: 正在執行測試...", 3000);

        const res = await axios.post(API.SIMULATION, {
            project_path: projectPath,
            selection: selection
        });

        const result = res.data;

        // 根據執行結果顯示不同訊息
        if (result.status === 'success') {

            // ⭐ 如果有回傳 app_url (例如 Streamlit)，直接打開瀏覽器
            if (result.app_url) {
                vscode.env.openExternal(vscode.Uri.parse(result.app_url));
                vscode.window.showInformationMessage(`✅ 測試已啟動！正在瀏覽器開啟...`, { modal: false });
            }

            const output = result.output || '(無輸出)';
            vscode.window.showInformationMessage(
                `✅ 執行成功！\n\n版本: ${versionInfo}\n\n輸出:\n${output.substring(0, 200)}${output.length > 200 ? '...' : ''}`,
                { modal: false },
                '查看完整輸出'
            ).then(sel => {
                if (sel === '查看完整輸出') {
                    const outputChannel = vscode.window.createOutputChannel('CodeSynth Test Execution');
                    outputChannel.clear();
                    outputChannel.appendLine('=== CodeSynth 測試執行結果 ===\n');
                    outputChannel.appendLine(`狀態: ${result.message}`);
                    outputChannel.appendLine(`執行檔案: ${result.files?.join(', ')}\n`);
                    outputChannel.appendLine('--- 標準輸出 (stdout) ---');
                    outputChannel.appendLine(result.output || '(無)');
                    if (result.error) {
                        outputChannel.appendLine('\n--- 標準錯誤 (stderr) ---');
                        outputChannel.appendLine(result.error);
                    }
                    outputChannel.show();
                }
            });
        } else if (result.status === 'failed') {
            vscode.window.showErrorMessage(`❌ 執行失敗！\n\n${result.message || result.output}`, { modal: false });
        } else {
            // 測試失敗/錯誤/超時
            const screenshot = result.screenshot;
            const buttons = ['查看錯誤詳情', '請 Antigravity 協助'];
            if (screenshot) {
                buttons.splice(1, 0, '📸 查看截圖');
            }

            vscode.window.showErrorMessage(
                `❌ ${result.message}\n\n${result.error || ''}`,
                { modal: false },
                ...buttons
            ).then(async sel => {
                if (sel === '查看錯誤詳情') {
                    const detail = `狀態: ${result.status}\n\n` +
                        `輸出:\n${result.output || '(無)'}\n\n` +
                        `錯誤:\n${result.error || '(無)'}\n\n` +
                        `結束代碼: ${result.exit_code || 'N/A'}`;
                    vscode.window.showInformationMessage(detail, { modal: true });
                } else if (sel === '📸 查看截圖' && screenshot) {
                    const screenshotUri = vscode.Uri.file(screenshot);
                    try {
                        await vscode.commands.executeCommand('vscode.open', screenshotUri);
                    } catch (e) {
                        vscode.window.showErrorMessage(`無法開啟截圖: ${e}`);
                    }
                } else if (sel === '請 Antigravity 協助') {
                    vscode.window.showInformationMessage(
                        '💡 請在 Antigravity 對話中說：\n\n「測試失敗了，幫我診斷問題」\n\nAntigravity 會自動分析錯誤並提供解決方案！',
                        { modal: true },
                        '我了解'
                    );
                }
            });
        }

    } catch (e) {
        vscode.window.showErrorMessage(`測試執行錯誤: ${e}`);
    }
}

// Helpers
async function checkTagConsistency(filesData: any, selection: { [key: string]: number }) {
    const tags: { [tag: string]: number } = {};
    let totalFiles = 0;

    for (const [file, versionId] of Object.entries(selection)) {
        const versions = filesData[file];
        if (versions && Array.isArray(versions)) {
            const version = versions.find((v: any) => v.id === versionId);
            if (version) {
                const tag = version.feature_tag || '無標籤';
                tags[tag] = (tags[tag] || 0) + 1;
                totalFiles++;
            }
        }
    }

    const tagList = Object.keys(tags);
    const hasMixedTags = tagList.length > 1;
    const primaryTag = tagList.reduce((a, b) => tags[a] > tags[b] ? a : b, tagList[0]);
    const summary = Object.entries(tags)
        .map(([tag, count]) => `${tag}: ${count}個檔案`)
        .join('\n');

    return { hasMixedTags, tags, primaryTag: primaryTag === '無標籤' ? null : primaryTag, summary, totalFiles };
}

async function unifyToTag(projectPath: string, filesData: any, targetTag: string, versionSelection: Map<string, number>) {
    for (const [file, versions] of Object.entries(filesData as any)) {
        if (versions && Array.isArray(versions)) {
            const taggedVersion = versions.find((v: any) => v.feature_tag === targetTag);
            if (taggedVersion) {
                versionSelection.set(file, taggedVersion.id);
            }
        }
    }
}
