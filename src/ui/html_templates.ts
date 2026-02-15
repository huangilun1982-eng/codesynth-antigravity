import { COCKPIT_CSS } from './assets/styles';
import { COCKPIT_SCRIPT, WIZARD_SCRIPT } from './assets/scripts';

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
            <button class="btn btn-primary" onclick="vscode.postMessage({command: 'start_simulation'})"><i class="codicon codicon-play"></i> 執行測試</button>
            <button class="btn" onclick="vscode.postMessage({command: 'open_preview'})" title="開啟即時預覽"><i class="codicon codicon-browser"></i> 預覽</button>
            <div style="flex:1"></div>
            <div class="tab-group">
                <button class="btn tab-btn active" onclick="switchTab('files')">檔案快照</button>
                <button class="btn tab-btn" onclick="switchTab('ailog')">AI 日誌</button>
                <button class="btn tab-btn" onclick="switchTab('memory')">記憶中樞</button>
                <button class="btn tab-btn" onclick="switchTab('skills')">技能商店</button>
            </div>
            <button class="btn" onclick="refresh()"><i class="codicon codicon-sync"></i></button>
        </div>

        <div id="tab-files" class="tab-content active">
            <!-- Stage Toolbar -->
            <div class="stage-bar">
                <button class="btn-mini" onclick="createStage()" title="將目前選擇建立為新階段"><i class="codicon codicon-plus"></i></button>
                <div id="stage-list" style="display:flex; gap:6px;">
                    <div id="stage-pill-all" class="stage-pill active" onclick="selectStage(null)">全部</div>
                    <!-- Dynamic Stages Injected Here -->
                </div>
            </div>
            
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

        <div id="tab-skills" class="tab-content" style="display:none">
            <div id="skill-list" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap:15px; padding:10px;">
                <div class="loading-spinner">正在載入技能包...</div>
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

export function getWizardHTML(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Project Wizard</title>
    <style>
        ${COCKPIT_CSS}
        .wizard-container {
            max-width: 600px;
            margin: 40px auto;
            background: var(--vscode-editor-background);
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .step-indicator {
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
        }
        .step-dot {
            width: 30px; 
            height: 30px; 
            border-radius: 50%; 
            background: var(--vscode-widget-border);
            text-align: center;
            line-height: 30px;
            font-weight: bold;
            opacity: 0.5;
        }
        .step-dot.active {
            background: var(--vscode-button-background);
            opacity: 1;
            color: var(--vscode-button-foreground);
        }
        .step-content {
            display: none;
        }
        .step-content.active {
            display: block;
            animation: fadeIn 0.3s;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-input { 
            width: 100%; 
            padding: 8px; 
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            border-radius: 4px;
        }
        
        .card-opt {
            border: 1px solid var(--vscode-widget-border);
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 4px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card-opt:hover { background: var(--vscode-list-hoverBackground); }
        
        .nav-buttons {
            display: flex;
            justify-content: space-between;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid var(--vscode-widget-border);
        }
        
        .skill-option {
            display: flex;
            gap: 10px;
            padding: 10px;
            border-bottom: 1px solid var(--vscode-widget-border);
        }
    </style>
</head>
<body>
    <div class="wizard-container">
        <h2 style="text-align: center; margin-bottom: 20px;">🪄 CodeSynth Project Wizard</h2>
        
        <div class="step-indicator">
            <div class="step-dot active">1</div>
            <div class="step-dot">2</div>
            <div class="step-dot">3</div>
            <div class="step-dot">4</div>
        </div>
        
        <!-- Step 1: Project Info -->
        <div id="step-1" class="step-content active">
            <h3>專案資訊</h3>
            <div class="form-group">
                <label class="form-label">專案名稱 (Name)</label>
                <input type="text" id="p-name" class="form-input" placeholder="MyAwesomeProject" value="MyProject">
            </div>
            <div class="form-group">
                <label class="form-label">儲存路徑 (Path)</label>
                <div style="display:flex; gap: 5px;">
                    <input type="text" id="p-path" class="form-input" placeholder="C:/Projects">
                    <button class="btn" onclick="selectFolder()">瀏覽...</button>
                </div>
            </div>
        </div>

        <!-- Step 2: Template -->
        <div id="step-2" class="step-content">
            <h3>選擇模板</h3>
            <label class="card-opt">
                <input type="radio" name="template" value="empty">
                <div>
                     <strong>空專案 (Empty)</strong><br>
                     <small>完全空白的起點。</small>
                </div>
            </label>
            <label class="card-opt">
                <input type="radio" name="template" value="webapp" checked>
                <div>
                     <strong>Web 應用程式 (Web App)</strong><br>
                     <small>包含 HTML/CSS/JS 基礎結構與即時預覽支援。</small>
                </div>
            </label>
            <label class="card-opt">
                <input type="radio" name="template" value="python">
                <div>
                     <strong>Python 腳本 (Python Script)</strong><br>
                     <small>基礎 Python 開發環境。</small>
                </div>
            </label>
        </div>

        <!-- Step 3: Skills -->
        <div id="step-3" class="step-content">
            <h3>預裝技能 (Skills)</h3>
            <p style="font-size: 0.9em; opacity: 0.8; margin-bottom: 15px;">選擇要預先安裝的功能模組。</p>
            <div id="skill-selection" style="max-height: 300px; overflow-y: auto;">
                <!-- Rendered by JS -->
                <div class="empty-state">Loading skills...</div>
            </div>
        </div>

        <!-- Step 4: Summary -->
        <div id="step-4" class="step-content">
            <div id="summary-content"></div>
        </div>

        <div class="nav-buttons">
            <button id="btn-prev" class="btn" onclick="prevStep()" disabled>上一步 (Back)</button>
            <button id="btn-next" class="btn btn-primary" onclick="nextStep()">下一步 (Next)</button>
        </div>
    </div>
    
    <script>
        ${WIZARD_SCRIPT}
    </script>
</body>
</html>`;
}
