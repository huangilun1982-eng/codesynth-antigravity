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
        } else if (tabName === 'skills') {
            document.getElementById('tab-skills').style.display = 'block';
            document.querySelector('.tab-btn:nth-child(4)').classList.add('active');
            loadSkills();
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
    
    // --- Stage Management Logic ---
    let currentStageId = null;

    function loadStages() {
        // Request stage list from extension (which calls Python API)
        vscode.postMessage({ command: 'get_stages' });
    }

    function createStage() {
        const name = prompt("請輸入階段名稱 (例如: v1.0-Alpha):");
        if (name) {
            const description = prompt("請輸入描述 (選填):", "");
            vscode.postMessage({ command: 'create_stage', name: name, description: description });
        }
    }

    function selectStage(stageId) {
        currentStageId = stageId;
        // Update UI emphasis
        document.querySelectorAll('.stage-pill').forEach(el => el.classList.remove('active'));
        if (stageId) {
            document.getElementById('stage-pill-' + stageId).classList.add('active');
            vscode.postMessage({ command: 'get_stage_items', stage_id: stageId });
        } else {
            document.getElementById('stage-pill-all').classList.add('active');
            vscode.postMessage({ command: 'refresh' }); // Reload full view
        }
    }

    window.addEventListener('message', event => {
        const message = event.data;
        if (message.command === 'update_stages') {
            renderStages(message.stages);
        } else if (message.command === 'update_stage_items') {
            // Received specific items for a stage -> Filter the view
            applyStageFilter(message.items);
        } else if (message.command === 'update_ai_log') {
            renderAILogs(message.logs);
        } else if (message.command === 'update_memory_status') {
            renderMemoryStatus(message.memory);
        } else if (message.command === 'update_skills') {
            renderSkills(message.skills);
        }
    });

    // --- Skill Store Logic ---
    function loadSkills() {
        vscode.postMessage({ command: 'get_skills' });
    }

    function installSkill(skillId, name) {
        if(confirm('確定要安裝技能包: ' + name + ' 嗎？')) {
            // For now, no params. In future, we can pop up a dialog.
            const params = {
                title: "Welcome to CodeSynth",
                subtitle: "Built with Antigravity",
                cta_text: "Get Started"
            };
            vscode.postMessage({ command: 'install_skill', skill_id: skillId, params: params });
        }
    }

    function renderSkills(skills) {
        const container = document.getElementById('skill-list');
        if (!container) return;

        if (!skills || skills.length === 0) {
            container.innerHTML = '<div class="empty-state">目前沒有可用的技能包</div>';
            return;
        }

        let html = '';
        skills.forEach(skill => {
            html += '<div class="log-card" style="border-left-color: #ff9f43;">' +
                    '<div class="log-header"><span class="log-what">' + skill.name + '</span> <span class="tag-badge">' + skill.version + '</span></div>' +
                    '<div class="log-body" style="margin: 10px 0;">' + skill.description + '</div>' + 
                    '<button class="btn btn-primary" style="width:100%" onclick="installSkill(\\'' + skill.id + '\\', \\'' + skill.name + '\\')">安裝 (Install)</button>' +
                    '</div>';
        });
        container.innerHTML = html;
    }

    function renderStages(stages) {
        const container = document.getElementById('stage-list');
        if (!container) return;
        
        let html = '<div id="stage-pill-all" class="stage-pill active" onclick="selectStage(null)">全部</div>';
        
        stages.forEach(stage => {
            html += '<div id="stage-pill-' + stage.id + '" class="stage-pill" onclick="selectStage(' + stage.id + ')" title="' + (stage.description || '') + '">' +
                        '<i class="codicon codicon-tag"></i> ' + stage.name +
                     '</div>';
        });
        
        container.innerHTML = html;
    }

    function applyStageFilter(items) {
        // items: [{file_path, version_id}]
        // 1. Hide all files first
        document.querySelectorAll('.file-group').forEach(el => el.style.display = 'none');
        
        // 2. Show only relevant files and select specific versions
        items.forEach(item => {
            // Find file group
            // Note: File names in ID might need escaping if they contain special chars. 
            // Simplified here assuming standard filenames.
            
            // Iterate all groups to find match (slower but safer for complex paths)
            const groups = document.querySelectorAll('.file-group');
            groups.forEach(group => {
                const title = group.querySelector('.fname').innerText;
                if (title === item.file_path || title.endsWith(item.file_path) || item.file_path.endsWith(title)) { // Fuzzy match for relative paths
                   group.style.display = 'block';
                   
                   // Select specific version
                   const radio = group.querySelector('input[value="' + item.version_id + '"]');
                   if (radio) {
                       radio.click(); // Trigger selection logic
                       const row = radio.closest('tr');
                       if(row) row.classList.add('stage-locked');
                   }
                }
            });
        });
    }

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

export const WIZARD_SCRIPT = `
    const vscode = acquireVsCodeApi();
    let currentStep = 1;
    let wizardData = {
        name: '',
        path: '',
        template: 'empty',
        skills: []
    };

    function nextStep() {
        if (!validateStep(currentStep)) return;
        
        // Save data from current step
        saveStepData(currentStep);

        currentStep++;
        updateUI();
    }

    function prevStep() {
        currentStep--;
        updateUI();
    }
    
    function validateStep(step) {
        if (step === 1) {
            const name = document.getElementById('p-name').value;
            const path = document.getElementById('p-path').value;
            if(!name || !path) {
                alert('請填寫完整專案資訊');
                return false;
            }
        }
        return true;
    }

    function saveStepData(step) {
        if (step === 1) {
            wizardData.name = document.getElementById('p-name').value;
            wizardData.path = document.getElementById('p-path').value;
        } else if (step === 2) {
             const selected = document.querySelector('input[name="template"]:checked');
             if(selected) wizardData.template = selected.value;
        } else if (step === 3) {
            const checkboxes = document.querySelectorAll('.skill-check:checked');
            wizardData.skills = Array.from(checkboxes).map(cb => cb.value);
        }
    }

    function updateUI() {
        // Hide all steps
        document.querySelectorAll('.step-content').forEach(el => el.classList.remove('active'));
        // Show current step
        document.getElementById('step-' + currentStep).classList.add('active');
        
        // Update Buttons
        document.getElementById('btn-prev').disabled = (currentStep === 1);
        if (currentStep === 4) {
            document.getElementById('btn-next').innerText = '建立專案 (Create)';
            document.getElementById('btn-next').onclick = createProject;
            renderSummary();
        } else {
            document.getElementById('btn-next').innerText = '下一步 (Next)';
            document.getElementById('btn-next').onclick = nextStep;
        }
        
        // Update Steps Indicator
        document.querySelectorAll('.step-dot').forEach((el, index) => {
             if (index + 1 === currentStep) el.classList.add('active');
             else el.classList.remove('active');
        });
    }

    function renderSummary() {
        let html = '<h3>確認專案資訊</h3>';
        html += '<p><strong>名稱:</strong> ' + wizardData.name + '</p>';
        html += '<p><strong>路徑:</strong> ' + wizardData.path + '</p>';
        html += '<p><strong>模板:</strong> ' + wizardData.template + '</p>';
        html += '<p><strong>技能:</strong> ' + (wizardData.skills.length ? wizardData.skills.join(', ') : '無') + '</p>';
        document.getElementById('summary-content').innerHTML = html;
    }

    function createProject() {
        document.getElementById('btn-next').disabled = true;
        document.getElementById('btn-next').innerText = '建立中...';
        vscode.postMessage({
            command: 'create_project',
            data: wizardData
        });
    }

    function selectFolder() {
        vscode.postMessage({ command: 'select_folder' });
    }

    window.addEventListener('message', event => {
        const message = event.data;
        if (message.command === 'set_path') {
            document.getElementById('p-path').value = message.path;
        } else if (message.command === 'update_skills') {
             renderSkills(message.skills);
        }
    });
    
    function renderSkills(skills) {
        const container = document.getElementById('skill-selection');
        let html = '';
        skills.forEach(skill => {
             html += '<label class="skill-option">';
             html += '<input type="checkbox" class="skill-check" value="' + skill.id + '">';
             html += '<span><strong>' + skill.name + '</strong><br><small>' + skill.description + '</small></span>';
             html += '</label>';
        });
        container.innerHTML = html;
    }

    // Init
    window.onload = function() {
        vscode.postMessage({ command: 'get_skills' }); 
        updateUI();
    };
`;
