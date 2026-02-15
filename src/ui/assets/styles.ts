export const COCKPIT_CSS = `
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

    /* Stage Pills */
    .stage-bar {
        display: flex;
        gap: 8px;
        padding: 8px 10px;
        background: #252526;
        border-bottom: 1px solid var(--border-color);
        overflow-x: auto;
        white-space: nowrap;
        align-items: center;
    }
    .stage-pill {
        background: #333;
        color: #aaa;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        cursor: pointer;
        border: 1px solid transparent;
        transition: all 0.2s;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .stage-pill:hover { background: #444; color: #eee; }
    .stage-pill.active { background: var(--accent-color); color: white; border-color: var(--accent-color); }
    
    .stage-locked {
        background: rgba(14, 99, 156, 0.2) !important;
        border-left: 2px solid var(--accent-color);
    }
`;
