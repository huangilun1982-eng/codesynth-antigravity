import { COCKPIT_CSS } from './assets/styles';
import { COCKPIT_SCRIPT } from './assets/scripts';

export function getCockpitHTML(filesData: any, projectPath: string): string {
    const safeProjectPath = projectPath.replace(/\\/g, '\\\\').replace(/`/g, '\\`');
    const sortedFiles = Object.keys(filesData).sort();

    let filesHtml = '';

    for (const file of sortedFiles) {
        const versions = filesData[file];
        if (!versions || versions.length === 0) { continue; }

        let versionsHtml = '';
        versions.forEach((v: any, index: number) => {
            const isSuccess = v.status === 'success';
            const isFailed = v.status === 'failed';
            const statusClass = isSuccess ? 'status-success' : (isFailed ? 'status-failed' : 'status-pending');
            const statusIcon = isSuccess ? '<i class="codicon codicon-check"></i>' : (isFailed ? '<i class="codicon codicon-error"></i>' : '<i class="codicon codicon-circle-outline"></i>');
            const tagHtml = v.feature_tag ? `<span class="tag-badge">${v.feature_tag}</span>` : '';
            const verNum = versions.length - index;
            const timeLabel = new Date(v.timestamp * 1000).toLocaleString('zh-TW', { hour12: false, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });

            // Compact Row Design
            versionsHtml += `
            <tr class="version-row ${statusClass}" data-id="${v.id}" onclick="selectRow(this, '${file}', ${v.id})">
                <td class="col-select">
                    <input type="radio" name="ver_${file}" value="${v.id}" ${index === 0 ? 'checked' : ''} onchange="event.stopPropagation(); notifySelectVersion('${file}', ${v.id})">
                </td>
                <td class="col-ver"><span class="ver-pill">V${verNum}</span></td>
                <td class="col-time">${timeLabel}</td>
                <td class="col-status"><span class="status-icon ${v.status}">${statusIcon}</span></td>
                <td class="col-tag">${tagHtml}</td>
                <td class="col-actions">
                    <button class="btn-mini" title="還原" onclick="event.stopPropagation(); restoreFile('${file}', ${v.id})"><i class="codicon codicon-discard"></i></button>
                    <button class="btn-mini" title="截圖" onclick="event.stopPropagation(); checkScreenshots('${file}', ${v.id})"><i class="codicon codicon-camera"></i></button>
                    <button class="btn-mini" title="更多" onclick="showContextMenu(event, '${file}', ${v.id})"><i class="codicon codicon-kebab-vertical"></i></button>
                </td>
            </tr>`;
        });

        filesHtml += `
        <div class="file-group">
            <div class="file-header-compact" onclick="toggleFile('${file}')">
                <div class="file-title">
                    <i class="codicon codicon-file-code"></i>
                    <span class="fname">${file}</span>
                    <span class="fbadge">${versions.length}</span>
                </div>
                <i class="codicon codicon-chevron-down toggle-icon" id="icon-${file}"></i>
            </div>
            <div class="file-body" id="body-${file}">
                <table class="version-table">
                    ${versionsHtml}
                </table>
            </div>
        </div>`;
    }

    if (!filesHtml) {
        filesHtml = `
        <div class="empty-state">
            <div class="empty-icon"><i class="codicon codicon-folder-opened"></i></div>
            <h3>專案尚未掃描</h3>
            <p>請點擊上方工具列的「掃描專案」</p>
        </div>`;
    }

    return `<!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CodeSynth Cockpit</title>
        <link href="${'https://unpkg.com/@vscode/codicons/dist/codicon.css'}" rel="stylesheet" />
        <style>
            ${COCKPIT_CSS}
        </style>
    </head>
    <body>
        <div class="toolbar">
            <button class="btn" onclick="scanProject()"><i class="codicon codicon-refresh"></i> 掃描專案</button>
            <button class="btn btn-primary" onclick="vscode.postMessage({command: 'codesynth.startSimulation'})"><i class="codicon codicon-play"></i> 執行測試</button>
            <div style="flex:1"></div>
            <div class="tab-group">
                <button class="btn tab-btn active" onclick="switchTab('files')">檔案快照</button>
                <button class="btn tab-btn" onclick="switchTab('ailog')">AI 日誌</button>
                <button class="btn tab-btn" onclick="switchTab('memory')">記憶中樞</button>
            </div>
            <button class="btn" onclick="refresh()"><i class="codicon codicon-sync"></i></button>
        </div>

        <div id="tab-files" class="tab-content active">
            <div id="file-list">
                ${filesHtml}
            </div>
        </div>

        <div id="tab-ailog" class="tab-content" style="display:none">
            <div id="ai-log-container" class="log-container">
                <div class="loading-spinner">載入中...</div>
            </div>
        </div>

        <div id="tab-memory" class="tab-content" style="display:none">
            <div class="toolbar" style="border-bottom:none; padding-top:0;">
                <button class="btn btn-primary" onclick="condenseMemory()"><i class="codicon codicon-sparkle"></i> 整理記憶 (Condense)</button>
                <span style="color:#888; font-size:12px; margin-left:10px;">* 將今日對話濃縮至 User Profile</span>
            </div>
            <div id="memory-container" class="log-container" style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                <!-- SOUL -->
                <div class="log-card" style="border-left-color: #d16d9e;">
                    <div class="log-header"><span class="log-what">SOUL (核心準則)</span></div>
                    <pre id="mem-soul" class="log-summary" style="white-space:pre-wrap; font-family:consolas;">Loading...</pre>
                </div>
                <!-- IDENTITY -->
                <div class="log-card" style="border-left-color: #569cd6;">
                    <div class="log-header"><span class="log-what">IDENTITY (人設)</span></div>
                    <pre id="mem-identity" class="log-summary" style="white-space:pre-wrap; font-family:consolas;">Loading...</pre>
                </div>
                <!-- USER -->
                <div class="log-card" style="border-left-color: #4ec9b0; grid-column: span 2;">
                    <div class="log-header"><span class="log-what">USER PROFILE (用戶偏好)</span></div>
                    <pre id="mem-user" class="log-summary" style="white-space:pre-wrap; font-family:consolas;">Loading...</pre>
                </div>
                <!-- MEMORY -->
                <div class="log-card" style="border-left-color: #dcdcaa; grid-column: span 2;">
                    <div class="log-header"><span class="log-what">PROJECT MEMORY (長期記憶)</span></div>
                    <pre id="mem-memory" class="log-summary" style="white-space:pre-wrap; font-family:consolas;">Loading...</pre>
                </div>
            </div>
        </div>

        <!-- Context Menu -->
        <div id="contextMenu">
            <div class="menu-item" onclick="execMenu('restore')"><i class="codicon codicon-discard"></i> 還原 (Restore)</div>
            <div class="menu-item" onclick="execMenu('run')"><i class="codicon codicon-play"></i> 執行 (Run)</div>
            <div class="menu-sep"></div>
            <div class="menu-item" onclick="execMenu('set_tag')"><i class="codicon codicon-tag"></i> 設定標籤</div>
            <div class="menu-item" onclick="execMenu('status_success')"><i class="codicon codicon-check"></i> 標記成功</div>
            <div class="menu-item" onclick="execMenu('status_failed')"><i class="codicon codicon-error"></i> 標記失敗</div>
        </div>

        <script>
            ${COCKPIT_SCRIPT}
        </script>
    </body>
    </html>`;
}
