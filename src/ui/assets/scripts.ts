export const COCKPIT_SCRIPT = `
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
        } else if (tabName === 'memory') {
            document.getElementById('tab-memory').style.display = 'block';
            document.querySelector('.tab-btn:nth-child(3)').classList.add('active');
            vscode.postMessage({ command: 'get_memory_status' });
        }
    }

    function condenseMemory() {
        vscode.postMessage({ command: 'condense_memory' });
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
        } else if (message.command === 'update_memory_status') {
            renderMemoryStatus(message.memory);
        }
    });

    function renderMemoryStatus(memory) {
        document.getElementById('mem-soul').innerText = memory.soul || 'N/A';
        document.getElementById('mem-identity').innerText = memory.identity || 'N/A';
        document.getElementById('mem-user').innerText = memory.user || 'N/A';
        document.getElementById('mem-memory').innerText = memory.memory || 'N/A';
    }

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
`;
