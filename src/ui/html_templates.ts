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
            :root {
                --bg-primary: #1e1e1e;
                --bg-secondary: #252526;
                --bg-hover: #2a2d2e;
                --bg-selected: #37373d;
                --border-color: #3e3e3e;
                --accent-color: #0e639c;
                --text-primary: #cccccc;
                --text-secondary: #858585;
                --success-color: #4ec9b0;
                --error-color: #f14c4c;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background-color: var(--bg-primary);
                color: var(--text-primary);
                margin: 0;
                padding: 10px;
                font-size: 13px;
            }

            /* Toolbar */
            .toolbar {
                display: flex;
                gap: 8px;
                padding-bottom: 10px;
                border-bottom: 1px solid var(--border-color);
                margin-bottom: 10px;
                position: sticky;
                top: 0;
                background: var(--bg-primary);
                z-index: 10;
            }

            .btn {
                background: var(--bg-secondary);
                color: var(--text-primary);
                border: 1px solid var(--border-color);
                padding: 4px 10px;
                border-radius: 2px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 12px;
            }
            .btn:hover { background: var(--bg-hover); }
            .btn-primary { background: var(--accent-color); border-color: var(--accent-color); color: white; }

            /* File Group */
            .file-group {
                border: 1px solid var(--border-color);
                margin-bottom: 8px;
                border-radius: 4px;
                background: var(--bg-secondary);
                overflow: hidden;
            }

            .file-header-compact {
                padding: 6px 10px;
                background: var(--bg-hover);
                display: flex;
                justify-content: space-between;
                align-items: center;
                cursor: pointer;
                user-select: none;
            }
            .file-header-compact:hover { background: #333; }

            .file-title { display: flex; align-items: center; gap: 8px; font-weight: 600; color: #e0e0e0; }
            .fname { font-family: Consolas, monospace; }
            .fbadge { background: #444; color: #aaa; padding: 1px 6px; border-radius: 10px; font-size: 10px; }

            /* Version Table */
            .file-body { display: block; }
            
            .version-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 12px;
            }

            .version-row {
                border-top: 1px solid #333;
                transition: background 0.1s;
                cursor: pointer;
            }
            .version-row:hover { background: #2a2d2e; }
            .version-row.selected { background: var(--bg-selected); }

            td { padding: 4px 8px; vertical-align: middle; }
            
            .col-select { width: 20px; text-align: center; }
            .col-ver { width: 40px; }
            .col-time { width: 100px; color: var(--text-secondary); }
            .col-status { width: 24px; text-align: center; }
            .col-tag { }
            .col-actions { text-align: right; width: 80px; opacity: 0.1; transition: opacity 0.2s; }
            .version-row:hover .col-actions { opacity: 1; }

            .ver-pill {
                background: #333;
                padding: 1px 5px;
                border-radius: 3px;
                color: #ccc;
                font-family: monospace;
            }

            .status-icon { font-size: 14px; display: flex; align-items: center; justify-content: center; }
            .status-icon.success { color: var(--success-color); }
            .status-icon.failed { color: var(--error-color); }
            
            .tag-badge {
                background: #094771;
                color: #fff;
                padding: 1px 6px;
                border-radius: 3px;
                font-size: 11px;
            }

            /* Mini Buttons */
            .btn-mini {
                background: transparent;
                border: none;
                color: #aaa;
                cursor: pointer;
                padding: 2px 4px;
                border-radius: 3px;
            }
            .btn-mini:hover { background: #444; color: white; }

            /* Context Menu */
            #contextMenu {
                display: none;
                position: absolute;
                background: #252526;
                border: 1px solid #454545;
                box-shadow: 0 2px 8px rgba(0,0,0,0.5);
                z-index: 1000;
                min-width: 160px;
                padding: 4px 0;
            }
            
            .menu-item {
                padding: 6px 12px;
                cursor: pointer;
                color: #cccccc;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .menu-item:hover { background: #094771; color: white; }
            .menu-sep { height: 1px; background: #454545; margin: 4px 0; }

            /* Tabs */
            .tab-group { display: flex; background: #2a2d2e; border-radius: 4px; padding: 2px; }
            .tab-btn { background: transparent; border: none; padding: 4px 12px; cursor: pointer; color: #888; border-radius: 4px; transition: all 0.2s; }
            .tab-btn.active { background: var(--bg-primary); color: var(--text-primary); font-weight: bold; box-shadow: 0 1px 4px rgba(0,0,0,0.2); }
            .tab-btn:hover:not(.active) { color: #ccc; }

            /* Log Stream */
            .log-container { padding: 10px; }
            .log-stream { display: flex; flex-direction: column; gap: 10px; }
            .log-card {
                background: #252526; border: 1px solid #3e3e3e; border-radius: 6px; padding: 10px;
                border-left: 4px solid #555;
            }
            .log-header { display: flex; justify-content: space-between; font-size: 0.85em; color: #888; margin-bottom: 5px; }
            .log-what { font-weight: bold; margin-bottom: 4px; color: #e0e0e0; }
            .log-summary { font-size: 0.9em; color: #ccc; line-height: 1.4; }
            .log-error { margin-top: 8px; font-family: monospace; background: rgba(255,0,0,0.1); color: #f48771; padding: 5px; border-radius: 4px; font-size: 0.9em; }
            
            .log-success { border-left-color: var(--success-color); }
            .log-failed { border-left-color: var(--error-color); }
            
            .loading-spinner { text-align: center; color: #888; margin-top: 20px; font-style: italic; }

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
            const vscode = acquireVsCodeApi();

            function switchTab(tabName) {
                document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
                document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
                
                if (tabName === 'files') {
                    document.getElementById('tab-files').style.display = 'block';
                    document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
                } else if (tabName === 'ailog') {
                    document.getElementById('tab-ailog').style.display = 'block';
                    document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
                    vscode.postMessage({ command: 'get_ai_log' });
                }
            }

            // Toggle File Accordion
            function toggleFile(file) {
                const body = document.getElementById('body-' + file);
                const icon = document.getElementById('icon-' + file);
                if (body.style.display === 'none') {
                    body.style.display = 'block';
                    icon.classList.remove('codicon-chevron-right');
                    icon.classList.add('codicon-chevron-down');
                } else {
                    body.style.display = 'none';
                    icon.classList.remove('codicon-chevron-down');
                    icon.classList.add('codicon-chevron-right');
                }
            }
            
            function selectRow(row, file, verId) {
                // Visual selection
                const rows = row.parentElement.querySelectorAll('.version-row');
                rows.forEach(r => r.classList.remove('selected'));
                row.classList.add('selected');
                
                // Trigger radio check
                const radio = row.querySelector('input[type="radio"]');
                if(radio) {
                    radio.checked = true;
                    // Dont trigger notify again if clicked directly (optional)
                    notifySelectVersion(file, verId);
                }
            }

            function scanProject() { vscode.postMessage({ command: 'scan_project' }); }
            function refresh() { vscode.postMessage({ command: 'refresh' }); }

            function restoreFile(file, verId) {
                if(confirm('確定要還原 ' + file + ' 到此版本嗎？')) {
                    vscode.postMessage({ command: 'restore_file', file_path: file, version_id: verId });
                }
            }
            
            function checkScreenshots(file, verId) {
                 vscode.postMessage({ command: 'check_screenshots', file_path: file, version_id: verId });
            }

            function notifySelectVersion(file, verId) {
                vscode.postMessage({ command: 'select_version', file_path: file, version_id: verId });
            }
            
            // --- Context Menu Logic ---
            let currentMenuTarget = null;

            function showContextMenu(e, file, verId) {
                e.preventDefault();
                e.stopPropagation();
                currentMenuTarget = { file, verId };
                const menu = document.getElementById('contextMenu');
                menu.style.display = 'block';
                
                let x = e.pageX;
                let y = e.pageY;
                if (x + 160 > window.innerWidth) x -= 160;
                menu.style.left = x + 'px';
                menu.style.top = y + 'px';
            }

            document.addEventListener('click', () => {
                document.getElementById('contextMenu').style.display = 'none';
            });

            function execMenu(action) {
                if (!currentMenuTarget) return;
                const { file, verId } = currentMenuTarget;
                
                if (action === 'restore') {
                    restoreFile(file, verId);
                } else if (action === 'run') {
                    vscode.postMessage({ command: 'run_file', file_path: file });
                } else if (action === 'status_success') {
                    vscode.postMessage({ command: 'update_status', file_path: file, version_id: verId, status: 'success' });
                } else if (action === 'status_failed') {
                    vscode.postMessage({ command: 'update_status', file_path: file, version_id: verId, status: 'failed' });
                } else if (action === 'set_tag') {
                    const tag = prompt("標籤名稱:", "Feature");
                    if (tag !== null) {
                         vscode.postMessage({ command: 'update_tag', file_path: file, version_id: verId, feature_tag: tag });
                    }
                }
            }
            
            window.addEventListener('message', event => {
                const message = event.data;
                if (message.command === 'update_ai_log') {
                    renderAILogs(message.logs);
                }
            });

            function renderAILogs(logs) {
                const container = document.getElementById('ai-log-container');
                if (!logs || logs.length === 0) {
                    container.innerHTML = '<div class="empty-state">尚無 AI 日誌記錄</div>';
                    return;
                }

                let html = '<div class="log-stream">';
                logs.forEach(log => {
                    const time = new Date(log.timestamp * 1000).toLocaleString('zh-TW');
                    const statusClass = log.test_result === 'success' ? 'log-success' : (log.test_result === 'failed' ? 'log-failed' : 'log-normal');
                    
                    html += '<div class="log-card ' + statusClass + '">';
                    html +=   '<div class="log-header">';
                    html +=     '<span class="log-time">' + time + '</span>';
                    html +=     '<span class="log-status">' + log.current_status + '</span>';
                    html +=   '</div>';
                    html +=   '<div class="log-body">';
                    html +=     '<div class="log-what">' + log.what_happened + '</div>';
                    html +=     '<div class="log-summary">' + (log.ai_summary || '') + '</div>';
                    html +=   '</div>';
                    if (log.error_message) {
                        html += '<div class="log-error">' + log.error_message + '</div>';
                    }
                    html += '</div>';
                });
                html += '</div>';
                container.innerHTML = html;
            }
</script>
    </body>
    </html>`;
}
